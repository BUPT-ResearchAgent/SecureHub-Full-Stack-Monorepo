# Status: real

"""GenerateHandsOnLab skill 回归测试。"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.topic_explorer.skills.generate_hands_on_lab import (
    GenerateHandsOnLab,
    GenerateHandsOnLabInput,
    GenerateHandsOnLabOutput,
)
from app.agents.base import SkillContext
from app.rag.retriever import EvidenceHit


def _make_hits(n: int = 3) -> list[EvidenceHit]:
    return [
        EvidenceHit(
            chunk_id=f"chunk-{i}",
            domain="course_websec",
            chunk_text=f"Lab exercise reference material {i}.",
            source="DVWA",
            reliability=0.9,
        )
        for i in range(n)
    ]


def test_generate_lab_runs_with_mocks():
    async def go():
        skill = GenerateHandsOnLab()
        inp = GenerateHandsOnLabInput(user_id="demo", query="SQL 注入实验", kp_id="kp-sqli")
        ctx = SkillContext(user_id="demo", persona_summary="{}")

        with (
            patch("app.agents.planned_skill.retrieve", new=AsyncMock(return_value=_make_hits(3))),
            patch(
                "app.agents.planned_skill.xfyun_chat",
                new=AsyncMock(return_value='{"content":"ok","evidence_chunk_ids":[],"quality_score":0.89,"steps":[{"title":"Step 1","description":"Start DVWA"}],"acceptance_criteria":["Exfiltrate users table"]}'),
            ),
            patch.object(SkillContext, "log_run", new=AsyncMock(return_value=None)),
        ):
            out = await skill.run(inp, ctx)

        assert isinstance(out, GenerateHandsOnLabOutput)
        assert len(out.steps) >= 1
        assert len(out.acceptance_criteria) >= 1

    asyncio.run(go())
