# Status: real

"""统一的 skill 入口 helper。

旧版 ``planned_skill.py`` 用 ``NotImplementedError`` 占位；本 helper 把每个 skill 的
入口收敛到 ``run_through_harness`` 一次调用：

1. 构造 ``SkillSpec``（prompt template / output model / evidence floor / capability dim）；
2. 透传到 ``Harness.run``；
3. Harness 负责：
   - rag.retrieve（兜底 fixture）
   - LLM 调用（兜底 fixture）
   - evidence floor
   - safety review
   - quality check
   - agent_runs 写入
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.agents.base import BaseSkill, SkillContext
from app.runtime.harness import (
    Harness,
    HarnessContext,
    SkillSpec,
    run_skill,
)


def _to_harness_context(ctx: SkillContext | HarnessContext) -> HarnessContext:
    if isinstance(ctx, HarnessContext):
        return ctx
    return HarnessContext(
        user_id=ctx.user_id,
        workflow_name=ctx.workflow_name,
        persona_summary=ctx.persona_summary,
        stream=ctx.stream,
        config=ctx.config,  # type: ignore[arg-type]
        log_run=_proxy_log_run(ctx),  # adapter to old SkillContext.log_run
    )


def _proxy_log_run(ctx: SkillContext):
    """Adapt old SkillContext.log_run signature into harness logger signature."""

    async def _adapter(
        *,
        run_id: UUID | None = None,
        workflow_name: str,
        user_id: UUID | str | None,
        agent_id: UUID | str | None,
        skill_id: UUID | str | None,
        parent_run_id: UUID | str | None,
        input_summary: dict[str, Any],
        output_summary: dict[str, Any],
        evidence_chunk_ids: list[UUID | str],
        quality_score: float | None,
        status: str,
        duration_ms: int | None,
        token_usage: dict[str, Any],
    ) -> None:
        # Fall back to the harness-level logger so we always hit agent_runs.
        from app.runtime.logger import log_agent_run

        await log_agent_run(
            run_id=run_id,
            workflow_name=workflow_name or ctx.workflow_name,
            user_id=user_id or ctx.user_id,
            agent_id=agent_id,
            skill_id=skill_id,
            parent_run_id=parent_run_id,
            input_summary=input_summary,
            output_summary=output_summary,
            evidence_chunk_ids=evidence_chunk_ids,
            quality_score=quality_score,
            status=status,
            duration_ms=duration_ms,
            token_usage=token_usage,
        )

    return _adapter


async def run_through_harness(
    skill: BaseSkill,
    inp: BaseModel,
    ctx: SkillContext | HarnessContext,
    *,
    spec_overrides: dict[str, Any] | None = None,
    prompt_template: str,
    output_model: type[BaseModel],
    agent_name: str,
    capability_dim: str = "doc",
    evidence_floor: int | None = None,
    quality_check: bool = True,
    applicable_domains: list[str] | None = None,
    harness: Harness | None = None,
) -> BaseModel:
    floor = evidence_floor if evidence_floor is not None else getattr(ctx.config, "MIN_EVIDENCE", 3)
    spec = SkillSpec(
        name=skill.name,
        agent_name=agent_name,
        input_model=type(inp),
        output_model=output_model,
        prompt_template=prompt_template,
        applicable_domains=applicable_domains or skill.applicable_domains or ["course_websec"],
        evidence_floor=floor,
        quality_check=quality_check,
        capability_dim=capability_dim,
        agent_id=skill.agent_id,
        skill_id=skill.skill_id,
    )
    if spec_overrides:
        for k, v in spec_overrides.items():
            setattr(spec, k, v)
    harness_ctx = _to_harness_context(ctx)
    return await run_skill(spec, inp, harness_ctx, harness=harness)
