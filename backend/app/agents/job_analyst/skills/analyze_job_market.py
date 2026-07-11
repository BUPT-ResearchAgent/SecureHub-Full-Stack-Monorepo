# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class AnalyzeJobMarketInput(SkillInput):
    target_role: str | None = None
    region: str | None = None


class AnalyzeJobMarketOutput(SkillOutput):
    trend: str = ""
    top_skills: list[str] = []


PROMPT_TEMPLATE = """
You are job_analyst summarizing the job market for security roles.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class AnalyzeJobMarket(BaseSkill):
    name = "AnalyzeJobMarket"
    applicable_domains = ["job"]
    output_schema = AnalyzeJobMarketOutput
