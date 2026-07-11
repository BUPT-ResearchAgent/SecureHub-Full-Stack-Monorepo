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
You are topic_explorer recommending course and research readings.

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
    applicable_domains = ["course_websec", "paper"]
    output_schema = RecommendReadingsOutput
