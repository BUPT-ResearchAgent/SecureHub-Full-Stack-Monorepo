# Status: [planned]

"""data-layer v2: seed agents + core skills

Revision ID: 20260611_0960
Revises: 20260611_0950
Create Date: 2026-06-11 09:60:00

Upserts the canonical 9 agents and the §8.3 core-skill catalogue. Supersedes
``20260610_1000_seed_agents`` (which only runs on PostgreSQL) with a
dialect-agnostic write path so the SQLite-fallback CI loop also leaves the
DB populated. Stable UUIDv5 ids keep upserts deterministic.

This intentionally re-asserts rows v1 may already have inserted: it does a
``SELECT id WHERE name = …`` first and only ``INSERT`` when missing, so the
re-run is safe on PG, SQLite, or any later host.
"""

import json
from collections.abc import Sequence
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from alembic import op

revision: str = "20260611_0960"
down_revision: str | None = "20260611_0950"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# 9 fixed agents — see CLAUDE.md §2.1 and AGENTS.md §3.1.
AGENTS: list[tuple[str, str, str]] = [
    ("policy_interpreter", "Policy and compliance interpretation agent.", "medium"),
    ("hot_analyst", "Security event and reading recommendation agent.", "high"),
    ("job_analyst", "Job market and skill gap analysis agent.", "low"),
    ("competition_advisor", "Competition and quiz generation agent.", "medium"),
    ("career_planner", "Learning persona, resource recommendation, and tutor routing agent.", "high"),
    ("topic_explorer", "Research topic and hands-on lab agent.", "medium"),
    ("doc_archivist", "Course document, PPT, mindmap, and video storyboard agent.", "low"),
    ("task_orchestrator", "Learning path and task planning agent.", "low"),
    ("outcome_evaluator", "Assessment, capability update, and quality gate agent.", "high"),
]

# Core skills required by the v2 spec (task brief §8.3).
CORE_SKILLS: dict[str, list[str]] = {
    "career_planner": ["BuildLearningPersona", "UpdatePersona", "RecommendResources"],
    "task_orchestrator": ["GenerateLearningPath"],
    "doc_archivist": [
        "GenerateCourseDoc",
        "GenerateCoursePPT",
        "GenerateMindmap",
        "GenerateVideoStoryboard",
    ],
    "competition_advisor": ["GenerateQuiz"],
    "topic_explorer": ["GenerateHandsOnLab", "RecommendReadings"],
    "outcome_evaluator": ["RunAssessment", "QualityCheck", "UpdateCapability"],
}


def stable_id(name: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"securehub:{name}"))


def _empty_vector_literal(dim: int) -> str:
    """A zero-vector literal that pgvector accepts on PG and that compiles
    to a BLOB on SQLite. Both backends store it without further casting."""
    return "[" + ",".join(["0"] * dim) + "]"


def _upsert_agent(
    bind: sa.engine.Connection, name: str, description: str, risk: str
) -> None:
    agent_id = stable_id(f"agent:{name}")
    existing = bind.execute(
        sa.text("SELECT id FROM agents WHERE name = :name"), {"name": name}
    ).first()
    if existing:
        bind.execute(
            sa.text(
                "UPDATE agents SET role_description = :rd, risk_level = :rl, "
                "enabled = :en WHERE name = :name"
            ),
            {"rd": description, "rl": risk, "en": True, "name": name},
        )
        return

    is_pg = bind.dialect.name == "postgresql"
    vector_literal = _empty_vector_literal(64)
    tools_value = ["rag.retrieve", "llm.xfyun"]
    if is_pg:
        bind.execute(
            sa.text(
                "INSERT INTO agents (id, name, role_description, capability_vector, "
                "tools, input_schema, output_schema, risk_level, enabled) "
                "VALUES (:id, :name, :rd, CAST(:cv AS vector), :tools, "
                "CAST(:is AS jsonb), CAST(:os AS jsonb), :rl, :en)"
            ),
            {
                "id": agent_id,
                "name": name,
                "rd": description,
                "cv": vector_literal,
                "tools": tools_value,
                "is": json.dumps({}),
                "os": json.dumps({}),
                "rl": risk,
                "en": True,
            },
        )
    else:
        bind.execute(
            sa.text(
                "INSERT INTO agents (id, name, role_description, capability_vector, "
                "tools, input_schema, output_schema, risk_level, enabled) "
                "VALUES (:id, :name, :rd, :cv, :tools, :is, :os, :rl, :en)"
            ),
            {
                "id": agent_id,
                "name": name,
                "rd": description,
                "cv": vector_literal,
                "tools": json.dumps(tools_value),
                "is": json.dumps({}),
                "os": json.dumps({}),
                "rl": risk,
                "en": True,
            },
        )


