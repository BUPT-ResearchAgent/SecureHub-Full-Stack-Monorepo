# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from pydantic import Field

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class RecommendResourcesInput(SkillInput):
    current_kp_id: str | None = None


class RecommendResourcesOutput(SkillOutput):
    content: str = Field(min_length=1)
    resources: list[dict[str, object]] = []


PROMPT_TEMPLATE = """
You are career_planner recommending resources based on persona and progress.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

When this skill is used for a tutor question, `content` must be a direct,
evidence-grounded Chinese answer for the learner. It must answer the question
before suggesting optional resources. Do not expose routing decisions, provider
metadata, QualityCheck fields, or JSON-in-JSON text to the learner.

Return JSON matching:
{output_schema_hint}
"""


class RecommendResources(BaseSkill):
    name = "RecommendResources"
    applicable_domains = ["course_websec"]
    output_schema = RecommendResourcesOutput
