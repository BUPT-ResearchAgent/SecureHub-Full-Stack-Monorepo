# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from pydantic import Field

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class UpdateCapabilityInput(SkillInput):
    score_vector: dict[str, float] = Field(default_factory=dict)
    capability_dimensions: list[str] = Field(default_factory=list)


class UpdateCapabilityOutput(SkillOutput):
    capability_delta: dict[str, float] = Field(default_factory=dict)
    updated_dimensions: dict[str, object] = Field(default_factory=dict)


PROMPT_TEMPLATE = """
You are outcome_evaluator updating user capability dimensions.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return only signed changes justified by the supplied assessment and evidence.
``capability_dimensions`` is the complete server-authorized set of existing
``user_capabilities`` rows for this learner. Every key in ``capability_delta``
must be one of those exact values. Map an assessment-specific concept to its
closest listed dimension; never invent a new capability name or baseline.
Do not fabricate a baseline score, evidence count, or an unevaluated dimension.

Return JSON matching:
{output_schema_hint}
"""


class UpdateCapability(BaseSkill):
    name = "UpdateCapability"
    applicable_domains = ["course_websec"]
    output_schema = UpdateCapabilityOutput
