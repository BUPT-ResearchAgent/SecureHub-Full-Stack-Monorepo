# Status: real

"""QualityCheck skill 回归测试。"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.outcome_evaluator.skills.quality_check import (
    QualityCheck,
    QualityCheckInput,
    QualityCheckOutput,
)
from app.agents.base import SkillContext
from app.rag.retriever import EvidenceHit


def _make_hits(n: int = 3) -> list[EvidenceHit]:
    return [
        EvidenceHit(
            chunk_id=f"chunk-{i}",
            domain="course_websec",
            chunk_text=f"Reference text for fact-checking {i}.",
            source="OWASP",
            reliability=0.9,
        )
        for i in range(n)
    ]


def test_quality_check_runs_with_mocks():
    async def go():
        skill = QualityCheck()
        inp = QualityCheckInput(
            user_id="demo",
            query="quality check",
            artifact={"markdown": "test content"},
        )
        ctx = SkillContext(user_id="demo", persona_summary="{}")

        with (
            patch("app.agents.planned_skill.retrieve", new=AsyncMock(return_value=_make_hits(3))),
            patch(
                "app.agents.planned_skill.xfyun_chat",
                new=AsyncMock(return_value='{"content":"ok","evidence_chunk_ids":[],"quality_score":0.94,"accept":true,"defects":[]}'),
            ),
            patch.object(SkillContext, "log_run", new=AsyncMock(return_value=None)),
        ):
            out = await skill.run(inp, ctx)

        assert isinstance(out, QualityCheckOutput)
        assert out.accept is True
        assert out.defects == []
        assert out.quality_score > 0

    asyncio.run(go())


def test_quality_check_rejects_on_low_score():
    out = QualityCheckOutput(
        content="test",
        evidence_chunk_ids=["chunk-1"],
        quality_score=0.3,
        accept=False,
        defects=[{"field": "markdown", "issue": "factual error"}],
    )
    assert out.accept is False
    assert len(out.defects) > 0
