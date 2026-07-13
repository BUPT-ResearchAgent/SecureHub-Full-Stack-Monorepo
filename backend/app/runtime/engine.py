# Status: real

"""The unique production execution authority for SecureHub workflows."""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.workflow_runtime import WorkflowEvidenceSnapshot, WorkflowStepAttempt
from app.runtime.contracts import ArtifactRef, ErrorCode, EvidenceRef, ExecutionMode, ProviderSelection, RunStatus, StepStatus
from app.runtime.harness.contracts import CandidateOutput, SkillDefinition
from app.runtime.harness.context import ExecutionCancelled, ExecutionContext
from app.runtime.harness.executor import SkillExecutionError, SkillExecutor
from app.runtime.budget import BudgetController, BudgetExceeded
from app.runtime.ports.run_recorder import AgentRunRecorder, RunRecordingError
from app.runtime.persistence.approval_store import ApprovalStore
from app.runtime.state_machine import InvalidStateTransition, SecureHubStateMachine
from app.runtime.workflow_definition import NodeDefinition, WorkflowDefinition
from app.runtime.workflow_registry import WorkflowRegistry
from app.runtime.typed_state import TypedWorkflowState


ActionHandler = Callable[[str, dict[str, Any], dict[str, Any], ExecutionContext], Awaitable[dict[str, Any]]]


class RuntimeEngineError(RuntimeError):
    def __init__(
        self,
        code: ErrorCode | str,
        message: str,
        *,
        blocked: bool = False,
        node_id: str | None = None,
    ) -> None:
        self.code = str(code)
        self.blocked = blocked
        self.node_id = node_id
        super().__init__(message)


@dataclass(frozen=True)
class ExecutionResult:
    workflow_run_id: UUID
    status: str
    output: dict[str, Any] | None = None


