# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class EvaluateSubmissionInput(SkillInput):
    submission: dict[str, object] = {}


class EvaluateSubmissionOutput(SkillOutput):
    score_vector: dict[str, float] = {}
    feedback: list[str] = []


PROMPT_TEMPLATE = """
You are outcome_evaluator evaluating a learner submission.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class EvaluateSubmission(BaseSkill):
    name = "EvaluateSubmission"
    applicable_domains = ["course_websec"]
    output_schema = EvaluateSubmissionOutput
