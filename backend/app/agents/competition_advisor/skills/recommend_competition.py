# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class RecommendCompetitionInput(SkillInput):
    team_profile: dict[str, str] = {}


class RecommendCompetitionOutput(SkillOutput):
    competitions: list[dict[str, str]] = []


PROMPT_TEMPLATE = """
You are competition_advisor recommending competitions.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class RecommendCompetition(BaseSkill):
    name = "RecommendCompetition"
    applicable_domains = ["competition"]
    output_schema = RecommendCompetitionOutput
