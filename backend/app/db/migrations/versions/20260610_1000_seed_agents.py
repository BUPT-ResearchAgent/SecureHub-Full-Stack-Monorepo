# Status: [planned]

"""seed agents and skills

Revision ID: 20260610_1000
Revises: 20260610_0900
Create Date: 2026-06-10 10:00:00
"""

from collections.abc import Sequence
from uuid import uuid5, NAMESPACE_URL

import sqlalchemy as sa
import pgvector.sqlalchemy
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260610_1000"
down_revision: str | None = "20260610_0900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AGENTS = [
    ("policy_interpreter", "Policy and compliance interpretation agent.", "medium"),
    ("hot_analyst", "Security event and reading recommendation agent.", "high"),
    ("job_analyst", "Job market analysis agent.", "low"),
    ("competition_advisor", "Competition and quiz generation agent.", "medium"),
    ("career_planner", "Learning persona and resource recommendation agent.", "high"),
    ("topic_explorer", "Research topic and hands-on lab agent.", "medium"),
    ("doc_archivist", "Course document and artifact generation agent.", "low"),
    ("task_orchestrator", "Learning path and task planning agent.", "low"),
    ("outcome_evaluator", "Assessment, capability update, and quality gate agent.", "high"),
]

SKILLS = {
    "policy_interpreter": ["InterpretPolicy", "ComplianceCheck"],
    "hot_analyst": ["RecommendReadings"],
    "competition_advisor": ["RecommendCompetition", "GenerateQuiz", "GenerateCompetitionPlan"],
    "career_planner": ["BuildLearningPersona", "UpdatePersona", "RecommendResources"],
    "topic_explorer": ["GenerateResearchTopic", "GenerateHandsOnLab", "RecommendReadings"],
    "doc_archivist": ["GenerateCourseDoc", "GenerateCoursePPT", "GenerateMindmap", "GenerateVideoStoryboard"],
    "task_orchestrator": ["GenerateLearningPath", "DecomposeWBS"],
    "outcome_evaluator": ["EvaluateSubmission", "RunAssessment", "QualityCheck", "UpdateCapability"],
}


def stable_id(name: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"securehub:{name}"))


def upgrade() -> None:
    # v1 seed relies on pgvector ``Vector(64)`` and JSONB / ARRAY bind params.
    # On SQLite (the local dev / CI fallback) those types compile to BLOB / JSON
    # / JSON but the bind-param serialisation paths differ. The v2 migration
    # ``20260611_0960_seed_agents_skills`` does the same seed in a
    # dialect-agnostic way (and supersedes this content via upsert), so on
    # non-PostgreSQL dialects we leave the rows to that migration.
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    agent_rows = [
        {
            "id": stable_id(f"agent:{name}"),
            "name": name,
            "role_description": description,
            "capability_vector": [0.0] * 64,
            "tools": ["rag.retrieve", "llm.xfyun"],
            "input_schema": {},
            "output_schema": {},
            "risk_level": risk,
            "enabled": True,
        }
        for name, description, risk in AGENTS
    ]
    agent_table = sa.table(
        "agents",
        sa.column("id", postgresql.UUID(as_uuid=False)),
        sa.column("name", sa.String()),
        sa.column("role_description", sa.Text()),
        sa.column("capability_vector", pgvector.sqlalchemy.Vector(64)),
        sa.column("tools", postgresql.ARRAY(sa.Text())),
        sa.column("input_schema", postgresql.JSONB()),
        sa.column("output_schema", postgresql.JSONB()),
        sa.column("risk_level", sa.String()),
        sa.column("enabled", sa.Boolean()),
    )
    skill_table = sa.table(
        "agent_skills",
        sa.column("id", postgresql.UUID(as_uuid=False)),
        sa.column("agent_id", postgresql.UUID(as_uuid=False)),
        sa.column("skill_name", sa.String()),
        sa.column("prompt_template", sa.Text()),
        sa.column("applicable_domains", postgresql.ARRAY(sa.Text())),
        sa.column("required_tools", postgresql.ARRAY(sa.Text())),
        sa.column("output_schema", postgresql.JSONB()),
        sa.column("version", sa.Integer()),
        sa.column("enabled", sa.Boolean()),
    )
    op.bulk_insert(agent_table, agent_rows)

    skill_rows = []
    for agent_name, skill_names in SKILLS.items():
        for skill_name in skill_names:
            skill_rows.append(
                {
                    "id": stable_id(f"skill:{agent_name}:{skill_name}:1"),
                    "agent_id": stable_id(f"agent:{agent_name}"),
                    "skill_name": skill_name,
                    "prompt_template": "TODO",
                    "applicable_domains": ["course_websec"],
                    "required_tools": ["rag.retrieve", "llm.xfyun"],
                    "output_schema": {},
                    "version": 1,
                    "enabled": True,
                }
            )
    op.bulk_insert(skill_table, skill_rows)


def downgrade() -> None:
    op.execute("DELETE FROM agent_skills")
    op.execute("DELETE FROM agents")
