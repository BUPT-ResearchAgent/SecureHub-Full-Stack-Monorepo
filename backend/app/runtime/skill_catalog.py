# Status: real

"""Frozen production Skill catalog derived from the fixed nine Agent classes.

The catalog intentionally maps all 28 existing production bindings to the
single canonical SkillDefinition contract.  It does not execute legacy
``skill.run()`` methods, which keeps fixture fallback and implicit quality
checks outside RuntimeEngine production paths.
"""

from __future__ import annotations

import importlib
import inspect
from typing import Any, get_type_hints

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent import Agent, AgentSkill
from app.db.seeds._constants import AGENTS, agent_id, skill_id
from app.runtime.capability_manifest import register_agents
from app.runtime.harness.contracts import SkillDefinition


FIXED_AGENT_NAMES = tuple(name for name, _description, _risk in AGENTS)
EXPECTED_PRODUCTION_SKILL_COUNT = 28


class CatalogIntegrityError(RuntimeError):
    pass


def _input_model(skill_class: type[Any]) -> type[BaseModel]:
    hints = get_type_hints(skill_class.run)
    model = hints.get("inp")
    if isinstance(model, type) and issubclass(model, BaseModel):
        return model
    raise CatalogIntegrityError(f"{skill_class.__name__} has no typed input model")


def _definition(agent_name: str, skill_name: str, skill_class: type[Any], risk_level: str) -> SkillDefinition:
    module = importlib.import_module(skill_class.__module__)
    prompt = getattr(module, "PROMPT_TEMPLATE", None)
    output_model = getattr(skill_class, "output_schema", None)
    if not isinstance(prompt, str) or not prompt.strip() or not isinstance(output_model, type) or not issubclass(output_model, BaseModel):
        raise CatalogIntegrityError(f"{agent_name}.{skill_name} does not expose canonical prompt/output metadata")
    quality_policy = "none" if skill_name == "QualityCheck" else "workflow_node"
    return SkillDefinition(
        name=skill_name,
        agent_name=agent_name,
        version=1,
        input_model=_input_model(skill_class),
        output_model=output_model,
        prompt_template=prompt,
        prompt_version="legacy-v1",
        required_domains=tuple(getattr(skill_class, "applicable_domains", ()) or ("course_websec",)),
        evidence_floor=1 if skill_name == "RouteTutorQuestion" else 3,
        quality_policy=quality_policy,
        artifact_policy="after_quality_accept" if skill_name.startswith("Generate") or skill_name == "RecommendReadings" else "none",
        fallback_policy="explicit-real-provider-only",
        risk_level=risk_level if risk_level in {"low", "medium", "high"} else "low",
    )


def build_production_skill_catalog() -> dict[tuple[str, str], SkillDefinition]:
    classes = {agent.name: agent for agent in register_agents()}
    if tuple(classes) != FIXED_AGENT_NAMES:
        missing = set(FIXED_AGENT_NAMES).difference(classes)
        extra = set(classes).difference(FIXED_AGENT_NAMES)
        raise CatalogIntegrityError(f"fixed agent manifest drifted; missing={sorted(missing)}, extra={sorted(extra)}")
    risk_by_agent = {name: risk for name, _description, risk in AGENTS}
    catalog: dict[tuple[str, str], SkillDefinition] = {}
    for agent_name in FIXED_AGENT_NAMES:
        agent_class = classes[agent_name]
        for skill_name, skill_class in agent_class.skills.items():
            key = (agent_name, skill_name)
            if key in catalog:
                raise CatalogIntegrityError(f"duplicate skill catalog entry: {key}")
            catalog[key] = _definition(agent_name, skill_name, skill_class, risk_by_agent[agent_name])
    if len(catalog) != EXPECTED_PRODUCTION_SKILL_COUNT:
        raise CatalogIntegrityError(
            f"production catalog must contain {EXPECTED_PRODUCTION_SKILL_COUNT} bindings, got {len(catalog)}"
        )
    return catalog


def assert_catalog_integrity(
    catalog: dict[tuple[str, str], SkillDefinition] | None = None,
    *,
    enabled_agent_ids: set[str] | None = None,
) -> None:
    catalog = catalog or build_production_skill_catalog()
    agent_names = {agent_name for agent_name, _skill_name in catalog}
    if agent_names != set(FIXED_AGENT_NAMES):
        raise CatalogIntegrityError("catalog does not use exactly the fixed nine agents")
    if len(catalog) != EXPECTED_PRODUCTION_SKILL_COUNT:
        raise CatalogIntegrityError("catalog binding count drifted")
    if enabled_agent_ids is not None:
        expected = {str(agent_id(name)) for name in FIXED_AGENT_NAMES}
        if enabled_agent_ids != expected:
            raise CatalogIntegrityError("enabled DB agent IDs do not match the frozen UUIDv5 manifest")
    for (agent_name, skill_name), definition in catalog.items():
        if definition.agent_name != agent_name or definition.name != skill_name:
            raise CatalogIntegrityError(f"catalog definition drift: {agent_name}.{skill_name}")
        # Resolving these UUIDv5 values here makes ID drift visible in tests and
        # documents the exact DB identity rule without persisting a duplicate id.
        agent_id(agent_name)
        skill_id(agent_name, skill_name, definition.version)


async def assert_persisted_catalog_integrity(
    session: AsyncSession,
    catalog: dict[tuple[str, str], SkillDefinition] | None = None,
) -> None:
    """Fail startup when the enabled database catalog drifts from code.

    The runtime resolves executable definitions from the frozen source catalog,
    but the durable database catalog is still an auditable production boundary.
    Comparing both surfaces before a Worker starts prevents an enabled tenth
    Agent, a renamed UUID, or an unreviewed Skill binding from receiving work.
    """
    catalog = catalog or build_production_skill_catalog()
    assert_catalog_integrity(catalog)

    agent_rows = list(
        (
            await session.execute(
                select(Agent.id, Agent.name).where(Agent.enabled.is_(True))
            )
        ).all()
    )
    enabled_agent_ids = {str(agent_id_value) for agent_id_value, _name in agent_rows}
    assert_catalog_integrity(catalog, enabled_agent_ids=enabled_agent_ids)
    enabled_names = {str(name) for _agent_id_value, name in agent_rows}
    if enabled_names != set(FIXED_AGENT_NAMES):
        raise CatalogIntegrityError("enabled DB agent names do not match the frozen manifest")

    skill_rows = list(
        (
            await session.execute(
                select(Agent.name, AgentSkill.skill_name, AgentSkill.id)
                .join(Agent, Agent.id == AgentSkill.agent_id)
                .where(Agent.enabled.is_(True), AgentSkill.enabled.is_(True))
            )
        ).all()
    )
    expected_bindings = set(catalog)
    persisted_bindings = {(str(agent_name), str(skill_name)) for agent_name, skill_name, _skill_id_value in skill_rows}
    if persisted_bindings != expected_bindings:
        raise CatalogIntegrityError("enabled DB skill bindings do not match the frozen production catalog")
    for agent_name, skill_name, persisted_skill_id in skill_rows:
        definition = catalog[(str(agent_name), str(skill_name))]
        if str(persisted_skill_id) != str(skill_id(str(agent_name), str(skill_name), definition.version)):
            raise CatalogIntegrityError("enabled DB skill IDs do not match the frozen UUIDv5 manifest")


__all__ = [
    "CatalogIntegrityError",
    "EXPECTED_PRODUCTION_SKILL_COUNT",
    "FIXED_AGENT_NAMES",
    "assert_catalog_integrity",
    "assert_persisted_catalog_integrity",
    "build_production_skill_catalog",
]
