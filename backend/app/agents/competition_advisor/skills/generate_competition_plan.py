# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class GenerateCompetitionPlanInput(PlannedSkillInput):
    deadline: str | None = None


class GenerateCompetitionPlanOutput(PlannedSkillOutput):
    milestones: list[dict[str, str]] = []


PROMPT_TEMPLATE = """
You are competition_advisor generating a competition preparation plan.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class GenerateCompetitionPlan(BaseSkill):
    name = "GenerateCompetitionPlan"
    applicable_domains = ["competition"]
    output_schema = GenerateCompetitionPlanOutput

    async def run(self, inp: GenerateCompetitionPlanInput, ctx: SkillContext) -> GenerateCompetitionPlanOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=GenerateCompetitionPlanOutput,
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
