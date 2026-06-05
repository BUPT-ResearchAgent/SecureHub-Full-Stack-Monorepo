# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class GenerateLearningPathInput(PlannedSkillInput):
    course_id: str | None = None


class GenerateLearningPathOutput(PlannedSkillOutput):
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, str]] = []
    milestones: list[dict[str, object]] = []


PROMPT_TEMPLATE = """
You are task_orchestrator generating a personalized learning path.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class GenerateLearningPath(BaseSkill):
    name = "GenerateLearningPath"
    applicable_domains = ["course_websec"]
    output_schema = GenerateLearningPathOutput

    async def run(self, inp: GenerateLearningPathInput, ctx: SkillContext) -> GenerateLearningPathOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=GenerateLearningPathOutput,
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
