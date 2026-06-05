# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class QualityCheckInput(PlannedSkillInput):
    artifact: dict[str, object] = {}


class QualityCheckOutput(PlannedSkillOutput):
    accept: bool = False
    defects: list[dict[str, str]] = []


PROMPT_TEMPLATE = """
You are outcome_evaluator checking generated output against evidence.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class QualityCheck(BaseSkill):
    name = "QualityCheck"
    applicable_domains = ["course_websec"]
    output_schema = QualityCheckOutput

    async def run(self, inp: QualityCheckInput, ctx: SkillContext) -> QualityCheckOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=QualityCheckOutput,
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
