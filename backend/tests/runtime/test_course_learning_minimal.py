# Status: partial-real

from __future__ import annotations

import asyncio
import json
from uuid import UUID, uuid4

import pytest

from app.llm.provider import LLMChunk, LLMResponse, TokenUsage
from app.runtime.harness.fixtures import default_llm_output
from app.runtime.harness.live_adapters import StrictLiveAdapters
from app.runtime.harness.types import EvidenceCard
from app.runtime.run_registry import RunRegistry
from app.runtime.workflows.course_learning_minimal import (
    FIXTURE_MODEL,
    FIXTURE_PROVIDER,
    WORKFLOW_NAME,
    run_course_learning_minimal,
    workflow_nodes,
)


USER_ID = "00000000-0000-0000-0000-000000000001"
_SKILL_NAMES = (
    "BuildLearningPersona",
    "GenerateLearningPath",
    "GenerateCourseDoc",
    "GenerateQuiz",
    "QualityCheck",
)
_EVIDENCE_IDS = tuple(uuid4() for _ in range(3))


def _run_payload() -> dict[str, object]:
    return {
        "workflow": WORKFLOW_NAME,
        "user_id": USER_ID,
        "course_id": "course-websec",
        "topic": "SQL 注入",
        "goal": "生成最小学习闭环",
        "mode": "fixture",
        "provider": "fixture",
        "stream": True,
    }


def _real_payload() -> dict[str, object]:
    return {
        **_run_payload(),
        "mode": "real",
        "provider": "deepseek",
        "stream": True,
    }


class FakeDeepSeekProvider:
    """Explicit fake provider used only for strict adapter tests, never live smoke."""

    provider_name = "deepseek"
    model_name = "fake-deepseek-v4"

    def __init__(self, *, fail: bool = False, invalid_json: bool = False) -> None:
        self.fail = fail
        self.invalid_json = invalid_json
        self.calls = 0

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def _next_content(self) -> str:
        skill_name = _SKILL_NAMES[min(self.calls, len(_SKILL_NAMES) - 1)]
        self.calls += 1
        if self.invalid_json:
            return "this is not json"
        return json.dumps(default_llm_output(skill_name), ensure_ascii=False)

    async def generate(self, *_args, **_kwargs) -> LLMResponse:
        if self.fail:
            raise RuntimeError("fake DeepSeek failure")
        content = self._next_content()
        return LLMResponse(
            content=content,
            usage=TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            provider=self.provider_name,
            model=self.model_name,
        )

    async def stream_generate(self, *_args, **_kwargs):
        if self.fail:
            raise RuntimeError("fake DeepSeek failure")
        yield LLMChunk(content=self._next_content(), index=0)


