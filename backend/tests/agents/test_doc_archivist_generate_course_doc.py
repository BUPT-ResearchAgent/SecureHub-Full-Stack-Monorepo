# Status: real

"""GenerateCourseDoc skill 回归测试。"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.doc_archivist.skills.generate_course_doc import (
    PROMPT_TEMPLATE,
    GenerateCourseDoc,
    GenerateCourseDocInput,
    GenerateCourseDocOutput,
)
from app.agents.base import SkillContext
from app.rag.retriever import EvidenceHit


def _make_hits(n: int = 3) -> list[EvidenceHit]:
    return [
        EvidenceHit(
            chunk_id=f"chunk-{i}",
            domain="course_websec",
            chunk_text=f"SQL injection documentation source {i}.",
            source="OWASP",
            reliability=0.9,
        )
        for i in range(n)
    ]


def test_generate_course_doc_runs_with_mocks():
    async def go():
        skill = GenerateCourseDoc()
        inp = GenerateCourseDocInput(user_id="demo", query="SQL 注入讲解文档", kp_id="kp-sqli")
        ctx = SkillContext(user_id="demo", persona_summary="{}")

        with (
            patch("app.agents.planned_skill.retrieve", new=AsyncMock(return_value=_make_hits(3))),
            patch(
                "app.agents.planned_skill.xfyun_chat",
                new=AsyncMock(return_value='{"content":"ok","evidence_chunk_ids":[],"quality_score":0.91,"markdown":"# SQL Injection","sections":["intro","attack","defense"]}'),
            ),
            patch.object(SkillContext, "log_run", new=AsyncMock(return_value=None)),
        ):
            out = await skill.run(inp, ctx)

        assert isinstance(out, GenerateCourseDocOutput)
        assert out.content
        assert len(out.markdown) > 0

    asyncio.run(go())


def test_course_doc_prompt_requires_strict_json_safe_markdown():
    assert "JSON validity is mandatory" in PROMPT_TEMPLATE
    assert "fenced code blocks" in PROMPT_TEMPLATE
    assert "internal double quote" in PROMPT_TEMPLATE
