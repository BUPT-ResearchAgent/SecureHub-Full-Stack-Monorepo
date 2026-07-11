# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class ComplianceCheckInput(SkillInput):
    target: dict[str, str] = {}


class ComplianceCheckOutput(SkillOutput):
    risk_score: float = 0.0
    items: list[dict[str, str]] = []


PROMPT_TEMPLATE = """
You are policy_interpreter running ComplianceCheck.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class ComplianceCheck(BaseSkill):
    name = "ComplianceCheck"
    applicable_domains = ["policy"]
    output_schema = ComplianceCheckOutput
