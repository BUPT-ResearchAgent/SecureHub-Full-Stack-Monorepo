# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class RecommendCompetitionInput(PlannedSkillInput):
    team_profile: dict[str, str] = {}


class RecommendCompetitionOutput(PlannedSkillOutput):
    competitions: list[dict[str, str]] = []


PROMPT_TEMPLATE = """
You are competition_advisor recommending competitions.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class RecommendCompetition(BaseSkill):
    name = "RecommendCompetition"
    applicable_domains = ["competition"]
    output_schema = RecommendCompetitionOutput

    async def run(self, inp: RecommendCompetitionInput, ctx: SkillContext) -> RecommendCompetitionOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=RecommendCompetitionOutput,
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
