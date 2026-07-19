# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from pydantic import Field

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput
from app.schemas.course_plan_profile import CoursePlanProfileSnapshot, CoursePlanRationaleCode


class GenerateLearningPathInput(SkillInput):
    course_id: str | None = None
    profile_snapshot: CoursePlanProfileSnapshot = Field(default_factory=CoursePlanProfileSnapshot)
    profile_reason_codes: tuple[CoursePlanRationaleCode, ...] = Field(default_factory=tuple)


class GenerateLearningPathOutput(SkillOutput):
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, str]] = []
    milestones: list[dict[str, object]] = []
    # The provider may add a bounded, user-facing explanation. The durable
    # action still records server-generated reason codes as the audit source.
    personalization_rationale: list[CoursePlanRationaleCode] = Field(default_factory=list, max_length=8)


PROMPT_TEMPLATE = """
You are task_orchestrator generating a personalized learning path.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class GenerateLearningPath(BaseSkill):
    name = "GenerateLearningPath"
    applicable_domains = ["course_websec"]
    output_schema = GenerateLearningPathOutput
