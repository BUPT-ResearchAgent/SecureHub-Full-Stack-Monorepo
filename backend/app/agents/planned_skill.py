# Status: [planned]

from typing import TypeVar

from pydantic import BaseModel, Field

from app.agents.base import BaseSkill, InsufficientEvidence, SkillContext
from app.llm.xfyun import xfyun_chat
from app.rag.retriever import retrieve
from app.runtime.guardrails.output_filter import safety_review


class PlannedSkillInput(BaseModel):
    user_id: str
    query: str
    domain: str = "course_websec"


class PlannedSkillOutput(BaseModel):
    content: str
    evidence_chunk_ids: list[str] = Field(default_factory=list)
    quality_score: float = 0.0


OutputT = TypeVar("OutputT", bound=PlannedSkillOutput)


async def prepare_planned_skill_output(
    skill: BaseSkill,
    inp: PlannedSkillInput,
    ctx: SkillContext,
    *,
    prompt_template: str,
    output_model: type[OutputT],
) -> OutputT:
    hits = await retrieve(inp.query, domain=inp.domain, top_k=getattr(ctx.config, "MIN_EVIDENCE", 3))
    if len(hits) < getattr(ctx.config, "MIN_EVIDENCE", 3):
        raise InsufficientEvidence("TODO: evidence threshold not met")

    prompt = prompt_template.format(
        evidence_text="\n".join(hit.chunk_text for hit in hits),
        persona_text=ctx.persona_summary,
        task_instruction=inp.query,
        output_schema_hint=output_model.model_json_schema(),
    )

    raw = await xfyun_chat(prompt, stream=ctx.stream)
    out = output_model.model_validate_json(raw)
    out = safety_review(out)
    out.evidence_chunk_ids = [str(hit.chunk_id) for hit in hits]
    return out


async def run_planned_skill(
    skill: BaseSkill,
    inp: PlannedSkillInput,
    ctx: SkillContext,
    *,
    prompt_template: str,
    output_model: type[OutputT],
) -> OutputT:
    out = await prepare_planned_skill_output(
        skill,
        inp,
        ctx,
        prompt_template=prompt_template,
        output_model=output_model,
    )
    await ctx.log_run(
        agent_id=skill.agent_id,
        skill_id=skill.skill_id,
        input_summary=inp.model_dump(),
        output_summary=out.model_dump(),
        evidence_chunk_ids=out.evidence_chunk_ids,
        quality_score=out.quality_score,
    )
    return out
