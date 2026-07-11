# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class GenerateResearchTopicInput(SkillInput):
    constraints: dict[str, str] = {}


class GenerateResearchTopicOutput(SkillOutput):
    topics: list[dict[str, object]] = []


PROMPT_TEMPLATE = """
You are topic_explorer generating bounded research topic candidates.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class GenerateResearchTopic(BaseSkill):
    name = "GenerateResearchTopic"
    applicable_domains = ["paper", "policy"]
    output_schema = GenerateResearchTopicOutput
