# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class RunAssessmentInput(SkillInput):
    answers: list[dict[str, object]] = []


class RunAssessmentOutput(SkillOutput):
    assessment: dict[str, object] = {}
    updated_profile: dict[str, object] = {}


PROMPT_TEMPLATE = """
You are outcome_evaluator running learning assessment.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class RunAssessment(BaseSkill):
    name = "RunAssessment"
    applicable_domains = ["course_websec"]
    output_schema = RunAssessmentOutput
