# Status: real

from app.agents._skill_helper import run_through_harness
from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput


class RouteTutorQuestionInput(PlannedSkillInput):
    question: str = ""


class RouteTutorQuestionOutput(PlannedSkillOutput):
    target_agent: str = "career_planner"
    target_skill: str = "RecommendResources"
    reason: str = ""


PROMPT_TEMPLATE = """
You are career_planner routing a tutor question to the right specialist agent.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Pick exactly one of: policy_interpreter / hot_analyst / topic_explorer / doc_archivist /
competition_advisor / outcome_evaluator. Explain the choice.

Return JSON matching:
{output_schema_hint}
"""


class RouteTutorQuestion(BaseSkill):
    name = "RouteTutorQuestion"
    applicable_domains = ["course_websec"]
    output_schema = RouteTutorQuestionOutput

    async def run(self, inp: RouteTutorQuestionInput, ctx: SkillContext) -> RouteTutorQuestionOutput:
        return await run_through_harness(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=RouteTutorQuestionOutput,
            agent_name="career_planner",
            capability_dim="planning",
            evidence_floor=1,  # routing 决策对证据要求低
        )  # type: ignore[return-value]
