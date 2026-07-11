# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class GenerateMindmapInput(SkillInput):
    kp_id: str | None = None


class GenerateMindmapOutput(SkillOutput):
    markmap_markdown: str = ""


PROMPT_TEMPLATE = """
You are doc_archivist generating a Markmap mindmap.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class GenerateMindmap(BaseSkill):
    name = "GenerateMindmap"
    applicable_domains = ["course_websec"]
    output_schema = GenerateMindmapOutput
