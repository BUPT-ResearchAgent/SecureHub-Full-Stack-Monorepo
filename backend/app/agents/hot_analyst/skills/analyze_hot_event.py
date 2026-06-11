# Status: real

from app.agents._skill_helper import run_through_harness
from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput


class AnalyzeHotEventInput(PlannedSkillInput):
    event_id: str | None = None
    time_window: str = "7d"


class AnalyzeHotEventOutput(PlannedSkillOutput):
    summary: str = ""
    edu_value: float = 0.0
    abuse_risk: str = "low"


PROMPT_TEMPLATE = """
You are hot_analyst evaluating a security event for its educational value.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class AnalyzeHotEvent(BaseSkill):
    name = "AnalyzeHotEvent"
    applicable_domains = ["course_websec", "paper", "news"]
    output_schema = AnalyzeHotEventOutput

    async def run(self, inp: AnalyzeHotEventInput, ctx: SkillContext) -> AnalyzeHotEventOutput:
        return await run_through_harness(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=AnalyzeHotEventOutput,
            agent_name="hot_analyst",
            capability_dim="hot",
        )  # type: ignore[return-value]
