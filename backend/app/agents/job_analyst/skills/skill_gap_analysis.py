# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class SkillGapAnalysisInput(SkillInput):
    target_role: str = "web_security_engineer"


class SkillGapAnalysisOutput(SkillOutput):
    gaps: list[dict[str, object]] = []
    fill_plan: list[str] = []


PROMPT_TEMPLATE = """
You are job_analyst diagnosing the gap between the learner profile and a target role.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class SkillGapAnalysis(BaseSkill):
    name = "SkillGapAnalysis"
    applicable_domains = ["job"]
    output_schema = SkillGapAnalysisOutput
