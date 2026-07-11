# Status: real

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class GenerateCourseDocInput(PlannedSkillInput):
    kp_id: str | None = None


class GenerateCourseDocOutput(PlannedSkillOutput):
    markdown: str = ""
    sections: list[str] = []


PROMPT_TEMPLATE = """
You are doc_archivist generating a course explanation document.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return a compact teaching summary with evidence references as JSON matching
the schema below. JSON validity is mandatory. For both ``content`` and
``markdown``, emit one single-line value only: no literal line breaks, no
internal double quote characters, no fenced code blocks, and at most 220 characters per
field. Use Chinese punctuation instead of quotation marks. Keep ``sections``
to at most three short labels. This bounded representation is required so the
provider can produce one unambiguous JSON object without truncation or invalid
string escaping.

Return JSON matching:
{output_schema_hint}
"""


class GenerateCourseDoc(BaseSkill):
    name = "GenerateCourseDoc"
    applicable_domains = ["course_websec"]
    output_schema = GenerateCourseDocOutput

    async def run(self, inp: GenerateCourseDocInput, ctx: SkillContext) -> GenerateCourseDocOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=GenerateCourseDocOutput,
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
