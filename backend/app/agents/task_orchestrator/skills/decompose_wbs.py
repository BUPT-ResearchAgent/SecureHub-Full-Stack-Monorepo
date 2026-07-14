# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class DecomposeWBSInput(SkillInput):
    goal: str = ""


class DecomposeWBSOutput(SkillOutput):
    tasks: list[dict[str, object]] = []


PROMPT_TEMPLATE = """
You are task_orchestrator decomposing a goal into WBS tasks.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class DecomposeWBS(BaseSkill):
    name = "DecomposeWBS"
    applicable_domains = ["course_websec", "competition", "paper"]
    output_schema = DecomposeWBSOutput
