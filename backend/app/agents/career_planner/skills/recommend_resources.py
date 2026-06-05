# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class RecommendResourcesInput(PlannedSkillInput):
    current_kp_id: str | None = None


class RecommendResourcesOutput(PlannedSkillOutput):
    resources: list[dict[str, object]] = []


PROMPT_TEMPLATE = """
You are career_planner recommending resources based on persona and progress.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class RecommendResources(BaseSkill):
    name = "RecommendResources"
    applicable_domains = ["course_websec"]
    output_schema = RecommendResourcesOutput

    async def run(self, inp: RecommendResourcesInput, ctx: SkillContext) -> RecommendResourcesOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=RecommendResourcesOutput,
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
