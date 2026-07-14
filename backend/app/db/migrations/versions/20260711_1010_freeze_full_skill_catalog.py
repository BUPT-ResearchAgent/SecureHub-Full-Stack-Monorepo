# Status: real

"""Freeze the complete 28-binding production Skill catalog.

Revision ID: 20260711_1010
Revises: 20260711_1000
Create Date: 2026-07-11 10:10:00

This is additive data migration.  It enables every existing production binding
under the fixed nine UUIDv5 Agent identities; no tenth Agent is introduced.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from alembic import op


revision: str = "20260711_1010"
down_revision: str | None = "20260711_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CATALOG: dict[str, tuple[str, ...]] = {
    "policy_interpreter": ("InterpretPolicy", "ComplianceCheck"),
    "hot_analyst": ("AnalyzeHotEvent", "RecommendReadings"),
    "job_analyst": ("AnalyzeJobMarket", "SkillGapAnalysis"),
    "competition_advisor": ("GenerateCompetitionPlan", "GenerateQuiz", "RecommendCompetition"),
    "career_planner": (
        "BuildLearningPersona",
        "UpdatePersona",
        "RecommendResources",
        "RouteTutorQuestion",
        "GenerateGrowthPlan",
    ),
    "topic_explorer": ("GenerateHandsOnLab", "GenerateResearchTopic", "RecommendReadings"),
    "doc_archivist": (
        "GenerateCourseDoc",
        "GenerateCoursePPT",
        "GenerateMindmap",
        "GenerateVideoStoryboard",
        "GenerateProposal",
    ),
    "task_orchestrator": ("GenerateLearningPath", "DecomposeWBS"),
    "outcome_evaluator": ("EvaluateSubmission", "RunAssessment", "QualityCheck", "UpdateCapability"),
}


def _stable(name: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"securehub:{name}"))


def _upsert(bind: sa.engine.Connection, agent_name: str, skill_name: str) -> None:
    aid = _stable(f"agent:{agent_name}")
    sid = _stable(f"skill:{agent_name}:{skill_name}:1")
    existing = bind.execute(
        sa.text(
            "SELECT id FROM agent_skills WHERE agent_id = :aid AND skill_name = :skill AND version = 1"
        ),
        {"aid": aid, "skill": skill_name},
    ).first()
    if existing:
        bind.execute(
            sa.text(
                "UPDATE agent_skills SET enabled = :enabled WHERE agent_id = :aid AND skill_name = :skill AND version = 1"
            ),
            {"enabled": True, "aid": aid, "skill": skill_name},
        )
        return
    payload = {
        "id": sid,
        "aid": aid,
        "skill": skill_name,
        "prompt": "catalog-bound; source prompt is versioned in runtime.skill_catalog",
        "domains": ["course_websec"],
        "tools": ["rag.retrieve", "llm.provider"],
        "schema": json.dumps({}),
        "enabled": True,
    }
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                "INSERT INTO agent_skills "
                "(id, agent_id, skill_name, prompt_template, applicable_domains, required_tools, output_schema, version, enabled) "
                "VALUES (:id, :aid, :skill, :prompt, :domains, :tools, CAST(:schema AS jsonb), 1, :enabled)"
            ),
            payload,
        )
    else:
        payload["domains"] = json.dumps(payload["domains"])
        payload["tools"] = json.dumps(payload["tools"])
        bind.execute(
            sa.text(
                "INSERT INTO agent_skills "
                "(id, agent_id, skill_name, prompt_template, applicable_domains, required_tools, output_schema, version, enabled) "
                "VALUES (:id, :aid, :skill, :prompt, :domains, :tools, :schema, 1, :enabled)"
            ),
            payload,
        )


def upgrade() -> None:
    bind = op.get_bind()
    for agent_name, skills in CATALOG.items():
        for skill_name in skills:
            _upsert(bind, agent_name, skill_name)


def downgrade() -> None:
    # Only remove bindings absent from the historical 14-skill core migration.
    historical = {
        "career_planner": {"BuildLearningPersona", "UpdatePersona", "RecommendResources"},
        "task_orchestrator": {"GenerateLearningPath"},
        "doc_archivist": {"GenerateCourseDoc", "GenerateCoursePPT", "GenerateMindmap", "GenerateVideoStoryboard"},
        "competition_advisor": {"GenerateQuiz"},
        "topic_explorer": {"GenerateHandsOnLab", "RecommendReadings"},
        "outcome_evaluator": {"RunAssessment", "QualityCheck", "UpdateCapability"},
    }
    bind = op.get_bind()
    for agent_name, skills in CATALOG.items():
        for skill_name in skills:
            if skill_name in historical.get(agent_name, set()):
                continue
            bind.execute(
                sa.text(
                    "DELETE FROM agent_skills WHERE agent_id = :aid AND skill_name = :skill AND version = 1"
                ),
                {"aid": _stable(f"agent:{agent_name}"), "skill": skill_name},
            )
