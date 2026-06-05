# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class GenerateCoursePPTInput(PlannedSkillInput):
    kp_id: str | None = None


class GenerateCoursePPTOutput(PlannedSkillOutput):
    reveal_markdown: str = ""
    slides: list[dict[str, str]] = []


PROMPT_TEMPLATE = """
You are doc_archivist generating reveal.js course slides.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class GenerateCoursePPT(BaseSkill):
    name = "GenerateCoursePPT"
    applicable_domains = ["course_websec"]
    output_schema = GenerateCoursePPTOutput

    async def run(self, inp: GenerateCoursePPTInput, ctx: SkillContext) -> GenerateCoursePPTOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=GenerateCoursePPTOutput,
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