class RuntimeEngine:
    """Runs a claimed durable root; it never owns an HTTP request lifecycle."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        workflow_registry: WorkflowRegistry,
        skill_catalog: dict[tuple[str, str], SkillDefinition],
        run_store: Any,
        event_store: Any,
        skill_executor: SkillExecutor,
        run_recorder: AgentRunRecorder | None = None,
        action_handler: ActionHandler | None = None,
        checkpoint_store: Any | None = None,
        provider_call_store: Any | None = None,
        runtime_build_sha: str = "dev",
        parallel_sessionmaker: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self.session = session
        self.workflow_registry = workflow_registry
        self.skill_catalog = skill_catalog
        self.run_store = run_store
        self.event_store = event_store
        self.skill_executor = skill_executor
        self.run_recorder = run_recorder or AgentRunRecorder(session)
        self.action_handler = action_handler or self._missing_action
        self.checkpoint_store = checkpoint_store
        self.provider_call_store = provider_call_store
        self.runtime_build_sha = runtime_build_sha
        self.parallel_sessionmaker = parallel_sessionmaker

    async def execute(self, workflow_run_id: UUID | str, *, lease_owner: str | None = None) -> ExecutionResult:
        run = await self.run_store.get_run(workflow_run_id)
        assert run is not None
        if SecureHubStateMachine.is_terminal_run(run.status):
            return ExecutionResult(run.id, run.status, dict(run.output_ref or {}) or None)
        if run.lease_epoch < 1:
            raise RuntimeEngineError(ErrorCode.LEASE_FENCED, "RuntimeEngine requires a claimed lease")
        if lease_owner is not None and run.lease_owner != lease_owner:
            raise RuntimeEngineError(ErrorCode.LEASE_FENCED, "claimed lease owner does not match RuntimeEngine owner")

        try:
            definition = self.workflow_registry.get(run.workflow_name, self._workflow_version(run.workflow_version))
        except Exception as exc:
            return await self._fail_root(run, ErrorCode.INVALID_WORKFLOW, "registered workflow definition is unavailable")

        try:
            root_input = definition.input_model.model_validate(dict(run.input_payload or {})).model_dump(mode="json")
        except ValidationError:
            return await self._fail_root(run, ErrorCode.INVALID_INPUT, "workflow input failed definition validation")

        if run.cancel_requested_at is not None or run.status == RunStatus.CANCELLING:
            return await self._cancel_root(run)

        state, attempts = await self._recover_state(
            run.id,
            workflow_schema_version=definition.checkpoint_schema_version,
        )
        try:
            await self._recover_completed_provider_results(
                run,
                definition,
                root_input,
                state,
                attempts,
            )
        except RuntimeEngineError as exc:
            return await self._fail_root(run, exc.code, str(exc), blocked=exc.blocked)
        # Pause is cooperative: a request may arrive while another process is
        # inside a provider stream, but RuntimeEngine converges it to paused at
        # the next durable boundary before starting any further node.
        if run.status == RunStatus.PAUSING:
            return await self._pause_root(run, definition, state)

        if run.status != RunStatus.RUNNING:
            try:
                SecureHubStateMachine.assert_run_transition(run.status, RunStatus.RUNNING)
                run = await self.run_store.transition_run(
                    run.id,
                    expected_state_version=run.state_version,
                    lease_epoch=run.lease_epoch,
                    status=RunStatus.RUNNING,
                    event_type="progress",
                    event_payload=self._root_payload(run, {"root_status": "running", "status": "running", "percentage": 1}),
                )
                await self.session.commit()
            except Exception as exc:
                await self.session.rollback()
                raise RuntimeEngineError(ErrorCode.LEASE_FENCED, "unable to start claimed root") from exc

        initial = definition.initial_nodes()
        if len(initial) != 1:
            return await self._fail_root(run, ErrorCode.INVALID_WORKFLOW, "workflow requires one deterministic initial node")
        current: NodeDefinition | None = initial[0]
        # Rebuild the bounded rework counter from durable step attempts after
        # a worker crash. A recovered root must not silently gain extra model
        # retries because its process-local counter was reset.
        rework_count = max(0, max(attempts.values(), default=1) - 1)

        while current is not None:
            run = await self.run_store.get_run(run.id)
            assert run is not None
            if run.cancel_requested_at is not None or run.status == RunStatus.CANCELLING:
                return await self._cancel_root(run)
            if SecureHubStateMachine.is_terminal_run(run.status):
                return ExecutionResult(run.id, run.status, dict(run.output_ref or {}) or None)
            if run.status == RunStatus.PAUSING:
                return await self._pause_root(run, definition, state)

            if current.node_id in state:
                candidate_state = state[current.node_id]
            else:
                try:
                    candidate_state = await self._execute_node(
                        run=run,
                        definition=definition,
                        node=current,
                        root_input=root_input,
                        state=state,
                        attempt=attempts.get(current.node_id, 0) + 1,
                    )
                except ExecutionCancelled:
                    return await self._cancel_root(await self.run_store.get_run(run.id))
                except RuntimeEngineError as exc:
                    if exc.code in {ErrorCode.PROVIDER_UNKNOWN_OUTCOME, ErrorCode.APPROVAL_REQUIRED}:
                        return await self._wait_for_approval(run, exc)
                    return await self._fail_root(run, exc.code, str(exc), blocked=exc.blocked)
                except Exception as exc:  # noqa: BLE001 - terminal convergence boundary
                    return await self._fail_root(run, ErrorCode.INTERNAL, "runtime node execution failed")
                state[current.node_id] = candidate_state
                attempts[current.node_id] = attempts.get(current.node_id, 0) + 1
                await self._write_checkpoint(run, definition, state)

            condition: str | None = None
            if current.skill_name == "QualityCheck":
                output = candidate_state.get("output", {})
                if bool(output.get("accept")):
                    condition = "accept"
                else:
                    condition = "defect"
                    defects = self._normalise_defects(output.get("defects"))
                    repeated_defect = state.record_defects(defects, node_id=current.node_id)
                    if repeated_defect or any(item["code"] == "safety_violation" for item in defects):
                        return await self._fail_root(
                            run,
                            ErrorCode.QUALITY_REJECTED,
                            "QualityCheck produced a repeated or non-reworkable defect",
                            blocked=True,
                        )
                    if rework_count >= definition.max_rework_attempts:
                        return await self._fail_root(
                            run,
                            ErrorCode.QUALITY_REJECTED,
                            "QualityCheck rejected candidate after bounded rework",
                            blocked=True,
                        )
                    successors = definition.rework_targets(current.node_id, defects)
                    if not successors:
                        return await self._fail_root(
                            run,
                            ErrorCode.QUALITY_REJECTED,
                            "QualityCheck rejected candidate without a deterministic rework route",
                            blocked=True,
                        )
                    rework_count += 1
                    SecureHubStateMachine.assert_run_transition(run.status, RunStatus.REWORKING)
                    run = await self.run_store.transition_run(
                        run.id,
                        expected_state_version=run.state_version,
                        lease_epoch=run.lease_epoch,
                        status=RunStatus.REWORKING,
                        event_type="progress",
                        event_payload=self._root_payload(
                            run,
                            {"root_status": "reworking", "status": "reworking", "rework_attempt": rework_count},
                        ),
                    )
                    await self.session.commit()
                    SecureHubStateMachine.assert_run_transition(run.status, RunStatus.RUNNING)
                    run = await self.run_store.transition_run(
                        run.id,
                        expected_state_version=run.state_version,
                        lease_epoch=run.lease_epoch,
                        status=RunStatus.RUNNING,
                        event_type="progress",
                        event_payload=self._root_payload(run, {"root_status": "running", "status": "running", "rework_attempt": rework_count}),
                    )
                    await self.session.commit()
                    # The defect edge intentionally invalidates the prior
                    # candidate. Leaving it in ``state`` would cause the
                    # loop below to skip the producer and re-check the same
                    # rejected output instead of creating a new attempt.
                    state.pop(current.node_id, None)
                    for rework_target in successors:
                        state.pop(rework_target.node_id, None)
                    if len(successors) == 1:
                        current = successors[0]
                        continue
                    try:
                        fanout_results = await self._execute_fanout(
                            run=run,
                            definition=definition,
                            nodes=successors,
                            root_input=root_input,
                            state=state,
                            attempts=attempts,
                        )
                    except RuntimeEngineError as exc:
                        return await self._fail_root(run, exc.code, str(exc), blocked=exc.blocked)
                    for node_id, branch_state in fanout_results.items():
                        state[node_id] = branch_state
                        attempts[node_id] = attempts.get(node_id, 0) + 1
                    await self._write_checkpoint(run, definition, state)
                    join = definition.common_join(tuple(node.node_id for node in successors))
                    if join is None or join.node_id != current.node_id:
                        return await self._fail_root(
                            run,
                            ErrorCode.INVALID_WORKFLOW,
                            "parallel rework branches must rejoin the QualityCheck node",
                        )
                    current = join
                    continue

            successors = definition.successors(current.node_id, condition=condition)
            if len(successors) > 1:
                # A resumed root reconstructs successful branches from durable
                # step attempts. Do not issue a second provider/action call for
                # those branches merely because their common predecessor is the
                # current node again after recovery.
                pending_successors = tuple(
                    node for node in successors if node.node_id not in state
                )
                if pending_successors:
                    try:
                        fanout_results = await self._execute_fanout(
                            run=run,
                            definition=definition,
                            nodes=pending_successors,
                            root_input=root_input,
                            state=state,
                            attempts=attempts,
                        )
                    except RuntimeEngineError as exc:
                        return await self._fail_root(run, exc.code, str(exc), blocked=exc.blocked)
                    for node_id, branch_state in fanout_results.items():
                        state[node_id] = branch_state
                        attempts[node_id] = attempts.get(node_id, 0) + 1
                    await self._write_checkpoint(run, definition, state)
                join = definition.common_join(tuple(node.node_id for node in successors))
                if join is None:
                    return await self._fail_root(
                        run,
                        ErrorCode.INVALID_WORKFLOW,
                        "fan-out branches require one deterministic shared join",
                    )
                current = join
                continue
            current = successors[0] if successors else None

        run = await self.run_store.get_run(run.id)
        assert run is not None
        final_output = self._final_output(definition, state)
        try:
            SecureHubStateMachine.assert_run_transition(run.status, RunStatus.SUCCEEDED)
            run = await self.run_store.transition_run(
                run.id,
                expected_state_version=run.state_version,
                lease_epoch=run.lease_epoch,
                status=RunStatus.SUCCEEDED,
                changes={"output_ref": final_output},
                event_type="done",
                event_payload=self._root_payload(
                    run,
                    {
                        "status": "succeeded",
                        "final_output_ref": final_output.get("ref"),
                        "quality_score": final_output.get("quality_score"),
                    },
                ),
            )
            await self.session.commit()
            return ExecutionResult(run.id, run.status, final_output)
        except Exception as exc:
            await self.session.rollback()
            raise RuntimeEngineError(ErrorCode.LEASE_FENCED, "unable to converge root terminal state") from exc

    async def _execute_node(
        self,
        *,
        run: Any,
        definition: WorkflowDefinition,
        node: NodeDefinition,
        root_input: dict[str, Any],
        state: TypedWorkflowState,
        attempt: int,
        reserve_budget: bool = True,
    ) -> dict[str, Any]:
        if reserve_budget:
            try:
                await self._reserve_node_budget(run, node)
            except BudgetExceeded as exc:
                raise RuntimeEngineError(ErrorCode.BUDGET_EXCEEDED, str(exc), blocked=True) from exc
        if node.kind == "action":
            return await self._execute_action(run, definition, node, root_input, state, attempt)
        skill = self._resolve_skill(definition, node, root_input)
        projected_state = state.project(definition.input_sources_for(node.node_id))
        mapped_input = node.input_mapper(root_input, projected_state) if node.input_mapper else dict(root_input)
        step = await self.run_store.create_step_attempt(
            workflow_run_id=run.id,
            node_id=node.node_id,
            attempt=attempt,
            agent_name=skill.agent_name,
            skill_name=skill.name,
            skill_version=str(skill.version),
            skill_definition_digest=skill.definition_digest,
            prompt_version=skill.prompt_version,
            prompt_digest=hashlib.sha256(skill.prompt_template.encode("utf-8")).hexdigest(),
            input_ref={"input_digest": self._digest(mapped_input)},
            status=StepStatus.PENDING,
            lease_epoch=run.lease_epoch,
        )
        context = self._execution_context(run, step, node)
        agent_run_id: UUID
        started = time.perf_counter()
        try:
            agent_run_id = await self.run_recorder.start(
                workflow_run_id=run.id,
                step_attempt_id=step.id,
                workflow_name=definition.name,
                user_id=run.user_id,
                agent_name=skill.agent_name,
                skill_name=skill.name,
                attempt=attempt,
                provider=context.provider_selection.requested_provider,
                model=context.provider_selection.requested_model,
                input_summary={"workflow_run_id": str(run.id), "step_attempt_id": str(step.id), "input_digest": self._digest(mapped_input)},
                require_resolution=run.mode == ExecutionMode.REAL,
            )
            step = await self.run_store.transition_step_attempt(
                step.id,
                expected_state_version=step.state_version,
                lease_epoch=run.lease_epoch,
                status=StepStatus.RUNNING,
                changes={"agent_run_id": agent_run_id},
                event_type="trace",
                event_payload=self._node_payload(
                    run,
                    node,
                    step,
                    {"status": "running", "agent_run_id": str(agent_run_id)},
                ),
                agent_run_id=agent_run_id,
            )
            # This commit is the precondition for RAG and Provider I/O.
            await self.session.commit()
        except Exception as exc:
            await self.session.rollback()
            raise RuntimeEngineError(ErrorCode.AGENT_RUN_PERSIST_FAILED, "running agent_run could not be persisted") from exc

        context = self._execution_context(run, step, node, agent_run_id=agent_run_id)
        try:
            candidate = await self.skill_executor.execute(skill, mapped_input, context)
            output = candidate.output_payload()
            try:
                await self._settle_provider_budget(
                    run,
                    node=node,
                    provider=candidate.actual_provider or context.provider_selection.requested_provider or "unknown",
                    usage=candidate.usage,
                )
            except BudgetExceeded as exc:
                raise RuntimeEngineError(ErrorCode.BUDGET_EXCEEDED, str(exc), blocked=True) from exc
            evidence_ids = self._uuid_evidence_ids(candidate)
            await self.run_recorder.succeed(
                agent_run_id,
                output_summary=self._compact_output(output),
                evidence_chunk_ids=evidence_ids,
                quality_score=self._quality_score(output),
                duration_ms=int((time.perf_counter() - started) * 1000),
                token_usage=candidate.usage,
            )
            step = await self.run_store.transition_step_attempt(
                step.id,
                expected_state_version=step.state_version,
                lease_epoch=run.lease_epoch,
                status=StepStatus.SUCCEEDED,
                changes={
                    "output_ref": {
                        "candidate_output": output,
                        "output_digest": self._digest(output),
                        "provider_call_id": candidate.provider_call_id,
                        "evidence_snapshot_ids": [str(item.evidence_snapshot_id) for item in candidate.evidence],
                    },
                    "quality_score": self._quality_score(output),
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                },
                event_type="trace",
                event_payload=self._node_payload(
                    run,
                    node,
                    step,
                    {
                        "status": "succeeded",
                        "agent_run_id": str(agent_run_id),
                        "quality_score": self._quality_score(output),
                    },
                ),
                agent_run_id=agent_run_id,
            )
            await self.session.commit()
            return {
                "output": output,
                "agent_run_id": str(agent_run_id),
                "step_attempt_id": str(step.id),
                "evidence_snapshot_ids": [str(item.evidence_snapshot_id) for item in candidate.evidence],
                "evidence_refs": [item.model_dump(mode="json") for item in candidate.evidence],
                "quality_score": self._quality_score(output),
                "usage": candidate.usage,
                "provider_call_id": candidate.provider_call_id,
                "stream_attempt": candidate.stream_attempt,
            }
        except ExecutionCancelled:
            await self._mark_step_cancelled(run, step, agent_run_id, started)
            raise
        except SkillExecutionError as exc:
            await self._mark_step_failed(run, step, agent_run_id, started, exc.code, str(exc), blocked=False)
            raise RuntimeEngineError(exc.code, str(exc)) from exc
        except RunRecordingError as exc:
            await self._mark_step_failed(run, step, agent_run_id, started, ErrorCode.AGENT_RUN_PERSIST_FAILED, str(exc), blocked=False)
            raise RuntimeEngineError(ErrorCode.AGENT_RUN_PERSIST_FAILED, str(exc)) from exc
        except Exception as exc:
            await self._mark_step_failed(run, step, agent_run_id, started, ErrorCode.INTERNAL, "skill execution failed", blocked=False)
            raise RuntimeEngineError(ErrorCode.INTERNAL, "skill execution failed") from exc

    async def _execute_fanout(
        self,
        *,
        run: Any,
        definition: WorkflowDefinition,
        nodes: tuple[NodeDefinition, ...],
        root_input: dict[str, Any],
        state: TypedWorkflowState,
        attempts: dict[str, int],
    ) -> dict[str, dict[str, Any]]:
        """Execute independent branches with isolated DB sessions when available.

        SQLAlchemy sessions are not safe for concurrent use.  Production
        wiring supplies a sessionmaker, so each fan-out branch owns a separate
        transaction/session while the shared root lease epoch fences every
        write.  Unit callers without a sessionmaker retain deterministic
        sequential behaviour rather than sharing a session unsafely.
        """
        if not nodes:
            return {}
        base_state = TypedWorkflowState.from_checkpoint(state.checkpoint_payload())
        dialect = getattr(getattr(self.session, "bind", None), "dialect", None)
        can_parallel = (
            self.parallel_sessionmaker is not None
            and len(nodes) > 1
            and getattr(dialect, "name", None) == "postgresql"
            and all(node.kind == "skill" for node in nodes)
        )
        if not can_parallel:
            results: dict[str, dict[str, Any]] = {}
            for node in nodes:
                branch_state = TypedWorkflowState.from_checkpoint(base_state.checkpoint_payload())
                results[node.node_id] = await self._execute_node(
                    run=run,
                    definition=definition,
                    node=node,
                    root_input=root_input,
                    state=branch_state,
                    attempt=attempts.get(node.node_id, 0) + 1,
                )
            return results

        # Reserve all branch capacity before any provider can observe a call.
        # The reservations use the parent session and therefore cannot race on
        # the root's ledger. Branch sessions settle their actual usage under a
        # fenced row lock below.
        try:
            for node in nodes:
                await self._reserve_node_budget(run, node)
        except BudgetExceeded as exc:
            raise RuntimeEngineError(ErrorCode.BUDGET_EXCEEDED, str(exc), blocked=True) from exc

        concurrency = min(
            definition.max_parallel_nodes,
            *(node.max_concurrency or definition.max_parallel_nodes for node in nodes),
        )
        semaphore = asyncio.Semaphore(concurrency)

        async def execute_branch(node: NodeDefinition) -> tuple[str, dict[str, Any]]:
            async with semaphore:
                async with self.parallel_sessionmaker() as branch_session:
                    branch_engine = self._branch_engine(branch_session)
                    branch_run = await branch_engine.run_store.get_run(run.id)
                    if branch_run is None:
                        raise RuntimeEngineError(ErrorCode.RUN_NOT_FOUND, "fan-out root disappeared")
                    branch_state = TypedWorkflowState.from_checkpoint(base_state.checkpoint_payload())
                    result = await branch_engine._execute_node(
                        run=branch_run,
                        definition=definition,
                        node=node,
                        root_input=root_input,
                        state=branch_state,
                        attempt=attempts.get(node.node_id, 0) + 1,
                        reserve_budget=False,
                    )
                    await branch_session.commit()
                    return node.node_id, result

        values = await asyncio.gather(*(execute_branch(node) for node in nodes))
        return dict(values)

    def _branch_engine(self, session: AsyncSession) -> "RuntimeEngine":
        """Create a per-branch facade without introducing a second Runtime."""
        from app.runtime.harness.executor import SkillExecutor
        from app.runtime.persistence.checkpoint_store import CheckpointStore
        from app.runtime.persistence.event_store import EventStore
        from app.runtime.persistence.evidence_snapshot_store import EvidenceSnapshotStore
        from app.runtime.persistence.provider_call_store import ProviderCallStore
        from app.runtime.persistence.run_store import RunStore
        from app.runtime.ports.run_recorder import AgentRunRecorder

        parent_executor = self.skill_executor
        executor = SkillExecutor(
            retriever=getattr(parent_executor, "_retriever", None),
            provider_resolver=getattr(parent_executor, "_provider_resolver", None),
            evidence_snapshot_store=EvidenceSnapshotStore(session),
            provider_call_store=ProviderCallStore(session),
            context_builder=getattr(parent_executor, "_context_builder", None),
            provider_policy=getattr(parent_executor, "_provider_policy", None),
            fallback_provider_resolver=getattr(parent_executor, "_fallback_provider_resolver", None),
        )
        events = EventStore(session)
        return RuntimeEngine(
            session=session,
            workflow_registry=self.workflow_registry,
            skill_catalog=self.skill_catalog,
            run_store=RunStore(session, event_store=events),
            event_store=events,
            skill_executor=executor,
            run_recorder=AgentRunRecorder(session),
            action_handler=self.action_handler,
            checkpoint_store=CheckpointStore(session),
            provider_call_store=ProviderCallStore(session),
            runtime_build_sha=self.runtime_build_sha,
            parallel_sessionmaker=self.parallel_sessionmaker,
        )

    async def _execute_action(
        self,
        run: Any,
        definition: WorkflowDefinition,
        node: NodeDefinition,
        root_input: dict[str, Any],
        state: TypedWorkflowState,
        attempt: int,
    ) -> dict[str, Any]:
        if node.approval_required or node.risk_level == "high":
            approvals = ApprovalStore(self.session)
            if not await approvals.has_approved(
                workflow_run_id=run.id,
                kind="workflow_action",
                node_id=node.node_id,
            ):
                raise RuntimeEngineError(
                    ErrorCode.APPROVAL_REQUIRED,
                    "high-risk workflow action requires explicit approval",
                    node_id=node.node_id,
                )
        step = await self._recover_action_step(run, node)
        if step is None:
            step = await self.run_store.create_step_attempt(
                workflow_run_id=run.id,
                node_id=node.node_id,
                attempt=attempt,
                status=StepStatus.PENDING,
                lease_epoch=run.lease_epoch,
            )
            step = await self.run_store.transition_step_attempt(
                step.id,
                expected_state_version=step.state_version,
                lease_epoch=run.lease_epoch,
                status=StepStatus.RUNNING,
                event_type="progress",
                event_payload=self._node_payload(run, node, step, {"node_status": "running", "percentage": 85}),
            )
            await self.session.commit()
        context = self._execution_context(run, step, node)
        try:
            projected_state = state.project(definition.input_sources_for(node.node_id))
            output = await self.action_handler(node.action_name or "", root_input, projected_state, context)
            step = await self.run_store.transition_step_attempt(
                step.id,
                expected_state_version=step.state_version,
                lease_epoch=run.lease_epoch,
                status=StepStatus.SUCCEEDED,
                changes={"output_ref": output},
                event_type="progress",
                event_payload=self._node_payload(run, node, step, {"node_status": "succeeded", "percentage": 95}),
                # Artifact visibility is controlled by ArtifactSaga's own
                # hidden `artifact` outbox row. Action lifecycle progress is
                # always public; hiding ordinary persistence actions creates
                # an unfillable public SSE sequence gap before `done`.
                publish_ready=True,
            )
            await self.session.commit()
            return {
                "output": output,
                "step_attempt_id": str(step.id),
                "artifact_refs": self._artifact_refs_from_output(output),
            }
        except Exception as exc:
            # Do not expose a storage/provider response body, but retain the
            # exception category so an operator can distinguish a persistence
            # conflict from an external artifact boundary failure.
            message = f"workflow action failed ({exc.__class__.__name__})"
            await self._mark_step_failed(
                run,
                step,
                None,
                time.perf_counter(),
                ErrorCode.ARTIFACT_PERSIST_FAILED,
                message,
                blocked=True,
            )
            raise RuntimeEngineError(ErrorCode.ARTIFACT_PERSIST_FAILED, message, blocked=True) from exc

    async def _recover_action_step(self, run: Any, node: NodeDefinition) -> Any | None:
        """Adopt an interrupted deterministic action instead of creating attempt N+1.

        Artifact actions may have committed a staging/active effect before a
        worker dies or a cooperative pause reaches a boundary. Their durable
        step identity is the recovery key, just as a completed ProviderCall
        is for skill execution.
        """
        step = await self.session.scalar(
            select(WorkflowStepAttempt)
            .where(
                WorkflowStepAttempt.workflow_run_id == run.id,
                WorkflowStepAttempt.node_id == node.node_id,
                WorkflowStepAttempt.status.in_((StepStatus.PENDING, StepStatus.RUNNING)),
            )
            .order_by(WorkflowStepAttempt.attempt.desc())
            .limit(1)
        )
        if step is None:
            return None
        step = await self.run_store.adopt_step_attempt(step.id, lease_epoch=run.lease_epoch)
        if step.status == StepStatus.PENDING:
            step = await self.run_store.transition_step_attempt(
                step.id,
                expected_state_version=step.state_version,
                lease_epoch=run.lease_epoch,
                status=StepStatus.RUNNING,
                event_type="progress",
                event_payload=self._node_payload(
                    run,
                    node,
                    step,
                    {"node_status": "running", "recovered_action_attempt": True, "percentage": 85},
                ),
            )
            await self.session.commit()
        return step

    async def _mark_step_failed(
        self,
        run: Any,
        step: Any,
        agent_run_id: UUID | None,
        started: float,
        code: ErrorCode | str,
        message: str,
        *,
        blocked: bool,
    ) -> None:
        try:
            if agent_run_id is not None:
                await self.run_recorder.fail(
                    agent_run_id,
                    error_code=str(code),
                    error_summary={"code": str(code), "message": message[:400]},
                    duration_ms=int((time.perf_counter() - started) * 1000),
                )
            await self.run_store.transition_step_attempt(
                step.id,
                expected_state_version=step.state_version,
                lease_epoch=run.lease_epoch,
                status=StepStatus.BLOCKED if blocked else StepStatus.FAILED,
                changes={"error_code": str(code), "error": {"code": str(code), "message": message[:400]}},
                event_type="trace",
                event_payload={
                    "node_id": step.node_id,
                    "agent_name": step.agent_name,
                    "skill_name": step.skill_name,
                    "step_attempt_id": str(step.id),
                    "mode": run.mode,
                    "status": "blocked" if blocked else "failed",
                    "code": str(code),
                },
                agent_run_id=agent_run_id,
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()

    async def _mark_step_cancelled(self, run: Any, step: Any, agent_run_id: UUID, started: float) -> None:
        try:
            await self.run_recorder.fail(
                agent_run_id,
                error_code=ErrorCode.RUN_CANCELLED.value,
                error_summary={"code": ErrorCode.RUN_CANCELLED.value},
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            await self.run_store.transition_step_attempt(
                step.id,
                expected_state_version=step.state_version,
                lease_epoch=run.lease_epoch,
                status=StepStatus.CANCELLED,
                event_type="trace",
                event_payload={"node_id": step.node_id, "status": "cancelled", "agent_run_id": str(agent_run_id)},
                agent_run_id=agent_run_id,
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()

    async def _fail_root(
        self,
        run: Any | None,
        code: ErrorCode | str,
        message: str,
        *,
        blocked: bool = False,
    ) -> ExecutionResult:
        if run is None:
            raise RuntimeEngineError(code, message, blocked=blocked)
        target = RunStatus.BLOCKED if blocked else RunStatus.FAILED
        try:
            if run.status != target:
                SecureHubStateMachine.assert_run_transition(run.status, target)
            run = await self.run_store.transition_run(
                run.id,
                expected_state_version=run.state_version,
                lease_epoch=run.lease_epoch,
                status=target,
                changes={"error": {"code": str(code), "message": message[:400]}},
                event_type="error",
                event_payload=self._root_payload(run, {"code": str(code), "message": message[:400], "recoverable": False, "terminal": True, "status": target.value}),
            )
            await self.session.commit()
            return ExecutionResult(run.id, run.status, None)
        except Exception:
            await self.session.rollback()
            raise RuntimeEngineError(code, message, blocked=blocked)

    async def _wait_for_approval(self, run: Any, error: RuntimeEngineError) -> ExecutionResult:
        try:
            approval_kind = (
                "provider_retry" if error.code == ErrorCode.PROVIDER_UNKNOWN_OUTCOME else "workflow_action"
            )
            approval = await ApprovalStore(self.session).request(
                workflow_run_id=run.id,
                node_id=error.node_id,
                kind=approval_kind,
                request={"code": error.code, "message": str(error)[:400]},
            )
            if run.status != RunStatus.WAITING_APPROVAL:
                SecureHubStateMachine.assert_run_transition(run.status, RunStatus.WAITING_APPROVAL)
                run = await self.run_store.transition_run(
                    run.id,
                    expected_state_version=run.state_version,
                    lease_epoch=run.lease_epoch,
                    status=RunStatus.WAITING_APPROVAL,
                    changes={"error": {"code": error.code, "message": str(error)[:400]}},
                    event_type="progress",
                    event_payload=self._root_payload(
                        run,
                        {
                            "root_status": "waiting_approval",
                            "status": "waiting_approval",
                            "code": error.code,
                            "approval_id": str(approval.id),
                            "approval_kind": approval.kind,
                        },
                    ),
                )
                await self.session.commit()
            return ExecutionResult(run.id, run.status, None)
        except Exception:
            await self.session.rollback()
            raise

    async def _cancel_root(self, run: Any | None) -> ExecutionResult:
        if run is None:
            raise RuntimeEngineError(ErrorCode.RUN_NOT_FOUND, "workflow run was not found")
        try:
            if run.status != RunStatus.CANCELLED:
                SecureHubStateMachine.assert_run_transition(run.status, RunStatus.CANCELLED)
                run = await self.run_store.transition_run(
                    run.id,
                    expected_state_version=run.state_version,
                    lease_epoch=run.lease_epoch,
                    status=RunStatus.CANCELLED,
                    event_type="done",
                    event_payload=self._root_payload(run, {"status": "cancelled", "final_output_ref": None}),
                )
                await self.session.commit()
            return ExecutionResult(run.id, run.status, None)
        except Exception:
            await self.session.rollback()
            raise

    async def _pause_root(
        self,
        run: Any,
        definition: WorkflowDefinition,
        state: TypedWorkflowState,
    ) -> ExecutionResult:
        """Persist a checkpoint then converge a cooperative pause exactly once."""
        try:
            await self._write_checkpoint(run, definition, state)
            refreshed = await self.run_store.get_run(run.id)
            assert refreshed is not None
            if refreshed.status == RunStatus.PAUSED:
                return ExecutionResult(refreshed.id, refreshed.status, None)
            if refreshed.status != RunStatus.PAUSING:
                raise RuntimeEngineError(ErrorCode.LEASE_FENCED, "pause state changed before checkpoint convergence")
            SecureHubStateMachine.assert_run_transition(refreshed.status, RunStatus.PAUSED)
            paused = await self.run_store.transition_run(
                refreshed.id,
                expected_state_version=refreshed.state_version,
                lease_epoch=refreshed.lease_epoch,
                status=RunStatus.PAUSED,
                event_type="progress",
                event_payload=self._root_payload(
                    refreshed,
                    {"root_status": "paused", "status": "paused", "checkpointed": True},
                ),
            )
            await self.session.commit()
            return ExecutionResult(paused.id, paused.status, None)
        except RuntimeEngineError:
            raise
        except Exception as exc:
            await self.session.rollback()
            raise RuntimeEngineError(ErrorCode.LEASE_FENCED, "unable to converge paused root") from exc

    async def _recover_state(
        self,
        workflow_run_id: UUID,
        *,
        workflow_schema_version: str = "v1",
    ) -> tuple[TypedWorkflowState, dict[str, int]]:
        rows = list(
            (
                await self.session.execute(
                    select(WorkflowStepAttempt)
                    .where(WorkflowStepAttempt.workflow_run_id == workflow_run_id)
                    .order_by(WorkflowStepAttempt.node_id, WorkflowStepAttempt.attempt.desc())
                )
            ).scalars().all()
        )
        snapshot_rows = list(
            (
                await self.session.execute(
                    select(WorkflowEvidenceSnapshot).where(
                        WorkflowEvidenceSnapshot.workflow_run_id == workflow_run_id
                    )
                )
            ).scalars().all()
        )
        snapshot_refs = {
            str(row.id): EvidenceRef(
                evidence_snapshot_id=row.id,
                chunk_id=row.chunk_id or "",
                document_id=row.document_id,
                content_digest=row.content_digest,
                citation=self._lineage_value(row.citation),
                source=self._lineage_value(row.source),
                rights=self._lineage_value(row.rights),
            ).model_dump(mode="json")
            for row in snapshot_rows
            if row.chunk_id
        }
        state = TypedWorkflowState(workflow_schema_version=workflow_schema_version)
        attempts: dict[str, int] = {}
        for row in rows:
            attempts[row.node_id] = max(attempts.get(row.node_id, 0), row.attempt)
            if row.node_id in state or row.status != StepStatus.SUCCEEDED:
                continue
            output = dict(row.output_ref or {})
            candidate = output.get("candidate_output")
            evidence_snapshot_ids = [str(value) for value in output.get("evidence_snapshot_ids") or []]
            state[row.node_id] = {
                "output": candidate if isinstance(candidate, dict) else output,
                "step_attempt_id": str(row.id),
                "agent_run_id": str(row.agent_run_id) if row.agent_run_id else None,
                "provider_call_id": output.get("provider_call_id"),
                "evidence_snapshot_ids": evidence_snapshot_ids,
                "evidence_refs": [snapshot_refs[value] for value in evidence_snapshot_ids if value in snapshot_refs],
                "artifact_refs": self._artifact_refs_from_output(output),
                "quality_score": row.quality_score,
            }
        return state, attempts

    async def _recover_completed_provider_results(
        self,
        run: Any,
        definition: WorkflowDefinition,
        root_input: dict[str, Any],
        state: TypedWorkflowState,
        attempts: dict[str, int],
    ) -> None:
        """Finish a step from a persisted strict candidate without re-calling a provider.

        A process can die after the journaled provider completion but before
        ``workflow_step_attempts`` becomes succeeded.  The candidate stored in
        the completed journal is already schema-validated. Reusing it is the
        only recovery behaviour that does not claim an external exactly-once
        guarantee or issue a duplicate call.
        """
        if self.provider_call_store is None:
            return
        calls = await self.provider_call_store.list_completed_success_for_run(run.id)
        if not calls:
            return
        nodes = {node.node_id: node for node in definition.nodes}
        changed = False
        for call in calls:
            if call.step_attempt_id is None:
                continue
            step = await self.run_store.get_step_attempt(call.step_attempt_id, required=False)
            if step is None or step.status != StepStatus.RUNNING:
                continue
            node = nodes.get(step.node_id)
            if node is None or node.kind != "skill":
                raise RuntimeEngineError(
                    ErrorCode.INVALID_WORKFLOW,
                    "completed provider call is not associated with a skill node",
                )
            candidate_payload = dict(call.response_ref or {}).get("candidate_output")
            if not isinstance(candidate_payload, dict):
                raise RuntimeEngineError(
                    ErrorCode.AGENT_RUN_PERSIST_FAILED,
                    "completed provider result lacks a reusable strict candidate",
                )
            skill = self._resolve_skill(definition, node, root_input)
            try:
                output = skill.output_model.model_validate(candidate_payload).model_dump(mode="json")
            except ValidationError as exc:
                raise RuntimeEngineError(
                    ErrorCode.STRICT_PARSE_FAILED,
                    "completed provider candidate no longer matches its frozen schema",
                ) from exc
            step = await self.run_store.adopt_step_attempt(step.id, lease_epoch=run.lease_epoch)
            if step.agent_run_id is None:
                raise RuntimeEngineError(
                    ErrorCode.AGENT_RUN_PERSIST_FAILED,
                    "completed provider result has no running agent run",
                )
            evidence_ids = self._uuid_list(output.get("evidence_chunk_ids") or [])
            await self.run_recorder.succeed(
                step.agent_run_id,
                output_summary=self._compact_output(output),
                evidence_chunk_ids=evidence_ids,
                quality_score=self._quality_score(output),
                duration_ms=step.duration_ms,
                token_usage=dict(call.usage or {}),
            )
            step = await self.run_store.transition_step_attempt(
                step.id,
                expected_state_version=step.state_version,
                lease_epoch=run.lease_epoch,
                status=StepStatus.SUCCEEDED,
                changes={
                    "output_ref": {
                        "candidate_output": output,
                        "output_digest": self._digest(output),
                        "provider_call_id": str(call.id),
                        "evidence_snapshot_ids": list(
                            dict(call.response_ref or {}).get("evidence_snapshot_ids") or []
                        ),
                    },
                    "quality_score": self._quality_score(output),
                    "duration_ms": step.duration_ms,
                },
                event_type="trace",
                event_payload=self._node_payload(
                    run,
                    node,
                    step,
                    {
                        "status": "succeeded",
                        "agent_run_id": str(step.agent_run_id),
                        "provider_call_id": str(call.id),
                        "recovered_provider_result": True,
                        "quality_score": self._quality_score(output),
                    },
                ),
                agent_run_id=step.agent_run_id,
                provider_call_id=call.id,
            )
            state[node.node_id] = {
                "output": output,
                "agent_run_id": str(step.agent_run_id),
                "step_attempt_id": str(step.id),
                "provider_call_id": str(call.id),
                "evidence_snapshot_ids": list(
                    dict(call.response_ref or {}).get("evidence_snapshot_ids") or []
                ),
                "quality_score": self._quality_score(output),
                "usage": dict(call.usage or {}),
            }
            attempts[node.node_id] = max(attempts.get(node.node_id, 0), step.attempt)
            changed = True
        if changed:
            await self.session.commit()

    def _resolve_skill(
        self, definition: WorkflowDefinition, node: NodeDefinition, root_input: dict[str, Any]
    ) -> SkillDefinition:
        agent_name, skill_name = node.agent_name, node.skill_name
        if definition.name == "resource_generate_v1" and node.node_id == "producer":
            mapping = definition.metadata.get("producer_by_resource_type", {})
            selected = mapping.get(root_input.get("resource_type"))
            if not selected:
                raise RuntimeEngineError(ErrorCode.INVALID_INPUT, "resource type has no registered producer")
            agent_name, skill_name = selected
        if not agent_name or not skill_name:
            raise RuntimeEngineError(ErrorCode.INVALID_WORKFLOW, "skill node is missing a catalog reference")
        try:
            return self.skill_catalog[(str(agent_name), str(skill_name))]
        except KeyError as exc:
            raise RuntimeEngineError(ErrorCode.INVALID_WORKFLOW, f"unknown skill: {agent_name}.{skill_name}") from exc

    def _execution_context(self, run: Any, step: Any, node: NodeDefinition, *, agent_run_id: UUID | None = None) -> ExecutionContext:
        async def emit(event_type: str, payload: dict[str, Any]) -> None:
            event_payload = self._node_payload(run, node, step, payload)
            await self.event_store.append_event(
                run.id,
                event_type,
                event_payload,
                step_attempt_id=step.id,
                agent_run_id=agent_run_id or step.agent_run_id,
                lease_epoch=run.lease_epoch,
            )
            await self.session.commit()

        async def cancelled() -> bool:
            # PostgreSQL is checked at safe boundaries, allowing an API process
            # to cancel a stream currently owned by another Worker process.
            current = await self.run_store.get_run(run.id)
            return bool(
                current
                and (
                    current.cancel_requested_at is not None
                    or current.status == RunStatus.CANCELLING
                )
            )

        limits = dict((run.budget or {}).get("limits") or {})
        max_tokens = node.budget_tokens or limits.get("max_provider_tokens") or limits.get("max_tokens") or 800
        return ExecutionContext(
            workflow_run_id=run.id,
            step_attempt_id=step.id,
            agent_run_id=agent_run_id or step.agent_run_id or UUID(int=0),
            user_id=run.user_id,
            mode=ExecutionMode(run.mode),
            provider_selection=ProviderSelection(
                requested_provider=run.requested_provider,
                requested_model=run.requested_model,
                policy_version=run.provider_policy_version,
            ),
            lease_epoch=run.lease_epoch,
            course_id=(run.input_payload or {}).get("course_id"),
            persona_summary=str((run.input_payload or {}).get("persona_summary") or ""),
            # QualityCheck remains an explicit durable node, but its strict
            # JSON verdict is not a learner-facing stream. Keeping it
            # non-streaming prevents internal decision payloads from entering
            # resource previews and avoids an unnecessary stream boundary.
            stream=node.node_id != "quality_check",
            emit=emit,
            cancellation_requested=cancelled,
            extras={"provider_attempt": step.attempt, "max_tokens": int(max_tokens)},
        )

    async def _reserve_node_budget(self, run: Any, node: NodeDefinition) -> None:
        limits = dict((run.budget or {}).get("limits") or {})
        estimate = int(node.budget_tokens or limits.get("max_provider_tokens") or 1)
        def reserve(raw: dict[str, Any]) -> dict[str, Any]:
            BudgetController.assert_can_start_node(
                raw,
                node_id=node.node_id,
                estimated_tokens=estimate,
                node_limit_tokens=node.budget_tokens,
            )
            return BudgetController.reserve_node(
                raw,
                node_id=node.node_id,
                estimated_tokens=estimate,
            )

        await self.run_store.mutate_budget(
            run.id,
            lease_epoch=run.lease_epoch,
            mutate=reserve,
        )
        await self.session.commit()

    async def _settle_provider_budget(
        self,
        run: Any,
        *,
        node: NodeDefinition,
        provider: str,
        usage: dict[str, Any],
    ) -> None:
        def settle(raw: dict[str, Any]) -> dict[str, Any]:
            BudgetController.assert_can_start_provider(
                raw,
                provider=provider,
                estimated_tokens=0,
            )
            return BudgetController.record_provider_usage(
                raw,
                node_id=node.node_id,
                provider=provider,
                usage=usage,
            )

        await self.run_store.mutate_budget(
            run.id,
            lease_epoch=run.lease_epoch,
            mutate=settle,
        )
        await self.session.commit()

    async def _write_checkpoint(self, run: Any, definition: WorkflowDefinition, state: TypedWorkflowState) -> None:
        if self.checkpoint_store is None:
            return
        try:
            await self.checkpoint_store.save(
                workflow_run_id=run.id,
                workflow_definition_digest=definition.definition_digest,
                catalog_version=definition.catalog_version,
                checkpoint_schema_version=definition.checkpoint_schema_version,
                runtime_build_sha=self.runtime_build_sha,
                state_json=state.checkpoint_payload(),
                event_cursor=max(int(run.next_event_sequence or 1) - 1, 0),
                lease_epoch=run.lease_epoch,
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise RuntimeEngineError(ErrorCode.INTERNAL, "checkpoint persistence failed")

    @staticmethod
    async def _missing_action(
        action_name: str,
        _root_input: dict[str, Any],
        _state: dict[str, Any],
        _context: ExecutionContext,
    ) -> dict[str, Any]:
        raise RuntimeEngineError(ErrorCode.ARTIFACT_PERSIST_FAILED, f"workflow action is not registered: {action_name}")

    @staticmethod
    def _workflow_version(value: str | None) -> int:
        text = str(value or "1").removeprefix("v")
        return int(text)

    @staticmethod
    def _digest(value: Any) -> str:
        import json

        return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    @staticmethod
    def _quality_score(output: dict[str, Any]) -> float | None:
        value = output.get("quality_score")
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalise_defects(value: Any) -> list[dict[str, Any]]:
        allowed = {
            "evidence_missing",
            "fact_conflict",
            "schema_invalid",
            "instructional_mismatch",
            "citation_mismatch",
            "safety_violation",
        }
        result: list[dict[str, Any]] = []
        for item in value if isinstance(value, list) else []:
            if not isinstance(item, dict):
                continue
            code = str(item.get("code") or item.get("taxonomy") or "schema_invalid")
            result.append(
                {
                    "code": code if code in allowed else "schema_invalid",
                    "message": str(item.get("message") or item.get("reason") or code)[:400],
                    "target_node": item.get("target_node"),
                    "resource_type": item.get("resource_type"),
                }
            )
        return result or [{"code": "schema_invalid", "message": "QualityCheck returned no valid defect taxonomy"}]

    @staticmethod
    def _lineage_value(value: Any) -> str | None:
        if isinstance(value, dict):
            for key in ("value", "url", "source", "citation", "rights_note", "license"):
                if value.get(key):
                    return str(value[key])
            return None
        return str(value) if value else None

    @classmethod
    def _artifact_refs_from_output(cls, output: dict[str, Any]) -> list[dict[str, Any]]:
        """Normalise one action result or a fan-out result into typed lineage."""
        candidates: list[dict[str, Any]] = [output]
        resources = output.get("resources")
        if isinstance(resources, list):
            candidates.extend(item for item in resources if isinstance(item, dict))
        refs: list[dict[str, Any]] = []
        seen: set[str] = set()
        for candidate in candidates:
            resource_id = candidate.get("resource_id")
            if not resource_id or str(resource_id) in seen:
                continue
            seen.add(str(resource_id))
            refs.append(
                ArtifactRef(
                    resource_id=str(resource_id),
                    resource_type=str(candidate.get("resource_type") or "resource"),
                    evidence_snapshot_ids=[str(value) for value in candidate.get("evidence_snapshot_ids") or []],
                    quality_score=cls._quality_score(candidate),
                    content_digest=candidate.get("content_digest"),
                    object_key=candidate.get("object_key"),
                    parent_resource_id=candidate.get("parent_resource_id"),
                    lineage_root_id=candidate.get("lineage_root_id"),
                    version=int(candidate.get("version") or 1),
                ).model_dump(mode="json")
            )
        return refs

    @staticmethod
    def _uuid_evidence_ids(candidate: CandidateOutput) -> list[UUID]:
        values: list[UUID] = []
        for item in candidate.evidence:
            try:
                values.append(UUID(str(item.chunk_id)))
            except (TypeError, ValueError):
                continue
        return values

    @staticmethod
    def _uuid_list(values: list[Any]) -> list[UUID]:
        resolved: list[UUID] = []
        for value in values:
            try:
                resolved.append(UUID(str(value)))
            except (TypeError, ValueError):
                continue
        return resolved

    @staticmethod
    def _compact_output(output: dict[str, Any]) -> dict[str, Any]:
        excluded = {"content", "markdown", "text", "raw_response", "reasoning", "reasoning_content"}
        return {key: value for key, value in output.items() if key not in excluded}

    @staticmethod
    def _checkpoint_value(value: dict[str, Any]) -> dict[str, Any]:
        return {key: item for key, item in value.items() if key not in {"raw_response", "reasoning", "reasoning_content"}}

    def _root_payload(self, run: Any, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "mode": run.mode,
            "requested_provider": run.requested_provider,
            "requested_model": run.requested_model,
            **payload,
        }

    @staticmethod
    def _node_payload(run: Any, node: NodeDefinition, step: Any, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "node_id": node.node_id,
            "agent_name": node.agent_name,
            "skill_name": node.skill_name,
            "step_attempt_id": str(step.id),
            "mode": run.mode,
            "requested_provider": run.requested_provider,
            "requested_model": run.requested_model,
            **payload,
        }

    @staticmethod
    def _final_output(definition: WorkflowDefinition, state: TypedWorkflowState) -> dict[str, Any]:
        if "persist_artifact" in state:
            output = state["persist_artifact"].get("output", {})
            return {"ref": output.get("resource_id"), "quality_score": output.get("quality_score"), "artifact": output}
        if "persist_artifacts" in state:
            output = state["persist_artifacts"].get("output", {})
            return {
                "ref": (output.get("resource_ids") or [None])[0],
                "quality_score": output.get("quality_score"),
                "artifacts": output.get("resources", []),
            }
        last = state.get(definition.nodes[-1].node_id, {})
        return {"ref": last.get("step_attempt_id"), "output": last.get("output", {}), "quality_score": last.get("quality_score")}


__all__ = ["ExecutionResult", "RuntimeEngine", "RuntimeEngineError"]
