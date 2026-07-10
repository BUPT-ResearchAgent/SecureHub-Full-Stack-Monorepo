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

Return concise Markdown content with evidence references as JSON matching the
schema below. JSON validity is mandatory: encode content and markdown as JSON
strings, escaping every newline, backslash, and internal double quote. Do not
use fenced code blocks. Express any code as short inline pseudocode that does
not contain double quotes. Keep the document focused enough to finish the JSON
object without truncation.

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
