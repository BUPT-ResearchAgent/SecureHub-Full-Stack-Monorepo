# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class GenerateHandsOnLabInput(PlannedSkillInput):
    kp_id: str | None = None


class GenerateHandsOnLabOutput(PlannedSkillOutput):
    prerequisites: list[str] = []
    setup: list[str] = []
    steps: list[dict[str, str]] = []
    acceptance_criteria: list[str] = []
    hints: list[str] = []


PROMPT_TEMPLATE = """
You are topic_explorer generating a safe hands-on lab.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class GenerateHandsOnLab(BaseSkill):
    name = "GenerateHandsOnLab"
    applicable_domains = ["course_websec"]
    output_schema = GenerateHandsOnLabOutput

    async def run(self, inp: GenerateHandsOnLabInput, ctx: SkillContext) -> GenerateHandsOnLabOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=GenerateHandsOnLabOutput,
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
