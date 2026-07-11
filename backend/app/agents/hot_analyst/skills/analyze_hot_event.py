# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class AnalyzeHotEventInput(SkillInput):
    event_id: str | None = None
    time_window: str = "7d"


class AnalyzeHotEventOutput(SkillOutput):
    summary: str = ""
    edu_value: float = 0.0
    abuse_risk: str = "low"


PROMPT_TEMPLATE = """
You are hot_analyst evaluating a security event for its educational value.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class AnalyzeHotEvent(BaseSkill):
    name = "AnalyzeHotEvent"
    applicable_domains = ["course_websec", "paper", "news"]
    output_schema = AnalyzeHotEventOutput
