# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class RecommendReadingsInput(SkillInput):
    kp_id: str | None = None


class RecommendReadingsOutput(SkillOutput):
    readings: list[dict[str, str]] = []


PROMPT_TEMPLATE = """
You are hot_analyst recommending educational readings.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class RecommendReadings(BaseSkill):
    name = "RecommendReadings"
    applicable_domains = ["paper", "course_websec"]
    output_schema = RecommendReadingsOutput
