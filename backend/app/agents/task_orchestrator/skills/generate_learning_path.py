# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class GenerateLearningPathInput(SkillInput):
    course_id: str | None = None


class GenerateLearningPathOutput(SkillOutput):
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, str]] = []
    milestones: list[dict[str, object]] = []


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
