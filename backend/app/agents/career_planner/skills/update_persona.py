# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class UpdatePersonaInput(PlannedSkillInput):
    learning_events: list[dict[str, object]] = []


class UpdatePersonaOutput(PlannedSkillOutput):
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

    async def run(self, inp: UpdatePersonaInput, ctx: SkillContext) -> UpdatePersonaOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=UpdatePersonaOutput,
        )
        await ctx.log_run(
            agent_id=self.agent_id,
            skill_id=self.skill_id,
            input_summary=inp.model_dump(),
            output_summary=out.model_dump(),
            evidence_chunk_ids=out.evidence_chunk_ids,
            quality_score=out.quality_score,
        )
        return out
