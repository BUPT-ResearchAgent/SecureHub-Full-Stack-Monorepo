# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class RecommendReadingsInput(PlannedSkillInput):
    kp_id: str | None = None


class RecommendReadingsOutput(PlannedSkillOutput):
    readings: list[dict[str, str]] = []


PROMPT_TEMPLATE = """
You are topic_explorer recommending course and research readings.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class RecommendReadings(BaseSkill):
    name = "RecommendReadings"
    applicable_domains = ["course_websec", "paper"]
    output_schema = RecommendReadingsOutput

    async def run(self, inp: RecommendReadingsInput, ctx: SkillContext) -> RecommendReadingsOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=RecommendReadingsOutput,
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
