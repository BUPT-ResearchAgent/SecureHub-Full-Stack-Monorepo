# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class UpdateCapabilityInput(SkillInput):
    score_vector: dict[str, float] = {}


class UpdateCapabilityOutput(SkillOutput):
    capability_delta: dict[str, float] = {}
    updated_dimensions: dict[str, object] = {}


PROMPT_TEMPLATE = """
You are outcome_evaluator updating user capability dimensions.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class UpdateCapability(BaseSkill):
    name = "UpdateCapability"
    applicable_domains = ["course_websec"]
    output_schema = UpdateCapabilityOutput
