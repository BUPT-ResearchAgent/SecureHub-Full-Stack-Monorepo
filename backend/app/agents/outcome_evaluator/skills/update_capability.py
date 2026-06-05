# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class UpdateCapabilityInput(PlannedSkillInput):
    score_vector: dict[str, float] = {}


class UpdateCapabilityOutput(PlannedSkillOutput):
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

    async def run(self, inp: UpdateCapabilityInput, ctx: SkillContext) -> UpdateCapabilityOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=UpdateCapabilityOutput,
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
