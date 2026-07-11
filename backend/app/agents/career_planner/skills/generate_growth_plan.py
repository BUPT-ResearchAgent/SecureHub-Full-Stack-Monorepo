# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class GenerateGrowthPlanInput(SkillInput):
    horizon_months: int = 6
    target_role: str | None = None


class GenerateGrowthPlanOutput(SkillOutput):
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
