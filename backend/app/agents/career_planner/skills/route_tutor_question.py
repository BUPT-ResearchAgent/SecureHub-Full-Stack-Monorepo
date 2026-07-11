# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class RouteTutorQuestionInput(SkillInput):
    question: str = ""


class RouteTutorQuestionOutput(SkillOutput):
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
