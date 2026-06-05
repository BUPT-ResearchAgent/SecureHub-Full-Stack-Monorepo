# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class RunAssessmentInput(PlannedSkillInput):
    answers: list[dict[str, object]] = []


class RunAssessmentOutput(PlannedSkillOutput):
    assessment: dict[str, object] = {}
    updated_profile: dict[str, object] = {}


PROMPT_TEMPLATE = """
You are outcome_evaluator running learning assessment.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class RunAssessment(BaseSkill):
    name = "RunAssessment"
    applicable_domains = ["course_websec"]
    output_schema = RunAssessmentOutput

    async def run(self, inp: RunAssessmentInput, ctx: SkillContext) -> RunAssessmentOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=RunAssessmentOutput,
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
