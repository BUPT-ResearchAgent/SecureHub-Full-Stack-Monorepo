# Status: real

"""旧式 planned skill helper（兼容层）。

新代码应使用 ``app.agents._skill_helper.run_through_harness``；
本模块保留是为了不破坏 22 个已落地的 skill 文件入口。
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, Field

from app.agents.base import BaseSkill, SkillContext
from app.agents._skill_helper import run_through_harness


class PlannedSkillInput(BaseModel):
    user_id: str
    query: str
    domain: str = "course_websec"


class PlannedSkillOutput(BaseModel):
    content: str = ""
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
    agent_name: str | None = None,
) -> OutputT:
    """旧 API：单步执行 skill，并把结果返回给调用者。

    与旧实现的区别：
    - 真正走 harness 完整链路（含 agent_runs 写入）；
    - 旧调用方一般在 skill.run 内再写一次 ``ctx.log_run`` —— 这是双写，新代码中第二次
      调用会变成 noop（``HarnessContext.log_run`` 已落表）。
    """
    output = await run_through_harness(
        skill,
        inp,
        ctx,
        prompt_template=prompt_template,
        output_model=output_model,
        agent_name=agent_name or "unknown",
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
