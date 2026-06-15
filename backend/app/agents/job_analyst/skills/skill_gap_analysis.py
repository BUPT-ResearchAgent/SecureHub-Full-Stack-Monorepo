# Status: real

from app.agents._skill_helper import run_through_harness
from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput


class SkillGapAnalysisInput(PlannedSkillInput):
    target_role: str = "web_security_engineer"


class SkillGapAnalysisOutput(PlannedSkillOutput):
    gaps: list[dict[str, object]] = []
    fill_plan: list[str] = []


PROMPT_TEMPLATE = """
You are job_analyst diagnosing the gap between the learner profile and a target role.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class SkillGapAnalysis(BaseSkill):
    name = "SkillGapAnalysis"
    applicable_domains = ["job"]
    output_schema = SkillGapAnalysisOutput

    async def run(self, inp: SkillGapAnalysisInput, ctx: SkillContext) -> SkillGapAnalysisOutput:
        return await run_through_harness(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=SkillGapAnalysisOutput,
            agent_name="job_analyst",
            capability_dim="job",
            evidence_floor=1,
        )  # type: ignore[return-value]
