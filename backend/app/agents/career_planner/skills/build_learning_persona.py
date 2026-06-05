# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class BuildLearningPersonaInput(PlannedSkillInput):
    dialogue_turns: list[dict[str, str]] = []


class BuildLearningPersonaOutput(PlannedSkillOutput):
    dimensions: dict[str, object] = {}
    next_question: str | None = None


PROMPT_TEMPLATE = """
You are career_planner building a 6+ dimension learning persona.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Collect base_knowledge, cognitive_style, weak_points, preferred_modality, time_budget, target_direction, and motivation.

Return JSON matching:
{output_schema_hint}
"""


class BuildLearningPersona(BaseSkill):
    name = "BuildLearningPersona"
    applicable_domains = ["course_websec"]
    output_schema = BuildLearningPersonaOutput

    async def run(self, inp: BuildLearningPersonaInput, ctx: SkillContext) -> BuildLearningPersonaOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=BuildLearningPersonaOutput,
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
