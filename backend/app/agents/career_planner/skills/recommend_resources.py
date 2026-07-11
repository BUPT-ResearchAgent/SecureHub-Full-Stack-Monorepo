# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class RecommendResourcesInput(SkillInput):
    current_kp_id: str | None = None


class RecommendResourcesOutput(SkillOutput):
    resources: list[dict[str, object]] = []


PROMPT_TEMPLATE = """
You are career_planner recommending resources based on persona and progress.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class RecommendResources(BaseSkill):
    name = "RecommendResources"
    applicable_domains = ["course_websec"]
    output_schema = RecommendResourcesOutput
