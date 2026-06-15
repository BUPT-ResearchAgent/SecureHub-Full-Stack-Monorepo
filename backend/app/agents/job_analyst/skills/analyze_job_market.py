# Status: real

from app.agents._skill_helper import run_through_harness
from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput


class AnalyzeJobMarketInput(PlannedSkillInput):
    target_role: str | None = None
    region: str | None = None


class AnalyzeJobMarketOutput(PlannedSkillOutput):
    trend: str = ""
    top_skills: list[str] = []


PROMPT_TEMPLATE = """
You are job_analyst summarizing the job market for security roles.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class AnalyzeJobMarket(BaseSkill):
    name = "AnalyzeJobMarket"
    applicable_domains = ["job"]
    output_schema = AnalyzeJobMarketOutput

    async def run(self, inp: AnalyzeJobMarketInput, ctx: SkillContext) -> AnalyzeJobMarketOutput:
        return await run_through_harness(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=AnalyzeJobMarketOutput,
            agent_name="job_analyst",
            capability_dim="job",
            evidence_floor=1,
        )  # type: ignore[return-value]
