"""Wave 6 regression gates for the single production execution authority."""

from __future__ import annotations

from pathlib import Path

from app.runtime.harness.fixtures import default_llm_output
from app.runtime.capability_manifest import register_agents
from app.runtime.skill_catalog import build_production_skill_catalog


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_catalog_classes_are_static_metadata_not_direct_execution_adapters() -> None:
    catalog = build_production_skill_catalog()
    assert len(catalog) == 28
    for agent in register_agents():
        for skill in agent.skills.values():
            assert not hasattr(skill, "run"), f"{agent.name}.{skill.name} reintroduced direct skill.run()"
            assert skill.output_schema is not None


def test_explicit_fixture_payloads_match_every_static_catalog_output() -> None:
    catalog = build_production_skill_catalog()
    invalid: dict[str, object] = {}
    for (agent_name, skill_name), definition in catalog.items():
        try:
            definition.output_model.model_validate(default_llm_output(skill_name))
        except ValueError as exc:
            invalid[f"{agent_name}.{skill_name}"] = exc.errors()
    assert not invalid


def test_legacy_execution_modules_are_absent() -> None:
    removed = (
        "app/agents/planned_skill.py",
        "app/agents/_skill_helper.py",
        "app/runtime/run_registry.py",
        "app/runtime/context.py",
        "app/runtime/graphs/course_learning.py",
        "app/runtime/workflows/course_learning_minimal.py",
        "app/runtime/harness/base.py",
        "app/runtime/harness/types.py",
        "app/runtime/harness/live_adapters.py",
        "app/services/agent/skill_execution_service.py",
        "app/services/agent_control_service.py",
    )
    assert not [path for path in removed if (BACKEND_ROOT / path).exists()]


def test_only_durable_workflow_serializer_remains() -> None:
    source = (BACKEND_ROOT / "app/streaming/agent_events.py").read_text(encoding="utf-8")
    assert "serialize_agent_events" not in source
    assert "workflow_event_response" in source