def _upsert_skill(
    bind: sa.engine.Connection, agent_name: str, skill_name: str
) -> None:
    agent_id = stable_id(f"agent:{agent_name}")
    skill_id = stable_id(f"skill:{agent_name}:{skill_name}:1")
    existing = bind.execute(
        sa.text(
            "SELECT id FROM agent_skills "
            "WHERE agent_id = :aid AND skill_name = :sn AND version = :v"
        ),
        {"aid": agent_id, "sn": skill_name, "v": 1},
    ).first()
    if existing:
        bind.execute(
            sa.text(
                "UPDATE agent_skills SET enabled = :en WHERE agent_id = :aid "
                "AND skill_name = :sn AND version = :v"
            ),
            {"en": True, "aid": agent_id, "sn": skill_name, "v": 1},
        )
        return

    is_pg = bind.dialect.name == "postgresql"
    domains_value = ["course_websec"]
    tools_value = ["rag.retrieve", "llm.xfyun"]
    if is_pg:
        bind.execute(
            sa.text(
                "INSERT INTO agent_skills (id, agent_id, skill_name, prompt_template, "
                "applicable_domains, required_tools, output_schema, version, enabled) "
                "VALUES (:id, :aid, :sn, :pt, :ad, :rt, CAST(:os AS jsonb), :v, :en)"
            ),
            {
                "id": skill_id,
                "aid": agent_id,
                "sn": skill_name,
                "pt": "TODO",
                "ad": domains_value,
                "rt": tools_value,
                "os": json.dumps({}),
                "v": 1,
                "en": True,
            },
        )
    else:
        bind.execute(
            sa.text(
                "INSERT INTO agent_skills (id, agent_id, skill_name, prompt_template, "
                "applicable_domains, required_tools, output_schema, version, enabled) "
                "VALUES (:id, :aid, :sn, :pt, :ad, :rt, :os, :v, :en)"
            ),
            {
                "id": skill_id,
                "aid": agent_id,
                "sn": skill_name,
                "pt": "TODO",
                "ad": json.dumps(domains_value),
                "rt": json.dumps(tools_value),
                "os": json.dumps({}),
                "v": 1,
                "en": True,
            },
        )


def upgrade() -> None:
    bind = op.get_bind()

    for name, description, risk in AGENTS:
        _upsert_agent(bind, name, description, risk)

    for agent_name, skill_names in CORE_SKILLS.items():
        for skill_name in skill_names:
            _upsert_skill(bind, agent_name, skill_name)


def downgrade() -> None:
    # Inverse of upgrade: remove the rows this migration owns. v1 seed will
    # still re-seed the agents row if its upgrade is re-run later.
    bind = op.get_bind()
    for agent_name, skill_names in CORE_SKILLS.items():
        agent_id = stable_id(f"agent:{agent_name}")
        for skill_name in skill_names:
            bind.execute(
                sa.text(
                    "DELETE FROM agent_skills WHERE agent_id = :aid "
                    "AND skill_name = :sn AND version = :v"
                ),
                {"aid": agent_id, "sn": skill_name, "v": 1},
            )
    for name, _description, _risk in AGENTS:
        bind.execute(sa.text("DELETE FROM agents WHERE name = :n"), {"n": name})
