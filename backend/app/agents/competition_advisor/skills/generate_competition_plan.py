# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class GenerateCompetitionPlanInput(SkillInput):
    deadline: str | None = None


class GenerateCompetitionPlanOutput(SkillOutput):
    milestones: list[dict[str, object]] = []


PROMPT_TEMPLATE = """
You are competition_advisor generating a competition preparation plan.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class GenerateCompetitionPlan(BaseSkill):
    name = "GenerateCompetitionPlan"
    applicable_domains = ["competition"]
    output_schema = GenerateCompetitionPlanOutput
