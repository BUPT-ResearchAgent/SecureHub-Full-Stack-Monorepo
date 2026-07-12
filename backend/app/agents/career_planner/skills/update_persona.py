# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class UpdatePersonaInput(SkillInput):
    learning_events: list[dict[str, object]] = []


class UpdatePersonaOutput(SkillOutput):
    updated_dimensions: dict[str, object] = {}


PROMPT_TEMPLATE = """
You are career_planner updating user_profiles.dimensions.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class UpdatePersona(BaseSkill):
    name = "UpdatePersona"
    applicable_domains = ["course_websec"]
    output_schema = UpdatePersonaOutput