class CancelAfterFirstTokenProvider(FakeDeepSeekProvider):
    def __init__(self) -> None:
        super().__init__()
        self.first_token_forwarded = asyncio.Event()
        self.release = asyncio.Event()

    async def stream_generate(self, *_args, **_kwargs):
        content = self._next_content()
        midpoint = max(1, len(content) // 2)
        yield LLMChunk(content=content[:midpoint], index=0)
        self.first_token_forwarded.set()
        await self.release.wait()
        yield LLMChunk(content=content[midpoint:], index=1)


def _strict_retriever(count: int):
    async def retrieve(*_args, **_kwargs) -> list[EvidenceCard]:
        return [
            EvidenceCard(
                chunk_id=str(_EVIDENCE_IDS[index]),
                document_id=str(uuid4()),
                domain="course_websec",
                source="fake://strict-rag",
                excerpt=f"strict fake evidence {index}",
                reliability=0.9,
                score=0.9 - index * 0.1,
            )
            for index in range(count)
        ]

    return retrieve


def _memory_persister(rows: list[dict[str, object]]):
    async def persist(**kwargs: object) -> None:
        rows.append(dict(kwargs))

    return persist


async def _collect_events(registry: RunRegistry, run_id: UUID) -> list[dict[str, object]]:
    return [event async for event in registry.iter_events(run_id)]


def test_fixture_workflow_runs_five_fixed_agents_with_trace_events():
    async def scenario():
        registry = RunRegistry()
        record = await registry.create(
            workflow=WORKFLOW_NAME,
            user_id=USER_ID,
            mode="fixture",
            provider=FIXTURE_PROVIDER,
            model=FIXTURE_MODEL,
            input_payload=_run_payload(),
            nodes=workflow_nodes(),
        )
        await run_course_learning_minimal(record.run_id, registry)
        snapshot = await registry.snapshot(record.run_id)
        events = await _collect_events(registry, record.run_id)
        return snapshot, events

    snapshot, events = asyncio.run(scenario())

    assert snapshot["status"] == "succeeded"
    assert snapshot["child_run_count"] == 5
    assert {child["agent_name"] for child in snapshot["child_runs"]} == {
        "career_planner",
        "task_orchestrator",
        "doc_archivist",
        "competition_advisor",
        "outcome_evaluator",
    }
    assert all(child["status"] == "succeeded" for child in snapshot["child_runs"])
    assert {event["event"] for event in events} >= {"progress", "evidence", "trace", "done"}
    assert events[-1]["event"] == "done"
    assert events[-1]["status"] == "succeeded"
    assert all(event["mode"] == "fixture" for event in events)
    assert all(event["provider"] == "fixture" for event in events)


def test_sse_history_fans_out_to_two_subscribers_and_replays_after_completion():
    async def scenario():
        registry = RunRegistry()
        record = await registry.create(
            workflow=WORKFLOW_NAME,
            user_id=USER_ID,
            mode="fixture",
            provider=FIXTURE_PROVIDER,
            model=FIXTURE_MODEL,
            input_payload=_run_payload(),
            nodes=workflow_nodes(),
        )
        first = asyncio.create_task(_collect_events(registry, record.run_id))
        second = asyncio.create_task(_collect_events(registry, record.run_id))
        await asyncio.sleep(0)
        await run_course_learning_minimal(record.run_id, registry)
        first_events, second_events = await asyncio.gather(first, second)
        completed_replay = await _collect_events(registry, record.run_id)
        cursor = int(first_events[3]["event_id"])
        resumed = [
            event
            async for event in registry.iter_events(
                record.run_id,
                after_event_id=cursor,
            )
        ]
        return first_events, second_events, completed_replay, cursor, resumed

    first, second, completed_replay, cursor, resumed = asyncio.run(scenario())

    first_ids = [event["event_id"] for event in first]
    assert first_ids == [event["event_id"] for event in second]
    assert first_ids == [event["event_id"] for event in completed_replay]
    assert {event["event"] for event in first} >= {"progress", "trace", "done"}
    assert all(int(event["event_id"]) > cursor for event in resumed)
    assert resumed[-1]["event"] == "done"


@pytest.mark.parametrize("evidence_count", [0, 2])
def test_strict_real_retriever_below_floor_blocks_without_fixture_or_llm(evidence_count: int):
    async def scenario():
        registry = RunRegistry()
        record = await registry.create(
            workflow=WORKFLOW_NAME,
            user_id=USER_ID,
            mode="real",
            provider="deepseek",
            model="placeholder",
            input_payload=_real_payload(),
            nodes=workflow_nodes(),
        )
        provider = FakeDeepSeekProvider()
        persisted: list[dict[str, object]] = []
        adapters = StrictLiveAdapters(
            provider=provider,
            retrieve_fn=_strict_retriever(evidence_count),
            cancellation_requested=record.cancellation_event.is_set,
            max_tokens=32,
        )
        await run_course_learning_minimal(
            record.run_id,
            registry,
            strict_adapters=adapters,
            persist_real_run=_memory_persister(persisted),
        )
        return await registry.snapshot(record.run_id), await _collect_events(registry, record.run_id), provider, persisted

    snapshot, events, provider, persisted = asyncio.run(scenario())

    assert snapshot["status"] == "blocked"
    assert snapshot["error"]["code"] == "INSUFFICIENT_EVIDENCE"
    assert provider.calls == 0
    assert not {event["event"] for event in events} & {"evidence", "token", "artifact", "trace"}
    assert events[-1]["event"] == "error"
    assert events[-1]["code"] == "INSUFFICIENT_EVIDENCE"
    assert all(event["mode"] == "real" for event in events)
    assert all(event["provider"] == "deepseek" for event in events)
    assert len(persisted) == 1
    assert persisted[0]["evidence_chunk_ids"] == []
    assert snapshot["child_runs"][0]["persistence"] == "agent_runs"


def test_strict_real_workflow_uses_fake_deepseek_and_persists_matching_trace_ids():
    async def scenario():
        registry = RunRegistry()
        record = await registry.create(
            workflow=WORKFLOW_NAME,
            user_id=USER_ID,
            mode="real",
            provider="deepseek",
            model="placeholder",
            input_payload=_real_payload(),
            nodes=workflow_nodes(),
        )
        provider = FakeDeepSeekProvider()
        persisted: list[dict[str, object]] = []
        adapters = StrictLiveAdapters(
            provider=provider,
            retrieve_fn=_strict_retriever(3),
            cancellation_requested=record.cancellation_event.is_set,
            max_tokens=32,
        )
        await run_course_learning_minimal(
            record.run_id,
            registry,
            strict_adapters=adapters,
            persist_real_run=_memory_persister(persisted),
        )
        return record, await registry.snapshot(record.run_id), await _collect_events(registry, record.run_id), persisted

    record, snapshot, events, persisted = asyncio.run(scenario())

    assert snapshot["status"] == "succeeded"
    assert snapshot["mode"] == "real"
    assert snapshot["provider"] == "deepseek"
    assert snapshot["model"] == "fake-deepseek-v4"
    assert len(persisted) == 5
    assert all(child["persistence"] == "agent_runs" for child in snapshot["child_runs"])
    child_ids = {str(child["agent_run_id"]) for child in snapshot["child_runs"]}
    trace_ids = {str(event["agent_run_id"]) for event in events if event["event"] == "trace"}
    assert child_ids == trace_ids
    assert all(str(row["run_id"]) in child_ids for row in persisted)
    assert all(row["workflow_run_id"] == record.run_id for row in persisted)
    assert all(
        row["input_summary"]["workflow_run_id"] == str(record.run_id)
        for row in persisted
    )
    assert {event["event"] for event in events} >= {
        "progress",
        "evidence",
        "token",
        "trace",
        "done",
    }
    assert not any(event["event"] == "artifact" for event in events)
    assert all(event["mode"] == "real" for event in events)
    assert all(event["provider"] == "deepseek" for event in events)

    evidence_ids = [str(item) for item in _EVIDENCE_IDS]
    for output in snapshot["final_output"].values():
        assert output["evidence_chunk_ids"] == evidence_ids
    for node_id, _agent_name, _skill_name in workflow_nodes():
        node_events = [event for event in events if event.get("node_id") == node_id]
        evidence_event = next(event for event in node_events if event["event"] == "evidence")
        token_event = next(event for event in node_events if event["event"] == "token")
        assert int(evidence_event["event_id"]) < int(token_event["event_id"])


@pytest.mark.parametrize(
    ("provider", "expected_code"),
    [
        (FakeDeepSeekProvider(fail=True), "PROVIDER_UNAVAILABLE"),
        (FakeDeepSeekProvider(invalid_json=True), "LLM_OUTPUT_INVALID"),
    ],
)
def test_strict_real_provider_and_json_failures_never_fall_back(provider, expected_code: str):
    async def scenario():
        registry = RunRegistry()
        record = await registry.create(
            workflow=WORKFLOW_NAME,
            user_id=USER_ID,
            mode="real",
            provider="deepseek",
            model="placeholder",
            input_payload=_real_payload(),
            nodes=workflow_nodes(),
        )
        persisted: list[dict[str, object]] = []
        adapters = StrictLiveAdapters(
            provider=provider,
            retrieve_fn=_strict_retriever(3),
            cancellation_requested=record.cancellation_event.is_set,
            max_tokens=32,
        )
        await run_course_learning_minimal(
            record.run_id,
            registry,
            strict_adapters=adapters,
            persist_real_run=_memory_persister(persisted),
        )
        return await registry.snapshot(record.run_id), await _collect_events(registry, record.run_id), persisted

    snapshot, events, persisted = asyncio.run(scenario())

    assert snapshot["status"] == "failed"
    assert snapshot["error"]["code"] == expected_code
    assert events[-1]["event"] == "error"
    assert events[-1]["code"] == expected_code
    assert not any(event["event"] == "artifact" for event in events)
    assert not any(event["event"] == "trace" for event in events)
    assert all(event["mode"] == "real" for event in events)
    assert all(event["provider"] == "deepseek" for event in events)
    assert len(persisted) == 1


def test_cancel_during_strict_stream_stops_future_token_and_artifact_events():
    async def scenario():
        registry = RunRegistry()
        record = await registry.create(
            workflow=WORKFLOW_NAME,
            user_id=USER_ID,
            mode="real",
            provider="deepseek",
            model="placeholder",
            input_payload=_real_payload(),
            nodes=workflow_nodes(),
        )
        provider = CancelAfterFirstTokenProvider()
        adapters = StrictLiveAdapters(
            provider=provider,
            retrieve_fn=_strict_retriever(3),
            cancellation_requested=record.cancellation_event.is_set,
            max_tokens=32,
        )
        task = asyncio.create_task(
            run_course_learning_minimal(
                record.run_id,
                registry,
                strict_adapters=adapters,
                persist_real_run=_memory_persister([]),
            )
        )
        await provider.first_token_forwarded.wait()
        cancel_cursor = record.next_event_id - 1
        cancelled = await registry.request_cancel(record.run_id)
        provider.release.set()
        await task
        return cancelled, cancel_cursor, await registry.snapshot(record.run_id), await _collect_events(registry, record.run_id)

    cancelled, cancel_cursor, snapshot, events = asyncio.run(scenario())

    assert cancelled.status in {"cancelling", "cancelled"}
    assert snapshot["status"] == "cancelled"
    assert events[-1]["event"] == "done"
    assert events[-1]["status"] == "cancelled"
    assert not any(
        event["event"] in {"token", "artifact"}
        and int(event["event_id"]) > cancel_cursor
        for event in events
    )
    assert snapshot["child_runs"][0]["status"] == "cancelled"
    assert all(child["status"] == "skipped" for child in snapshot["child_runs"][1:])


def test_pre_cancelled_workflow_skips_unstarted_nodes():
    async def scenario():
        registry = RunRegistry()
        record = await registry.create(
            workflow=WORKFLOW_NAME,
            user_id=USER_ID,
            mode="fixture",
            provider=FIXTURE_PROVIDER,
            model=FIXTURE_MODEL,
            input_payload=_run_payload(),
            nodes=workflow_nodes(),
        )
        await registry.request_cancel(record.run_id)
        await run_course_learning_minimal(record.run_id, registry)
        snapshot = await registry.snapshot(record.run_id)
        events = await _collect_events(registry, record.run_id)
        return snapshot, events

    snapshot, events = asyncio.run(scenario())

    assert snapshot["status"] == "cancelled"
    assert all(child["status"] == "skipped" for child in snapshot["child_runs"])
    assert events[-1]["event"] == "done"
    assert events[-1]["status"] == "cancelled"
    assert not {event["event"] for event in events} & {"token", "artifact"}


@pytest.mark.anyio
async def test_agent_run_service_uses_supplied_id_and_resolved_seed_links(sqlite_session) -> None:
    from app.db.models.agent.agent_run import AgentRun
    from app.db.seeds._constants import DEMO_USER_ID
    from app.db.seeds.seed_agent_skills import run as seed_agent_skills
    from app.db.seeds.seed_agents import run as seed_agents
    from app.db.seeds.seed_demo_user import run as seed_demo_user
    from app.services.agent.agent_run_service import AgentRunService

    await seed_demo_user(sqlite_session)
    await seed_agents(sqlite_session)
    await seed_agent_skills(sqlite_session)
    await sqlite_session.commit()

    workflow_run_id = uuid4()
    child_run_id = uuid4()
    service = AgentRunService(sqlite_session)
    persisted_id = await service.begin_run(
        run_id=child_run_id,
        workflow_name=WORKFLOW_NAME,
        agent_name="career_planner",
        skill_name="BuildLearningPersona",
        user_id=DEMO_USER_ID,
        input_summary={"workflow_run_id": str(workflow_run_id)},
        require_resolution=True,
    )
    await service.finish_success(
        persisted_id,
        output_summary={"status": "ok"},
        evidence_chunk_ids=[_EVIDENCE_IDS[0]],
    )

    row = await sqlite_session.get(AgentRun, child_run_id)
    assert persisted_id == child_run_id
    assert row is not None
    assert row.agent_id is not None
    assert row.skill_id is not None
    assert row.input_summary["workflow_run_id"] == str(workflow_run_id)
    assert row.evidence_chunk_ids == [str(_EVIDENCE_IDS[0])]
