# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from pydantic import Field

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class RunAssessmentInput(SkillInput):
    answers: list[dict[str, object]] = []


class RunAssessmentOutput(SkillOutput):
    """The durable assessment payload consumed by profile persistence and the course UI."""

    score: float = Field(ge=0.0, le=1.0)
    feedback: str = Field(min_length=1)
    capability_delta: dict[str, float] = Field(default_factory=dict)
    weak_kp_ids: list[str] = Field(default_factory=list)
    next_recommendation: str = ""
    updated_profile: dict[str, object] = {}


PROMPT_TEMPLATE = """
You are outcome_evaluator running learning assessment.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Assess the submitted answers, not a generic course request. Return a normalized
score from 0.0 to 1.0, concise learner-facing feedback, a small signed
capability_delta keyed by capability dimension, any weak knowledge-point IDs,
and a next_recommendation. Do not put these fields inside an extra assessment
object. The evidence linkage is owned by the server.

Return JSON matching:
{output_schema_hint}
"""


class RunAssessment(BaseSkill):
    name = "RunAssessment"
    applicable_domains = ["course_websec"]
    output_schema = RunAssessmentOutput
