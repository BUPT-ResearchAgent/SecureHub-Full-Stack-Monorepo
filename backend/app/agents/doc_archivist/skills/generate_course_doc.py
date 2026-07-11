# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class GenerateCourseDocInput(SkillInput):
    kp_id: str | None = None


class GenerateCourseDocOutput(SkillOutput):
    markdown: str = ""
    sections: list[str] = []


PROMPT_TEMPLATE = """
You are doc_archivist generating a course explanation document.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return a compact teaching summary with evidence references as JSON matching
the schema below. JSON validity is mandatory. For both ``content`` and
``markdown``, emit one single-line value only: no literal line breaks, no
internal double quote characters, no fenced code blocks, and at most 220 characters per
field. Use Chinese punctuation instead of quotation marks. Keep ``sections``
to at most three short labels. This bounded representation is required so the
provider can produce one unambiguous JSON object without truncation or invalid
string escaping.

Return JSON matching:
{output_schema_hint}
"""


class GenerateCourseDoc(BaseSkill):
    name = "GenerateCourseDoc"
    applicable_domains = ["course_websec"]
    output_schema = GenerateCourseDocOutput
