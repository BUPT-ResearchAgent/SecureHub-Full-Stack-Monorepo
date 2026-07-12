# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class GenerateHandsOnLabInput(SkillInput):
    kp_id: str | None = None


class GenerateHandsOnLabOutput(SkillOutput):
    prerequisites: list[str] = []
    setup: list[str] = []
    steps: list[dict[str, str]] = []
    acceptance_criteria: list[str] = []
    hints: list[str] = []


PROMPT_TEMPLATE = """
You are topic_explorer generating a safe hands-on lab.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class GenerateHandsOnLab(BaseSkill):
    name = "GenerateHandsOnLab"
    applicable_domains = ["course_websec"]
    output_schema = GenerateHandsOnLabOutput
