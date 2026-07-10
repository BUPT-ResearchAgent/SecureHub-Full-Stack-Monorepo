# Status: partial-real

"""Fixed five-agent workflow for fixture and controlled strict real runs.

The fixture path remains deterministic and non-durable.  ``mode=real`` uses
only the strict RAG/DeepSeek adapters and verifies every child ``agent_runs``
write before emitting its trace event.  The node order is intentionally fixed.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel

from app.agents._skill_helper import run_through_harness
from app.agents.career_planner.skills.build_learning_persona import (
    PROMPT_TEMPLATE as BUILD_PERSONA_PROMPT,
    BuildLearningPersona,
    BuildLearningPersonaInput,
    BuildLearningPersonaOutput,
)
from app.agents.competition_advisor.skills.generate_quiz import (
    PROMPT_TEMPLATE as GENERATE_QUIZ_PROMPT,
    GenerateQuiz,
    GenerateQuizInput,
    GenerateQuizOutput,
)
from app.agents.doc_archivist.skills.generate_course_doc import (
    PROMPT_TEMPLATE as GENERATE_DOC_PROMPT,
    GenerateCourseDoc,
    GenerateCourseDocInput,
    GenerateCourseDocOutput,
)
from app.agents.outcome_evaluator.skills.quality_check import (
    PROMPT_TEMPLATE as QUALITY_CHECK_PROMPT,
    QualityCheck,
    QualityCheckInput,
    QualityCheckOutput,
)
from app.agents.task_orchestrator.skills.generate_learning_path import (
    PROMPT_TEMPLATE as GENERATE_PATH_PROMPT,
    GenerateLearningPath,
    GenerateLearningPathInput,
    GenerateLearningPathOutput,
)
from app.runtime.harness import Harness, HarnessConfig, HarnessContext, InsufficientEvidence
from app.runtime.harness.errors import CancellationRequested, HarnessError
from app.runtime.harness.fixtures import default_evidence_fixtures, default_llm_output
from app.runtime.harness.live_adapters import (
    AgentRunPersistenceFailed,
    StrictLLMOutputInvalid,
    StrictLiveAdapters,
    StrictProviderUnavailable,
    persist_strict_agent_run,
)
from app.runtime.harness.types import EvidenceCard
from app.runtime.run_registry import RunRegistry, WorkflowRunRecord


WORKFLOW_NAME = "course_learning_minimal"
FIXTURE_PROVIDER = "fixture"
FIXTURE_MODEL = "fixture-canned"
FIXTURE_STEP_DELAY_SECONDS = 0.05


class WorkflowCancelled(RuntimeError):
    pass


InputBuilder = Callable[[WorkflowRunRecord, dict[str, dict[str, Any]]], BaseModel]
StrictPersistFn = Callable[..., Awaitable[None]]


@dataclass(frozen=True)
class WorkflowNodeDefinition:
    node_id: str
    agent_name: str
    skill_name: str
    skill_factory: Callable[[], Any]
    input_builder: InputBuilder
    prompt_template: str
    output_model: type[BaseModel]


def _topic(record: WorkflowRunRecord) -> str:
    return str(record.input_payload.get("topic") or "SQL 注入")


def _goal(record: WorkflowRunRecord) -> str:
    return str(record.input_payload.get("goal") or f"学习 {_topic(record)}")


def _as_json(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return {"value": str(value)}


def _build_persona_input(record: WorkflowRunRecord, _: dict[str, dict[str, Any]]) -> BaseModel:
    return BuildLearningPersonaInput(
        user_id=record.user_id,
        query=f"{_goal(record)}；当前主题：{_topic(record)}",
        dialogue_turns=[],
    )


def _build_path_input(record: WorkflowRunRecord, _: dict[str, dict[str, Any]]) -> BaseModel:
    return GenerateLearningPathInput(
        user_id=record.user_id,
        query=f"为 {_topic(record)} 生成个性化学习路径",
        course_id=str(record.input_payload.get("course_id") or "course-websec"),
    )


def _build_doc_input(record: WorkflowRunRecord, _: dict[str, dict[str, Any]]) -> BaseModel:
    return GenerateCourseDocInput(
        user_id=record.user_id,
        query=f"生成 {_topic(record)} 的入门课程讲解文档",
    )


def _build_quiz_input(record: WorkflowRunRecord, _: dict[str, dict[str, Any]]) -> BaseModel:
    return GenerateQuizInput(
        user_id=record.user_id,
        query=f"生成 {_topic(record)} 的证据驱动练习题",
        difficulty=2,
    )


def _build_quality_input(
    record: WorkflowRunRecord,
    outputs: dict[str, dict[str, Any]],
) -> BaseModel:
    return QualityCheckInput(
        user_id=record.user_id,
        query=f"核验 {_topic(record)} 的学习路径、课程文档和题目质量",
        artifact={
            "learning_path": outputs.get("generate_learning_path", {}),
            "course_doc": outputs.get("generate_course_doc", {}),
            "quiz": outputs.get("generate_quiz", {}),
        },
    )


NODE_DEFINITIONS: tuple[WorkflowNodeDefinition, ...] = (
    WorkflowNodeDefinition(
        node_id="build_learning_persona",
        agent_name="career_planner",
        skill_name="BuildLearningPersona",
        skill_factory=BuildLearningPersona,
        input_builder=_build_persona_input,
        prompt_template=BUILD_PERSONA_PROMPT,
        output_model=BuildLearningPersonaOutput,
    ),
    WorkflowNodeDefinition(
        node_id="generate_learning_path",
        agent_name="task_orchestrator",
        skill_name="GenerateLearningPath",
        skill_factory=GenerateLearningPath,
        input_builder=_build_path_input,
        prompt_template=GENERATE_PATH_PROMPT,
        output_model=GenerateLearningPathOutput,
    ),
    WorkflowNodeDefinition(
        node_id="generate_course_doc",
        agent_name="doc_archivist",
        skill_name="GenerateCourseDoc",
        skill_factory=GenerateCourseDoc,
        input_builder=_build_doc_input,
        prompt_template=GENERATE_DOC_PROMPT,
        output_model=GenerateCourseDocOutput,
    ),
    WorkflowNodeDefinition(
        node_id="generate_quiz",
        agent_name="competition_advisor",
        skill_name="GenerateQuiz",
        skill_factory=GenerateQuiz,
        input_builder=_build_quiz_input,
        prompt_template=GENERATE_QUIZ_PROMPT,
        output_model=GenerateQuizOutput,
    ),
    WorkflowNodeDefinition(
        node_id="quality_check",
        agent_name="outcome_evaluator",
        skill_name="QualityCheck",
        skill_factory=QualityCheck,
        input_builder=_build_quality_input,
        prompt_template=QUALITY_CHECK_PROMPT,
        output_model=QualityCheckOutput,
    ),
)


def workflow_nodes() -> list[tuple[str, str, str]]:
    return [(node.node_id, node.agent_name, node.skill_name) for node in NODE_DEFINITIONS]


async def _fixture_rag_retrieve(
    _query: str,
    *,
    domain: str,
    top_k: int,
    filters: dict[str, Any] | None = None,
) -> list[EvidenceCard]:
    del filters
    return [EvidenceCard(**item) for item in default_evidence_fixtures(domain)[:top_k]]


async def _fixture_llm_complete(
    _prompt: str,
    *,
    skill_name: str,
    stream: bool = False,
    emit: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
) -> dict[str, Any]:
    del stream, emit
    return {
        **default_llm_output(skill_name),
        "provider": FIXTURE_PROVIDER,
        "model": FIXTURE_MODEL,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }


def _fixture_harness() -> Harness:
    return Harness(rag_retrieve=_fixture_rag_retrieve, llm_complete=_fixture_llm_complete)


def _strict_harness(adapters: StrictLiveAdapters) -> Harness:
    return Harness(rag_retrieve=adapters.rag_retrieve, llm_complete=adapters.llm_complete)


def _enrich_event(
    event: dict[str, Any],
    *,
    record: WorkflowRunRecord,
    node: WorkflowNodeDefinition,
) -> dict[str, Any]:
    payload = dict(event)
    payload["workflow_run_id"] = str(record.run_id)
    payload.setdefault("node_id", node.node_id)
    payload.setdefault("agent_name", node.agent_name)
    payload.setdefault("skill_name", node.skill_name)
    payload.setdefault("mode", record.mode)
    payload.setdefault("provider", record.provider)
    payload.setdefault("model", record.model)
    if payload.get("event") == "trace":
        payload.setdefault("agent_run_id", payload.get("run_id"))
        payload.setdefault(
            "persistence",
            "agent_runs" if record.mode == "real" else "registry",
        )
    return payload


async def _raise_if_cancelled(record: WorkflowRunRecord) -> None:
    if record.cancellation_event.is_set():
        raise WorkflowCancelled("workflow cancellation requested")


def _fixture_log_run(
    registry: RunRegistry,
    record: WorkflowRunRecord,
    node: WorkflowNodeDefinition,
) -> Callable[..., Awaitable[None]]:
    async def log_run(**kwargs: Any) -> None:
        raw_run_id = kwargs.get("run_id")
        agent_run_id = raw_run_id if isinstance(raw_run_id, UUID) else None
        evidence_ids = list(kwargs.get("evidence_chunk_ids") or [])
        await registry.record_node_result(
            record.run_id,
            node.node_id,
            status=str(kwargs.get("status") or "success"),
            agent_run_id=agent_run_id,
            persistence="registry",
            duration_ms=kwargs.get("duration_ms"),
            quality_score=kwargs.get("quality_score"),
            evidence_count=len(evidence_ids),
        )

    return log_run


def _strict_log_run(
    registry: RunRegistry,
    record: WorkflowRunRecord,
    node: WorkflowNodeDefinition,
    *,
    persist_real_run: StrictPersistFn | None,
) -> Callable[..., Awaitable[None]]:
    async def log_run(**kwargs: Any) -> None:
        raw_run_id = kwargs.get("run_id")
        if not isinstance(raw_run_id, UUID):
            raise AgentRunPersistenceFailed("strict child run id must be a UUID")

        input_summary = dict(kwargs.get("input_summary") or {})
        input_summary["workflow_run_id"] = str(record.run_id)
        output_summary = dict(kwargs.get("output_summary") or {})
        evidence_ids = list(kwargs.get("evidence_chunk_ids") or [])
        status = str(kwargs.get("status") or "failed")
        persister = persist_real_run or persist_strict_agent_run
        await persister(
            run_id=raw_run_id,
            workflow_run_id=record.run_id,
            workflow_name=WORKFLOW_NAME,
            user_id=record.user_id,
            agent_name=node.agent_name,
            skill_name=node.skill_name,
            input_summary=input_summary,
            output_summary=output_summary,
            evidence_chunk_ids=evidence_ids,
            quality_score=kwargs.get("quality_score"),
            status=status,
            duration_ms=kwargs.get("duration_ms"),
            token_usage=dict(kwargs.get("token_usage") or {}),
        )
        await registry.record_node_result(
            record.run_id,
            node.node_id,
            status=status,
            agent_run_id=raw_run_id,
            persistence="agent_runs",
            duration_ms=kwargs.get("duration_ms"),
            quality_score=kwargs.get("quality_score"),
            evidence_count=len(evidence_ids),
        )

    return log_run


async def _run_node(
    registry: RunRegistry,
    record: WorkflowRunRecord,
    node: WorkflowNodeDefinition,
    outputs: dict[str, dict[str, Any]],
    *,
    persona_summary: str,
    strict_adapters: StrictLiveAdapters | None,
    persist_real_run: StrictPersistFn | None,
) -> dict[str, Any]:
    await _raise_if_cancelled(record)
    if not await registry.begin_node(record.run_id, node.node_id):
        raise WorkflowCancelled("workflow cancellation requested")

    await registry.publish(
        record.run_id,
        {
            "event": "progress",
            "workflow_run_id": str(record.run_id),
            "node_id": node.node_id,
            "agent_name": node.agent_name,
            "skill_name": node.skill_name,
            "status": "running",
            "percentage": 0,
            "mode": record.mode,
            "provider": record.provider,
            "model": record.model,
        },
    )

    if record.mode == "fixture":
        await asyncio.sleep(FIXTURE_STEP_DELAY_SECONDS)
        await _raise_if_cancelled(record)

    async def emit(event: dict[str, Any]) -> None:
        if record.cancellation_event.is_set() and event.get("event") in {"token", "artifact"}:
            raise CancellationRequested("workflow cancellation requested")
        await registry.publish(
            record.run_id,
            _enrich_event(event, record=record, node=node),
        )

    if record.mode == "fixture":
        context = HarnessContext(
            user_id=record.user_id,
            workflow_name=WORKFLOW_NAME,
            persona_summary=persona_summary,
            stream=False,
            config=HarnessConfig(min_evidence=3, mock_mode=True, llm_provider=FIXTURE_PROVIDER),
            emit=emit,
            log_run=_fixture_log_run(registry, record, node),
            course_id=str(record.input_payload.get("course_id") or "course-websec"),
        )
        harness = _fixture_harness()
        spec_overrides: dict[str, Any] = {"fallback": "error"}
    elif record.mode == "real":
        if strict_adapters is None:
            raise StrictProviderUnavailable("strict real adapters were not initialized")
        context = HarnessContext(
            user_id=record.user_id,
            workflow_name=WORKFLOW_NAME,
            persona_summary=persona_summary,
            stream=bool(record.input_payload.get("stream", True)),
            config=HarnessConfig(min_evidence=3, mock_mode=False, llm_provider="deepseek"),
            emit=emit,
            log_run=_strict_log_run(
                registry,
                record,
                node,
                persist_real_run=persist_real_run,
            ),
            course_id=str(record.input_payload.get("course_id") or "course-websec"),
            extras={"agent_run_id": uuid4()},
        )
        harness = _strict_harness(strict_adapters)
        spec_overrides = {
            "fallback": "error",
            "strict_output": True,
            "strict_log_run": True,
            "strict_quality_check": True,
        }
    else:
        raise RuntimeError(f"unsupported workflow mode: {record.mode}")

    output = await run_through_harness(
        node.skill_factory(),
        node.input_builder(record, outputs),
        context,
        prompt_template=node.prompt_template,
        output_model=node.output_model,
        agent_name=node.agent_name,
        applicable_domains=["course_websec"],
        evidence_floor=3,
        spec_overrides=spec_overrides,
        harness=harness,
    )
    await _raise_if_cancelled(record)
    return _as_json(output)


async def _mark_current_node_failed(
    registry: RunRegistry,
    record: WorkflowRunRecord,
    node: WorkflowNodeDefinition | None,
) -> None:
    if node is not None:
        await registry.record_node_result(
            record.run_id,
            node.node_id,
            status="failed",
        )


async def _publish_failure(
    registry: RunRegistry,
    record: WorkflowRunRecord,
    node: WorkflowNodeDefinition | None,
    *,
    code: str,
    message: str,
    blocked: bool = False,
) -> None:
    await _mark_current_node_failed(registry, record, node)
    await registry.mark_failed(record.run_id, code=code, message=message, blocked=blocked)
    await registry.publish(
        record.run_id,
        {
            "event": "error",
            "workflow_run_id": str(record.run_id),
            "code": code,
            "message": message,
            "recoverable": False,
            "mode": record.mode,
            "provider": record.provider,
            "model": record.model,
            "_terminal": True,
        },
    )


async def run_course_learning_minimal(
    run_id: UUID,
    registry: RunRegistry,
    *,
    strict_adapters: StrictLiveAdapters | None = None,
    persist_real_run: StrictPersistFn | None = None,
) -> None:
    """Execute the five fixed nodes in sequence and publish lifecycle events."""
    record = await registry.get(run_id)
    outputs: dict[str, dict[str, Any]] = {}
    current_node: WorkflowNodeDefinition | None = None
    persona_summary = ""

    try:
        if record.mode not in {"fixture", "real"}:
            raise RuntimeError(f"unsupported workflow mode: {record.mode}")
        if record.mode == "real":
            if record.provider != "deepseek":
                raise StrictProviderUnavailable("real mode requires provider=deepseek")
            strict_adapters = strict_adapters or StrictLiveAdapters(
                cancellation_requested=record.cancellation_event.is_set,
            )
            if strict_adapters.provider_name != "deepseek":
                raise StrictProviderUnavailable("real mode requires provider=deepseek")
            record.model = strict_adapters.model_name

        if not await registry.mark_running(run_id):
            raise WorkflowCancelled("workflow cancellation requested")

        for node in NODE_DEFINITIONS:
            current_node = node
            output = await _run_node(
                registry,
                record,
                node,
                outputs,
                persona_summary=persona_summary,
                strict_adapters=strict_adapters,
                persist_real_run=persist_real_run,
            )
            outputs[node.node_id] = output
            if node.node_id == "build_learning_persona":
                persona_summary = str(output.get("content") or "")

        quality_output = outputs.get("quality_check", {})
        await registry.mark_succeeded(run_id, outputs)
        await registry.publish(
            run_id,
            {
                "event": "done",
                "workflow_run_id": str(run_id),
                "status": "succeeded",
                "final_output_ref": f"workflow-runs/{run_id}",
                "child_run_count": len(NODE_DEFINITIONS),
                "quality_score": quality_output.get("quality_score"),
                "mode": record.mode,
                "provider": record.provider,
                "model": record.model,
            },
        )
    except (WorkflowCancelled, CancellationRequested):
        await registry.mark_cancelled(run_id)
        await registry.publish(
            run_id,
            {
                "event": "done",
                "workflow_run_id": str(run_id),
                "status": "cancelled",
                "final_output_ref": None,
                "child_run_count": len(record.nodes),
                "quality_score": None,
                "mode": record.mode,
                "provider": record.provider,
                "model": record.model,
            },
        )
    except InsufficientEvidence as exc:
        await _publish_failure(
            registry,
            record,
            current_node,
            code="INSUFFICIENT_EVIDENCE",
            message=str(exc),
            blocked=True,
        )
    except StrictProviderUnavailable as exc:
        await _publish_failure(
            registry,
            record,
            current_node,
            code="PROVIDER_UNAVAILABLE",
            message=str(exc),
        )
    except StrictLLMOutputInvalid as exc:
        await _publish_failure(
            registry,
            record,
            current_node,
            code="LLM_OUTPUT_INVALID",
            message=str(exc),
        )
    except AgentRunPersistenceFailed as exc:
        await _publish_failure(
            registry,
            record,
            current_node,
            code="AGENT_RUN_PERSIST_FAILED",
            message=str(exc),
        )
    except HarnessError as exc:
        await _publish_failure(
            registry,
            record,
            current_node,
            code=str(getattr(exc, "code", "WORKFLOW_FAILED")).upper(),
            message=str(exc),
        )
    except Exception as exc:
        await _publish_failure(
            registry,
            record,
            current_node,
            code="WORKFLOW_FAILED",
            message=str(exc),
        )
