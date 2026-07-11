# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class GenerateCoursePPTInput(SkillInput):
    kp_id: str | None = None


class GenerateCoursePPTOutput(SkillOutput):
    reveal_markdown: str = ""
    slides: list[dict[str, object]] = []


PROMPT_TEMPLATE = """
You are doc_archivist generating reveal.js course slides.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class GenerateCoursePPT(BaseSkill):
    name = "GenerateCoursePPT"
    applicable_domains = ["course_websec"]
    output_schema = GenerateCoursePPTOutput
