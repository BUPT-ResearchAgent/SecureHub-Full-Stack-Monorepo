# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from pydantic import Field, model_validator

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class UpdatePersonaInput(SkillInput):
    learning_events: list[dict[str, object]] = Field(default_factory=list)
    persona_dimension_keys: list[str] = Field(default_factory=list)


class UpdatePersonaOutput(SkillOutput):
    # The final atomic assessment action consumes ``dimensions``. The former
    # updated_dimensions-only contract dropped a valid parsed persona patch.
    dimensions: dict[str, object] = Field(default_factory=dict)
    updated_dimensions: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def mirror_legacy_patch_into_action_field(self) -> "UpdatePersonaOutput":
        if not self.dimensions and self.updated_dimensions:
            self.dimensions = dict(self.updated_dimensions)
        return self


PROMPT_TEMPLATE = """
You are career_planner updating user_profiles.dimensions.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return a ``dimensions`` patch, not a replacement profile. Each changed value
must be traceable to supplied learning events or evidence. ``persona_dimension_keys``
is the server-authorized key set for the existing profile: use only those exact
keys and do not encode capability scores as persona dimensions. Preserve
dimensions that are not affected; do not invent missing persona values.

Return JSON matching:
{output_schema_hint}
"""


class UpdatePersona(BaseSkill):
    name = "UpdatePersona"
    applicable_domains = ["course_websec"]
    output_schema = UpdatePersonaOutput
