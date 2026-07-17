# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from pydantic import Field

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class RunAssessmentInput(SkillInput):
    answers: list[dict[str, object]] = Field(default_factory=list)


class RunAssessmentOutput(SkillOutput):
    """The durable assessment payload consumed by profile persistence and the course UI."""

    score: float = Field(ge=0.0, le=1.0)
    feedback: str = Field(min_length=1)
    capability_delta: dict[str, float] = Field(default_factory=dict)
    weak_kp_ids: list[str] = Field(default_factory=list)
    next_recommendation: str = ""
    # Kept for compatibility with historical roots. Persona persistence is
    # owned by the later UpdatePersona/final atomic action, never this model.
    updated_profile: dict[str, object] = Field(default_factory=dict)


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
When the input contains a ``server_verified_published_submission``
``assessment_summary``, its ``scoring.objective_floor_score`` was computed by
the server from the frozen assessment version and the durable learner
submission. It is a lower bound for the complete paper: never return a score
below it or describe the submission as incomplete solely because an answer was
bounded for prompt transport. Use linked Evidence only to assess the remaining
subjective content; do not invent subjective credit or a weakness.
When evidence is insufficient for a claimed weakness, keep the feedback to
what the submitted assessment actually supports instead of inventing a claim.

Return JSON matching:
{output_schema_hint}
"""


class RunAssessment(BaseSkill):
    name = "RunAssessment"
    applicable_domains = ["course_websec"]
    output_schema = RunAssessmentOutput
