# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class GenerateVideoStoryboardInput(SkillInput):
    kp_id: str | None = None


class GenerateVideoStoryboardOutput(SkillOutput):
    mermaid: str = ""
    tts_segments: list[str] = []


PROMPT_TEMPLATE = """
You are doc_archivist generating a lightweight video storyboard and TTS script.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class GenerateVideoStoryboard(BaseSkill):
    name = "GenerateVideoStoryboard"
    applicable_domains = ["course_websec"]
    output_schema = GenerateVideoStoryboardOutput
