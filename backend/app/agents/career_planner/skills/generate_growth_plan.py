# Status: real

from app.agents._skill_helper import run_through_harness
from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput


class GenerateGrowthPlanInput(PlannedSkillInput):
    horizon_months: int = 6
    target_role: str | None = None


class GenerateGrowthPlanOutput(PlannedSkillOutput):
    milestones: list[dict[str, object]] = []
    resources: list[dict[str, object]] = []


PROMPT_TEMPLATE = """
You are career_planner crafting a long-horizon growth plan.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class GenerateGrowthPlan(BaseSkill):
    name = "GenerateGrowthPlan"
    applicable_domains = ["course_websec", "job", "competition"]
    output_schema = GenerateGrowthPlanOutput

    async def run(self, inp: GenerateGrowthPlanInput, ctx: SkillContext) -> GenerateGrowthPlanOutput:
        return await run_through_harness(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=GenerateGrowthPlanOutput,
            agent_name="career_planner",
            capability_dim="planning",
        )  # type: ignore[return-value]
