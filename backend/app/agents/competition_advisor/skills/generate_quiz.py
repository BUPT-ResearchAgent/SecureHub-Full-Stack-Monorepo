# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class GenerateQuizInput(PlannedSkillInput):
    kp_id: str | None = None
    difficulty: int = 3


class GenerateQuizOutput(PlannedSkillOutput):
    quiz_items: list[dict[str, object]] = []


PROMPT_TEMPLATE = """
You are competition_advisor generating course quiz items.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Generate questions with explanations and evidence_chunk_ids. Do not fabricate CVEs or produce directly executable attack payloads.

Return JSON matching:
{output_schema_hint}
"""


class GenerateQuiz(BaseSkill):
    name = "GenerateQuiz"
    applicable_domains = ["course_websec"]
    output_schema = GenerateQuizOutput

    async def run(self, inp: GenerateQuizInput, ctx: SkillContext) -> GenerateQuizOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=GenerateQuizOutput,
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
