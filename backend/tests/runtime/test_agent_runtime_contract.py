# Status: real

"""Wave 0 architecture invariants.

These tests intentionally fail before a second runtime, implicit QualityCheck,
unbounded agent roster, or eighth external SSE type can leak back into code.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.runtime.contracts import EventEnvelope, EventType, RunStatus, SSE_EVENT_TYPES
from app.runtime.skill_catalog import (
    CatalogIntegrityError,
    EXPECTED_PRODUCTION_SKILL_COUNT,
    FIXED_AGENT_NAMES,
    assert_catalog_integrity,
    assert_persisted_catalog_integrity,
    build_production_skill_catalog,
)
from app.db.seeds._constants import agent_id, skill_id
from app.runtime.state_machine import InvalidStateTransition, SecureHubStateMachine
from app.runtime.workflow_definition import EdgeDefinition, NodeDefinition, WorkflowDefinition


class _Input(BaseModel):
    value: str


class _Output(BaseModel):
    value: str


def test_fixed_nine_agent_manifest_and_complete_catalog_are_locked() -> None:
    catalog = build_production_skill_catalog()
    assert_catalog_integrity(catalog)
    assert len(FIXED_AGENT_NAMES) == 9
    assert len(catalog) == EXPECTED_PRODUCTION_SKILL_COUNT == 28
    assert {agent for agent, _skill in catalog} == set(FIXED_AGENT_NAMES)


class _CatalogResult:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[object, ...]]:
        return self._rows


class _CatalogSession:
    def __init__(self, agent_rows: list[tuple[object, ...]], skill_rows: list[tuple[object, ...]]) -> None:
        self._rows = iter((agent_rows, skill_rows))

    async def execute(self, _statement):
        return _CatalogResult(next(self._rows))


@pytest.mark.anyio
async def test_enabled_database_catalog_must_match_the_frozen_manifest() -> None:
    catalog = build_production_skill_catalog()
    agent_rows = [(agent_id(name), name) for name in FIXED_AGENT_NAMES]
    skill_rows = [
        (agent_name, skill_name, skill_id(agent_name, skill_name, definition.version))
        for (agent_name, skill_name), definition in catalog.items()
    ]

    await assert_persisted_catalog_integrity(_CatalogSession(agent_rows, skill_rows), catalog)  # type: ignore[arg-type]

    with pytest.raises(CatalogIntegrityError, match="skill bindings"):
        await assert_persisted_catalog_integrity(
            _CatalogSession(agent_rows, skill_rows[:-1]),  # type: ignore[arg-type]
            catalog,
        )


def test_public_sse_contract_has_exactly_seven_event_types() -> None:
    assert SSE_EVENT_TYPES == {"progress", "evidence", "token", "artifact", "trace", "done", "error"}
    for index, event_type in enumerate(EventType, start=1):
        envelope = EventEnvelope(workflow_run_id="run-1", sequence=index, event_type=event_type)
        assert envelope.sequence == index
    with pytest.raises(ValueError, match="forbidden"):
        EventEnvelope(
            workflow_run_id="run-1",
            sequence=1,
            event_type=EventType.TRACE,
            payload={"prompt": "must never leave the runtime"},
        )


def test_state_machine_rejects_terminal_and_illegal_transitions() -> None:
    SecureHubStateMachine.assert_run_transition(RunStatus.QUEUED, RunStatus.RUNNING)
    SecureHubStateMachine.assert_run_transition(RunStatus.RUNNING, RunStatus.SUCCEEDED)
    with pytest.raises(InvalidStateTransition):
        SecureHubStateMachine.assert_run_transition(RunStatus.SUCCEEDED, RunStatus.RUNNING)
    with pytest.raises(InvalidStateTransition):
        SecureHubStateMachine.assert_run_transition(RunStatus.QUEUED, RunStatus.SUCCEEDED)


def test_workflow_definition_requires_explicit_nonrecursive_quality_node() -> None:
    producer = NodeDefinition(
        node_id="producer",
        kind="skill",
        agent_name="doc_archivist",
        skill_name="GenerateCourseDoc",
        quality_policy="workflow_node",
    )
    with pytest.raises(ValueError, match="QualityCheck"):
        WorkflowDefinition(
            name="invalid",
            version=1,
            input_model=_Input,
            output_model=_Output,
            nodes=(producer,),
        )
    quality = NodeDefinition(
        node_id="quality",
        kind="skill",
        agent_name="outcome_evaluator",
        skill_name="QualityCheck",
        quality_policy="none",
    )
    definition = WorkflowDefinition(
        name="valid",
        version=1,
        input_model=_Input,
        output_model=_Output,
        nodes=(producer, quality),
        edges=(EdgeDefinition("producer", "quality"),),
    )
    assert len(definition.definition_digest) == 64


def test_runtime_contract_stays_framework_neutral() -> None:
    source = WorkflowDefinition.__module__
    assert source == "app.runtime.workflow_definition"
    import inspect

    code = inspect.getsource(WorkflowDefinition)
    assert "langgraph" not in code.lower()
