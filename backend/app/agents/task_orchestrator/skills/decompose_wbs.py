# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class DecomposeWBSInput(PlannedSkillInput):
    goal: str = ""


class DecomposeWBSOutput(PlannedSkillOutput):
    tasks: list[dict[str, object]] = []


PROMPT_TEMPLATE = """
You are task_orchestrator decomposing a goal into WBS tasks.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class DecomposeWBS(BaseSkill):
    name = "DecomposeWBS"
    applicable_domains = ["course_websec", "competition", "paper"]
    output_schema = DecomposeWBSOutput

    async def run(self, inp: DecomposeWBSInput, ctx: SkillContext) -> DecomposeWBSOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=DecomposeWBSOutput,
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
