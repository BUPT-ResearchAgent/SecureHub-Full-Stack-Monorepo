# Status: real

"""Wave 4-5 fault injection for the durable Runtime control plane.

These tests deliberately use local fakes at external boundaries.  They prove
the Runtime's real/fixture separation and recovery decisions; they do not
claim a provider, RAG index, or object store integration succeeded.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models.workflow_runtime import WorkflowAuditLog, WorkflowRun, WorkflowStepAttempt
from app.llm.provider import LLMChunk
from app.runtime.budget import BudgetController
from app.runtime.contracts import ArtifactRef, ErrorCode, EvidenceRef, ExecutionMode, ProviderSelection
from app.runtime.engine import RuntimeEngine
from app.runtime.harness.contracts import SkillDefinition
from app.runtime.harness.context import ExecutionContext
from app.runtime.harness.executor import SkillExecutor
from app.runtime.observability import RuntimeMetricsService
from app.runtime.persistence import ApprovalStore, CheckpointStore, EventStore, RunStore
from app.runtime.persistence.common import utcnow
from app.runtime.tools import PolicyEngine, ToolDefinition
from app.runtime.typed_state import TypedWorkflowState
from app.runtime.workflow_definition import EdgeDefinition, NodeDefinition, WorkflowDefinition
from app.runtime.workflow_registry import WorkflowRegistry
from app.runtime.workflows.course_learning_full_v1 import COURSE_LEARNING_FULL_V1
from app.schemas.agent_control import WorkflowRunStartRequest
from app.services.workflow_application_service import WorkflowApplicationService


class _Input(BaseModel):
    value: str


class _Output(BaseModel):
    value: str


def _registry(definition: WorkflowDefinition) -> WorkflowRegistry:
    registry = WorkflowRegistry()
    registry.register(definition)
    return registry


async def _claimed_run(
    session: Any,
    definition: WorkflowDefinition,
    *,
    budget: dict[str, Any] | None = None,
    user_id: UUID | None = None,
) -> tuple[RunStore, Any]:
    store = RunStore(session)
    run = await store.create_run(
        workflow_name=definition.name,
        workflow_version=str(definition.version),
        workflow_definition_digest=definition.definition_digest,
        catalog_version=definition.catalog_version,
        provider_policy_version=definition.provider_policy_version,
        checkpoint_schema_version=definition.checkpoint_schema_version,
        runtime_build_sha="dev",
        user_id=user_id or uuid4(),
        mode="fixture",
        requested_provider="fixture",
        requested_model="fixture-v1",
        input_payload={"value": "wave test"},
        budget=budget or {},
    )
    await session.commit()
    claimed = await store.claim_next("wave-test-worker", lease_seconds=60)
    assert claimed is not None
    await session.commit()
    return store, claimed


def _action_engine(
    session: Any,
    definition: WorkflowDefinition,
    store: RunStore,
    action_handler: Any,
) -> RuntimeEngine:
    events = EventStore(session)
    return RuntimeEngine(
        session=session,
        workflow_registry=_registry(definition),
        skill_catalog={},
        run_store=store,
        event_store=events,
        skill_executor=object(),
        action_handler=action_handler,
        checkpoint_store=CheckpointStore(session),
        runtime_build_sha="dev",
    )


def test_typed_state_projects_only_declared_lineage_and_routes_taxonomy() -> None:
    evidence = EvidenceRef(
        evidence_snapshot_id=str(uuid4()),
        chunk_id="chunk-1",
        document_id="document-1",
        content_digest="a" * 64,
    )
    artifact = ArtifactRef(
        resource_id=str(uuid4()),
        resource_type="doc",
        evidence_snapshot_ids=[evidence.evidence_snapshot_id],
        lineage_root_id=str(uuid4()),
    )
    state = TypedWorkflowState(
        {
            "generate_path": {
                "output": {"title": "path"},
                "evidence_snapshot_ids": [str(evidence.evidence_snapshot_id)],
                "evidence_refs": [evidence],
            },
            "hidden_other_branch": {"output": {"secret": "not projected"}},
            "resource_doc": {"output": {"title": "doc"}, "artifact_refs": [artifact]},
        }
    )

    projection = state.project(("generate_path", "resource_doc"))
    assert set(projection) == {"generate_path", "resource_doc"}
    assert projection["resource_doc"]["artifact_refs"][0]["resource_id"] == str(artifact.resource_id)
    assert projection["generate_path"]["evidence_snapshot_ids"] == [str(evidence.evidence_snapshot_id)]
    assert "hidden_other_branch" not in projection

    citation_targets = COURSE_LEARNING_FULL_V1.rework_targets(
        "quality_check", [{"code": "citation_mismatch"}]
    )
    assert [node.node_id for node in citation_targets] == [
        "resource_doc",
        "resource_ppt",
        "resource_quiz",
        "resource_lab",
    ]
    defects = [{"code": "fact_conflict", "target_node": "resource_doc"}]
    assert state.record_defects(defects, node_id="quality_check") is False
    assert state.record_defects(defects, node_id="quality_check") is True


def test_fanout_action_output_retains_every_artifact_lineage_reference() -> None:
    output = {
        "resources": [
            {
                "resource_id": str(uuid4()),
                "resource_type": "doc",
                "evidence_snapshot_ids": [str(uuid4())],
                "lineage_root_id": str(uuid4()),
                "version": 1,
            },
            {
                "resource_id": str(uuid4()),
                "resource_type": "quiz",
                "evidence_snapshot_ids": [str(uuid4())],
                "lineage_root_id": str(uuid4()),
                "version": 1,
            },
        ]
    }
    refs = RuntimeEngine._artifact_refs_from_output(output)
    assert len(refs) == 2
    assert {ref["resource_type"] for ref in refs} == {"doc", "quiz"}


@pytest.mark.anyio
async def test_recovered_fanout_does_not_repeat_completed_branches(sqlite_session: Any) -> None:
    definition = WorkflowDefinition(
        name="recovered_fanout_v1",
        version=1,
        input_model=_Input,
        output_model=_Output,
        nodes=(
            NodeDefinition("start", "action", action_name="start"),
            NodeDefinition("branch_a", "action", action_name="branch_a", input_sources=("start",)),
            NodeDefinition("branch_b", "action", action_name="branch_b", input_sources=("start",)),
            NodeDefinition("join", "action", action_name="join", input_sources=("branch_a", "branch_b")),
        ),
        edges=(
            EdgeDefinition("start", "branch_a"),
            EdgeDefinition("start", "branch_b"),
            EdgeDefinition("branch_a", "join"),
            EdgeDefinition("branch_b", "join"),
        ),
    )
    store, claimed = await _claimed_run(sqlite_session, definition)
    for node_id in ("start", "branch_a", "branch_b"):
        await store.create_step_attempt(
            workflow_run_id=claimed.id,
            node_id=node_id,
            attempt=1,
            status="succeeded",
            output_ref={"value": node_id},
            lease_epoch=claimed.lease_epoch,
        )
    await sqlite_session.commit()

    executed: list[str] = []

    async def action(action_name: str, *_args: Any, **_kwargs: Any) -> dict[str, str]:
        executed.append(action_name)
        return {"value": action_name}

    result = await _action_engine(sqlite_session, definition, store, action).execute(
        claimed.id,
        lease_owner="wave-test-worker",
    )

    assert result.status == "succeeded"
    assert executed == ["join"]
    attempts = list(
        (
            await sqlite_session.execute(
                select(WorkflowStepAttempt)
                .where(WorkflowStepAttempt.workflow_run_id == claimed.id)
                .order_by(WorkflowStepAttempt.created_at.asc())
            )
        ).scalars().all()
    )
    assert [(item.node_id, item.attempt) for item in attempts] == [
        ("start", 1),
        ("branch_a", 1),
        ("branch_b", 1),
        ("join", 1),
    ]


@pytest.mark.anyio
async def test_recovered_action_adopts_its_incomplete_step_attempt(sqlite_session: Any) -> None:
    definition = WorkflowDefinition(
        name="recovered_action_v1",
        version=1,
        input_model=_Input,
        output_model=_Output,
        nodes=(NodeDefinition("persist", "action", action_name="persist"),),
    )
    store, claimed = await _claimed_run(sqlite_session, definition)
    running = await store.transition_run(
        claimed.id,
        expected_state_version=claimed.state_version,
        lease_epoch=claimed.lease_epoch,
        status="running",
    )
    original_epoch = running.lease_epoch
    original_step = await store.create_step_attempt(
        workflow_run_id=running.id,
        node_id="persist",
        attempt=1,
        status="pending",
        lease_epoch=running.lease_epoch,
    )
    await store.transition_step_attempt(
        original_step.id,
        expected_state_version=original_step.state_version,
        lease_epoch=running.lease_epoch,
        status="running",
    )
    await sqlite_session.execute(
        update(WorkflowRun)
        .where(WorkflowRun.id == running.id)
        .values(lease_expires_at=utcnow() - timedelta(seconds=1))
    )
    await sqlite_session.commit()
    replacement = await store.claim_next("recovery-worker", lease_seconds=60)
    assert replacement is not None and replacement.lease_epoch == original_epoch + 1

    calls: list[str] = []

    async def action(action_name: str, *_args: Any, **_kwargs: Any) -> dict[str, str]:
        calls.append(action_name)
        return {"value": action_name}

    result = await _action_engine(sqlite_session, definition, store, action).execute(
        replacement.id,
        lease_owner="recovery-worker",
    )
    attempts = list(
        (
            await sqlite_session.execute(
                select(WorkflowStepAttempt)
                .where(WorkflowStepAttempt.workflow_run_id == replacement.id)
                .order_by(WorkflowStepAttempt.attempt.asc())
            )
        ).scalars().all()
    )

    assert result.status == "succeeded"
    assert calls == ["persist"]
    assert [(item.id, item.attempt, item.status) for item in attempts] == [
        (original_step.id, 1, "succeeded"),
    ]


class _FallbackInput(BaseModel):
    query: str
    domain: str = "course_websec"


class _FallbackOutput(BaseModel):
    answer: str


def _fallback_definition() -> SkillDefinition:
    return SkillDefinition(
        name="FallbackProbe",
        agent_name="career_planner",
        version=1,
        input_model=_FallbackInput,
        output_model=_FallbackOutput,
        prompt_template="{task_instruction}\n{evidence_text}\n{output_schema_hint}",
        evidence_floor=1,
        fallback_policy="explicit-real-provider-only",
    )


class _Retriever:
    async def retrieve(self, *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        return [
            {
                "chunk_id": "durable-chunk-1",
                "document_id": "durable-document-1",
                "chunk_text": "Use parameterized queries for untrusted database values.",
                "source": "https://example.invalid/evidence",
                "metadata": {},
            }
        ]


class _SnapshotStore:
    async def save_many(self, *, records: list[dict[str, Any]]) -> list[dict[str, str]]:
        return [{"id": str(uuid4())} for _record in records]


class _PrimaryInterruptedProvider:
    provider_name = "xfyun"
    model_name = "spark-test"

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    async def stream_generate(self, *_args: Any, **_kwargs: Any) -> AsyncIterator[LLMChunk]:
        yield LLMChunk(content='{"answer":"partial', index=0)
        raise RuntimeError("simulated primary socket interruption")


class _PrimarySchemaInvalidProvider:
    provider_name = "xfyun"
    model_name = "spark-test"

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    async def stream_generate(self, *_args: Any, **_kwargs: Any) -> AsyncIterator[LLMChunk]:
        yield LLMChunk(content='{"answer":7}', index=0, finish_reason="stop")


class _FallbackProvider:
    provider_name = "deepseek"
    model_name = "deepseek-test"

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    async def stream_generate(self, *_args: Any, **_kwargs: Any) -> AsyncIterator[LLMChunk]:
        yield LLMChunk(content='{"answer":"replacement"}', index=0, finish_reason="stop")


class _Journal:
    def __init__(self) -> None:
        self.started: list[dict[str, Any]] = []
        self.completed: list[dict[str, Any]] = []
        self.visible: list[dict[str, Any]] = []

    async def start(self, **payload: Any) -> dict[str, str]:
        identifier = str(uuid4())
        self.started.append({**payload, "id": identifier})
        return {"id": identifier}

    async def complete(self, **payload: Any) -> None:
        self.completed.append(payload)

    async def add_visible_tokens(self, **payload: Any) -> None:
        self.visible.append(payload)

    async def mark_unknown(self, **_payload: Any) -> None:
        raise AssertionError("observed stream interruption must not become unknown")


@pytest.mark.anyio
async def test_real_primary_failure_uses_new_fallback_attempt_and_replaces_draft() -> None:
    emitted: list[tuple[str, dict[str, Any]]] = []

    async def emit(event_type: str, payload: dict[str, Any]) -> None:
        emitted.append((event_type, payload))

    journal = _Journal()
    executor = SkillExecutor(
        retriever=_Retriever(),
        provider_resolver=lambda _context: _PrimaryInterruptedProvider(),
        fallback_provider_resolver=lambda _name, _context: _FallbackProvider(),
        evidence_snapshot_store=_SnapshotStore(),
        provider_call_store=journal,
    )
    context = ExecutionContext(
        workflow_run_id=uuid4(),
        step_attempt_id=uuid4(),
        agent_run_id=uuid4(),
        user_id=uuid4(),
        mode=ExecutionMode.REAL,
        provider_selection=ProviderSelection(requested_provider="xfyun", requested_model="spark-test"),
        lease_epoch=1,
        emit=emit,
    )

    candidate = await executor.execute(_fallback_definition(), {"query": "Explain SQL injection."}, context)

    assert candidate.output.answer == "replacement"
    assert candidate.actual_provider == "deepseek"
    assert [row["provider"] for row in journal.started] == ["xfyun", "deepseek"]
    assert [row["outcome"] for row in journal.completed] == ["unavailable", "success"]
    assert journal.visible
    switches = [payload for event_type, payload in emitted if event_type == "trace"]
    assert switches and switches[-1]["provider_switch"]["replace_draft"] is True
    replacement_tokens = [payload for event_type, payload in emitted if event_type == "token"]
    assert replacement_tokens[-1]["replace_draft"] is True
    assert "partial" not in candidate.output.answer


@pytest.mark.anyio
async def test_strict_parse_failure_uses_declared_real_fallback_without_accepting_invalid_output() -> None:
    emitted: list[tuple[str, dict[str, Any]]] = []

    async def emit(event_type: str, payload: dict[str, Any]) -> None:
        emitted.append((event_type, payload))

    journal = _Journal()
    executor = SkillExecutor(
        retriever=_Retriever(),
        provider_resolver=lambda _context: _PrimarySchemaInvalidProvider(),
        fallback_provider_resolver=lambda _name, _context: _FallbackProvider(),
        evidence_snapshot_store=_SnapshotStore(),
        provider_call_store=journal,
    )
    context = ExecutionContext(
        workflow_run_id=uuid4(),
        step_attempt_id=uuid4(),
        agent_run_id=uuid4(),
        user_id=uuid4(),
        mode=ExecutionMode.REAL,
        provider_selection=ProviderSelection(requested_provider="xfyun", requested_model="spark-test"),
        lease_epoch=1,
        emit=emit,
    )

    candidate = await executor.execute(_fallback_definition(), {"query": "Explain SQL injection."}, context)

    assert candidate.output.answer == "replacement"
    assert candidate.actual_provider == "deepseek"
    assert [row["provider"] for row in journal.started] == ["xfyun", "deepseek"]
    assert [row["outcome"] for row in journal.completed] == ["known_error", "success"]
    switches = [payload for event_type, payload in emitted if event_type == "trace"]
    assert switches and switches[-1]["provider_switch"]["reason"] == ErrorCode.STRICT_PARSE_FAILED.value
    replacement_tokens = [payload for event_type, payload in emitted if event_type == "token"]
    assert replacement_tokens[-1]["replace_draft"] is True


@pytest.mark.anyio
async def test_budget_exhaustion_blocks_before_action_or_terminal_artifact(sqlite_session: Any) -> None:
    definition = WorkflowDefinition(
        name="budget_block_v1",
        version=1,
        input_model=_Input,
        output_model=_Output,
        nodes=(NodeDefinition("expensive", "action", action_name="Noop", budget_tokens=2),),
    )
    store, claimed = await _claimed_run(
        sqlite_session,
        definition,
        budget={"limits": {"max_tokens": 1}},
    )

    async def action(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("budget must block before an action effect")

    result = await _action_engine(sqlite_session, definition, store, action).execute(
        claimed.id,
        lease_owner="wave-test-worker",
    )
    events = await EventStore(sqlite_session).replay_events(claimed.id)
    assert result.status == "blocked"
    assert (await store.get_run(claimed.id)).error["code"] == ErrorCode.BUDGET_EXCEEDED
    assert events[-1].event_type == "error"
    assert {event.event_type for event in events}.isdisjoint({"token", "artifact"})


@pytest.mark.anyio
async def test_high_risk_action_requires_durable_approval_then_requeues(sqlite_session: Any) -> None:
    definition = WorkflowDefinition(
        name="approval_control_v1",
        version=1,
        input_model=_Input,
        output_model=_Output,
        nodes=(
            NodeDefinition(
                "publish",
                "action",
                action_name="Noop",
                risk_level="high",
                approval_required=True,
            ),
        ),
    )
    owner = uuid4()
    store, claimed = await _claimed_run(sqlite_session, definition, user_id=owner)

    async def action(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("unapproved high-risk action must not execute")

    result = await _action_engine(sqlite_session, definition, store, action).execute(
        claimed.id,
        lease_owner="wave-test-worker",
    )
    approvals = await ApprovalStore(sqlite_session).list_for_run(claimed.id)
    assert result.status == "waiting_approval"
    assert len(approvals) == 1 and approvals[0].status == "pending"
    await sqlite_session.commit()

    bind = sqlite_session.bind
    assert bind is not None
    service = WorkflowApplicationService(
        async_sessionmaker(bind, expire_on_commit=False),
        workflow_registry=_registry(definition),
        runtime_build_sha="dev",
    )
    approval = await service.decide_approval(
        claimed.id,
        approvals[0].id,
        approved=True,
        actor_user_id=owner,
    )
    assert approval.status == "approved"
    assert (await store.get_run(claimed.id)).status == "queued"


@pytest.mark.anyio
async def test_explicit_checkpoint_migration_is_persisted_before_resume(sqlite_session: Any) -> None:
    definition = WorkflowDefinition(
        name="checkpoint_migration_v1",
        version=1,
        input_model=_Input,
        output_model=_Output,
        nodes=(NodeDefinition("noop", "action", action_name="Noop"),),
        checkpoint_schema_version="typed-state-v1",
    )
    owner = uuid4()
    store, claimed = await _claimed_run(sqlite_session, definition, user_id=owner)
    running = await store.transition_run(
        claimed.id,
        expected_state_version=claimed.state_version,
        lease_epoch=claimed.lease_epoch,
        status="running",
    )
    checkpoint = await CheckpointStore(sqlite_session).save(
        workflow_run_id=running.id,
        workflow_definition_digest=definition.definition_digest,
        catalog_version=definition.catalog_version,
        checkpoint_schema_version="v1",
        runtime_build_sha="dev",
        state_json={"noop": {"output": {"value": "legacy"}}},
        lease_epoch=running.lease_epoch,
    )
    pausing = await store.transition_run(
        running.id,
        expected_state_version=running.state_version,
        lease_epoch=running.lease_epoch,
        status="pausing",
    )
    await store.transition_run(
        pausing.id,
        expected_state_version=pausing.state_version,
        lease_epoch=pausing.lease_epoch,
        status="paused",
    )
    await sqlite_session.commit()

    bind = sqlite_session.bind
    assert bind is not None
    service = WorkflowApplicationService(
        async_sessionmaker(bind, expire_on_commit=False),
        workflow_registry=_registry(definition),
        runtime_build_sha="dev",
    )
    response = await service.resume(claimed.id, actor_user_id=owner)
    assert response.status == "queued"
    assert response.compatibility == "compatible"
    migrated = await CheckpointStore(sqlite_session).latest(claimed.id)
    assert migrated is not None and migrated.id != checkpoint.id
    assert migrated.checkpoint_schema_version == "typed-state-v1"
    assert migrated.state_json["node_outputs"]["noop"]["output"]["value"] == "legacy"
    audits = list(
        (
            await sqlite_session.execute(
                select(WorkflowAuditLog.action).where(WorkflowAuditLog.workflow_run_id == claimed.id)
            )
        ).scalars().all()
    )
    assert "checkpoint_migrated" in audits


def test_budget_provider_limit_policy_and_metrics_are_deterministic() -> None:
    raw = {"limits": {"max_tokens": 10, "provider_max_tokens": {"xfyun": 4}}}
    reserved = BudgetController.reserve_node(raw, node_id="producer", estimated_tokens=4)
    assert BudgetController.snapshot(reserved).usage.reserved_tokens == 4
    settled = BudgetController.record_provider_usage(
        reserved,
        node_id="producer",
        provider="xfyun",
        usage={"prompt_tokens": 2, "completion_tokens": 2, "total_tokens": 4},
    )
    snapshot = BudgetController.snapshot(settled)
    assert snapshot.usage.total_tokens == 4
    assert snapshot.usage.reserved_tokens == 0

    policy = PolicyEngine()
    assert policy.decide(ToolDefinition("lookup", "read-only", permission="ALLOW")).outcome == "ALLOW"
    assert policy.decide(ToolDefinition("publish", "high impact", risk_level="high", permission="ASK")).outcome == "ASK"
    assert policy.decide(ToolDefinition("filesystem_read", "forbidden", permission="ALLOW")).outcome == "DENY"


@pytest.mark.anyio
async def test_metrics_exposes_outbox_and_audit_counts(sqlite_session: Any) -> None:
    definition = WorkflowDefinition(
        name="metrics_probe_v1",
        version=1,
        input_model=_Input,
        output_model=_Output,
        nodes=(NodeDefinition("noop", "action", action_name="Noop"),),
    )
    store, claimed = await _claimed_run(sqlite_session, definition)
    await EventStore(sqlite_session).append_event(
        claimed.id,
        "trace",
        {"phase": "probe"},
        lease_epoch=claimed.lease_epoch,
    )
    await ApprovalStore(sqlite_session).audit(claimed.id, action="metrics_probe")
    await sqlite_session.commit()
    metrics = await RuntimeMetricsService(sqlite_session).snapshot(workflow_run_id=claimed.id)
    assert metrics["outbox_unpublished"] == 1
    assert metrics["trace_events"] == 1
    assert metrics["audit_events"] == 1
