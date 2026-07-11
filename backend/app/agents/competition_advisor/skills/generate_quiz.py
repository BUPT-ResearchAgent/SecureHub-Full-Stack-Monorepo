# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class GenerateQuizInput(SkillInput):
    kp_id: str | None = None
    difficulty: int = 3


class GenerateQuizOutput(SkillOutput):
    quiz_items: list[dict[str, object]] = []


PROMPT_TEMPLATE = """
You are competition_advisor generating course quiz items.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Generate questions with explanations and evidence_chunk_ids. Do not fabricate CVEs or produce directly executable attack payloads.

Return JSON matching:
{output_schema_hint}
"""


class GenerateQuiz(BaseSkill):
    name = "GenerateQuiz"
    applicable_domains = ["course_websec"]
    output_schema = GenerateQuizOutput
