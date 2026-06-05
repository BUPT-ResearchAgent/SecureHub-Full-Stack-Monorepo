# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class GenerateVideoStoryboardInput(PlannedSkillInput):
    kp_id: str | None = None


class GenerateVideoStoryboardOutput(PlannedSkillOutput):
    mermaid: str = ""
    tts_segments: list[str] = []


PROMPT_TEMPLATE = """
You are doc_archivist generating a lightweight video storyboard and TTS script.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class GenerateVideoStoryboard(BaseSkill):
    name = "GenerateVideoStoryboard"
    applicable_domains = ["course_websec"]
    output_schema = GenerateVideoStoryboardOutput

    async def run(self, inp: GenerateVideoStoryboardInput, ctx: SkillContext) -> GenerateVideoStoryboardOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=GenerateVideoStoryboardOutput,
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
