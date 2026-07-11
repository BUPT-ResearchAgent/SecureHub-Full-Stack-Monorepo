# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class InterpretPolicyInput(SkillInput):
    target_type: str = "course"


class InterpretPolicyOutput(SkillOutput):
    summary: str = ""
    capability_mapping: dict[str, str] = {}
    compliance_risks: list[str] = []
    suggestions: list[str] = []
    citations: list[str] = []


PROMPT_TEMPLATE = """
You are policy_interpreter. Use only retrieved policy evidence.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class InterpretPolicy(BaseSkill):
    name = "InterpretPolicy"
    applicable_domains = ["policy"]
    output_schema = InterpretPolicyOutput
