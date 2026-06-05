# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class GenerateMindmapInput(PlannedSkillInput):
    kp_id: str | None = None


class GenerateMindmapOutput(PlannedSkillOutput):
    markmap_markdown: str = ""


PROMPT_TEMPLATE = """
You are doc_archivist generating a Markmap mindmap.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class GenerateMindmap(BaseSkill):
    name = "GenerateMindmap"
    applicable_domains = ["course_websec"]
    output_schema = GenerateMindmapOutput

    async def run(self, inp: GenerateMindmapInput, ctx: SkillContext) -> GenerateMindmapOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=GenerateMindmapOutput,
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
