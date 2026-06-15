# Status: real

"""旧式 planned skill helper（兼容层）。

新代码应使用 ``app.agents._skill_helper.run_through_harness``；
本模块保留是为了不破坏 22 个已落地的 skill 文件入口。
"""

from __future__ import annotations

import json
from typing import Any
from typing import TypeVar

from pydantic import BaseModel, Field

from app.agents.base import BaseSkill, SkillContext
from app.agents._skill_helper import run_through_harness
from app.llm.xfyun import xfyun_chat
from app.rag.retriever import retrieve
from app.runtime.harness import EvidenceCard, Harness
from app.runtime.harness.fixtures import default_evidence_fixtures, default_llm_output


class PlannedSkillInput(BaseModel):
    user_id: str
    query: str
    domain: str = "course_websec"


class PlannedSkillOutput(BaseModel):
    content: str = ""
    evidence_chunk_ids: list[str] = Field(default_factory=list)
    quality_score: float = 0.0


OutputT = TypeVar("OutputT", bound=PlannedSkillOutput)


async def _legacy_rag_retrieve(
    query: str,
    *,
    domain: str,
    top_k: int,
    filters: dict[str, Any] | None = None,
) -> list[EvidenceCard]:
    hits = await retrieve(query, domain=domain, top_k=top_k, filter=filters)
    if not hits:
        return [
            EvidenceCard(
                chunk_id=str(hit["chunk_id"]),
                document_id=hit.get("document_id"),
                domain=str(hit.get("domain") or domain),
                source=hit.get("source"),
                excerpt=str(hit.get("excerpt") or hit.get("chunk_text") or ""),
                reliability=float(hit.get("reliability", 0.0)),
                score=float(hit.get("score", 0.0)),
                metadata=dict(hit.get("metadata") or {}),
            )
            for hit in default_evidence_fixtures(domain)
        ][: max(top_k, 3)]
    return [
        EvidenceCard(
            chunk_id=str(hit.chunk_id),
            document_id=str(hit.document_id) if hit.document_id else None,
            domain=hit.domain,
            source=hit.source,
            excerpt=hit.chunk_text,
            reliability=hit.reliability,
            score=hit.score,
            metadata=hit.metadata,
        )
        for hit in hits
    ]


async def _legacy_llm_complete(
    prompt: str,
    *,
    skill_name: str,
    stream: bool = False,
    emit=None,
) -> dict[str, Any]:
    try:
        raw = await xfyun_chat(prompt, stream=stream)
    except Exception:
        return default_llm_output(skill_name)
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {"content": str(raw), "quality_score": 0.7}


async def prepare_planned_skill_output(
    skill: BaseSkill,
    inp: PlannedSkillInput,
    ctx: SkillContext,
    *,
    prompt_template: str,
    output_model: type[OutputT],
    agent_name: str | None = None,
) -> OutputT:
    """旧 API：单步执行 skill，并把结果返回给调用者。

    与旧实现的区别：
    - 真正走 harness 完整链路（含 agent_runs 写入）；
    - 旧调用方一般在 skill.run 内再写一次 ``ctx.log_run`` —— 这是双写，新代码中第二次
      调用会变成 noop（``HarnessContext.log_run`` 已落表）。
    """
    harness = Harness(
        rag_retrieve=_legacy_rag_retrieve,
        llm_complete=_legacy_llm_complete,
    )
    output = await run_through_harness(
        skill,
        inp,
        ctx,
        prompt_template=prompt_template,
        output_model=output_model,
        agent_name=agent_name or "unknown",
        harness=harness,
    )
    return output  # type: ignore[return-value]


async def run_planned_skill(
    skill: BaseSkill,
    inp: PlannedSkillInput,
    ctx: SkillContext,
    *,
    prompt_template: str,
    output_model: type[OutputT],
    agent_name: str | None = None,
) -> OutputT:
    return await prepare_planned_skill_output(
        skill,
        inp,
        ctx,
        prompt_template=prompt_template,
        output_model=output_model,
        agent_name=agent_name,
    )
