# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class EvaluateSubmissionInput(PlannedSkillInput):
    submission: dict[str, object] = {}


class EvaluateSubmissionOutput(PlannedSkillOutput):
    score_vector: dict[str, float] = {}
    feedback: list[str] = []


PROMPT_TEMPLATE = """
You are outcome_evaluator evaluating a learner submission.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class EvaluateSubmission(BaseSkill):
    name = "EvaluateSubmission"
    applicable_domains = ["course_websec"]
    output_schema = EvaluateSubmissionOutput

    async def run(self, inp: EvaluateSubmissionInput, ctx: SkillContext) -> EvaluateSubmissionOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=EvaluateSubmissionOutput,
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
