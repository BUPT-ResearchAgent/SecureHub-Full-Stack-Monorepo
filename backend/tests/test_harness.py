# Status: real

"""Harness 基础回归测试：

- 兜底 fixture 模式下 skill 能跑通；
- evidence_floor 守门：证据不足直接抛 InsufficientEvidence；
- 输出 evidence_chunk_ids 透传；
- agent_runs logger（兜底情况下为 noop 不抛错）。
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

import pytest

from app.runtime.harness import (
    EvidenceCard,
    Harness,
    HarnessContext,
    InsufficientEvidence,
    SkillSpec,
)


class _Input(__import__("pydantic").BaseModel):
    user_id: str = "demo"
    query: str = "SQL injection basics"
    domain: str = "course_websec"


class _Output(__import__("pydantic").BaseModel):
    content: str = ""
    quality_score: float = 0.0
    evidence_chunk_ids: list[str] = []


PROMPT = """You are demo agent.
Evidence:
{evidence_text}
Persona:
{persona_text}
Task:
{task_instruction}
Schema:
{output_schema_hint}
"""


def _spec_real_evidence() -> SkillSpec:
    return SkillSpec(
        name="DemoSkill",
        agent_name="demo_agent",
        input_model=_Input,
        output_model=_Output,
        prompt_template=PROMPT,
        evidence_floor=3,
        quality_check=False,  # avoid extra LLM
    )


async def _fake_rag_with_3(
    query: str,
    *,
    domain: str,
    top_k: int,
    filters: dict[str, Any] | None = None,
) -> list[EvidenceCard]:
    return [
        EvidenceCard(
            chunk_id=str(uuid4()),
            domain=domain,
            source="fixture",
            excerpt=f"hit-{i}",
            score=0.5 + i / 10,
        )
        for i in range(3)
    ]


async def _fake_rag_with_1(
    query: str,
    *,
    domain: str,
    top_k: int,
    filters: dict[str, Any] | None = None,
) -> list[EvidenceCard]:
    return [
        EvidenceCard(
            chunk_id=str(uuid4()),
            domain=domain,
            source="fixture",
            excerpt="only one",
        )
    ]


async def _fake_llm(
    prompt: str,
    *,
    skill_name: str,
    stream: bool = False,
    emit=None,
) -> dict[str, Any]:
    return {"content": "ok", "quality_score": 0.9}


def test_happy_path_runs_through_harness():
    async def go() -> _Output:
        harness = Harness(rag_retrieve=_fake_rag_with_3, llm_complete=_fake_llm)
        ctx = HarnessContext(user_id="demo", workflow_name="test")
        return await harness.run(_spec_real_evidence(), _Input(), ctx)

    out = asyncio.run(go())
    assert out.content == "ok"
    assert len(out.evidence_chunk_ids) == 3


def test_insufficient_evidence_blocks_llm():
    async def go() -> _Output:
        harness = Harness(rag_retrieve=_fake_rag_with_1, llm_complete=_fake_llm)
        ctx = HarnessContext(user_id="demo", workflow_name="test")
        return await harness.run(_spec_real_evidence(), _Input(), ctx)

    with pytest.raises(InsufficientEvidence):
        asyncio.run(go())


def test_evidence_floor_disabled_when_required_false():
    spec = _spec_real_evidence()
    spec.require_evidence = False
    spec.evidence_floor = 5  # would normally fail

    async def go() -> _Output:
        harness = Harness(rag_retrieve=_fake_rag_with_1, llm_complete=_fake_llm)
        ctx = HarnessContext(user_id="demo", workflow_name="test")
        return await harness.run(spec, _Input(), ctx)

    out = asyncio.run(go())
    assert out.content == "ok"
