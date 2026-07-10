# Status: partial-real

from __future__ import annotations

import asyncio

from app.runtime.run_registry import RunRegistry
from app.runtime.workflows.course_learning_minimal import (
    FIXTURE_MODEL,
    FIXTURE_PROVIDER,
    WORKFLOW_NAME,
    run_course_learning_minimal,
    workflow_nodes,
)


USER_ID = "00000000-0000-0000-0000-000000000001"


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
        events = [event async for event in registry.iter_events(record.run_id)]
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
        events = [event async for event in registry.iter_events(record.run_id)]
        return snapshot, events

    snapshot, events = asyncio.run(scenario())

    assert snapshot["status"] == "cancelled"
    assert all(child["status"] == "skipped" for child in snapshot["child_runs"])
    assert events[-1]["event"] == "done"
    assert events[-1]["status"] == "cancelled"
    assert not {event["event"] for event in events} & {"token", "artifact"}
