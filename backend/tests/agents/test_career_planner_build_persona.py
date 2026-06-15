# Status: real

"""BuildLearningPersona skill 回归测试。"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.career_planner.skills.build_learning_persona import (
    BuildLearningPersona,
    BuildLearningPersonaInput,
    BuildLearningPersonaOutput,
)
from app.agents.base import SkillContext
from app.rag.retriever import EvidenceHit


def _make_hits(n: int = 3) -> list[EvidenceHit]:
    return [
        EvidenceHit(
            chunk_id=f"chunk-{i}",
            domain="course_websec",
            chunk_text=f"SQL injection evidence chunk {i}.",
            source="OWASP",
            reliability=0.9,
        )
        for i in range(n)
    ]


def test_build_persona_runs_with_mock_retriever_and_llm():
    async def go():
        skill = BuildLearningPersona()
        inp = BuildLearningPersonaInput(
            user_id="demo",
            query="SQL 注入学习",
        )
        ctx = SkillContext(user_id="demo", persona_summary="{}")

        with (
            patch("app.agents.planned_skill.retrieve", new=AsyncMock(return_value=_make_hits(3))),
            patch(
                "app.agents.planned_skill.xfyun_chat",
                new=AsyncMock(return_value='{"content":"ok","evidence_chunk_ids":[],"quality_score":0.85,"dimensions":{"base_knowledge":"beginner"}}'),
            ),
            patch.object(SkillContext, "log_run", new=AsyncMock(return_value=None)),
        ):
            out = await skill.run(inp, ctx)

        assert isinstance(out, BuildLearningPersonaOutput)
        assert out.content
        assert out.quality_score > 0

    asyncio.run(go())


def test_build_persona_output_has_expected_fields():
    out = BuildLearningPersonaOutput(
        content="test",
        evidence_chunk_ids=["chunk-1"],
        quality_score=0.8,
        dimensions={"base_knowledge": "beginner"},
    )
    assert "base_knowledge" in out.dimensions
