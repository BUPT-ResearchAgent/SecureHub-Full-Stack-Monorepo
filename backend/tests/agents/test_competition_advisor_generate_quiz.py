# Status: real

"""GenerateQuiz skill 回归测试。"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.competition_advisor.skills.generate_quiz import (
    GenerateQuiz,
    GenerateQuizInput,
    GenerateQuizOutput,
)
from app.agents.base import SkillContext
from app.rag.retriever import EvidenceHit


def _make_hits(n: int = 3) -> list[EvidenceHit]:
    return [
        EvidenceHit(
            chunk_id=f"chunk-{i}",
            domain="course_websec",
            chunk_text=f"Web security fundamentals evidence {i}.",
            source="OWASP",
            reliability=0.9,
        )
        for i in range(n)
    ]


def test_generate_quiz_runs_with_mocks():
    async def go():
        skill = GenerateQuiz()
        inp = GenerateQuizInput(user_id="demo", query="SQL 注入题目", kp_id="kp-sqli")
        ctx = SkillContext(user_id="demo", persona_summary="{}")

        with (
            patch("app.agents.planned_skill.retrieve", new=AsyncMock(return_value=_make_hits(3))),
            patch(
                "app.agents.planned_skill.xfyun_chat",
                new=AsyncMock(return_value='{"content":"ok","evidence_chunk_ids":[],"quality_score":0.86,"quiz_items":[{"type":"single_choice","question":"test"}]}'),
            ),
            patch.object(SkillContext, "log_run", new=AsyncMock(return_value=None)),
        ):
            out = await skill.run(inp, ctx)

        assert isinstance(out, GenerateQuizOutput)
        assert out.content
        assert len(out.quiz_items) >= 1

    asyncio.run(go())
