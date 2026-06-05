# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class GenerateResearchTopicInput(PlannedSkillInput):
    constraints: dict[str, str] = {}


class GenerateResearchTopicOutput(PlannedSkillOutput):
    topics: list[dict[str, object]] = []


PROMPT_TEMPLATE = """
You are topic_explorer generating bounded research topic candidates.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class GenerateResearchTopic(BaseSkill):
    name = "GenerateResearchTopic"
    applicable_domains = ["paper", "policy"]
    output_schema = GenerateResearchTopicOutput

    async def run(self, inp: GenerateResearchTopicInput, ctx: SkillContext) -> GenerateResearchTopicOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=GenerateResearchTopicOutput,
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
