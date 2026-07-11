# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class BuildLearningPersonaInput(SkillInput):
    dialogue_turns: list[dict[str, str]] = []


class BuildLearningPersonaOutput(SkillOutput):
    dimensions: dict[str, object] = {}
    next_question: str | None = None


PROMPT_TEMPLATE = """
You are career_planner building a 6+ dimension learning persona.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Collect base_knowledge, cognitive_style, weak_points, preferred_modality, time_budget, target_direction, and motivation.

Return JSON matching:
{output_schema_hint}
"""


class BuildLearningPersona(BaseSkill):
    name = "BuildLearningPersona"
    applicable_domains = ["course_websec"]
    output_schema = BuildLearningPersonaOutput
