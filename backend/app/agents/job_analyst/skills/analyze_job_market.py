# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from pydantic import Field

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class AnalyzeJobMarketInput(SkillInput):
    target_role: str | None = None
    region: str | None = None
    fund_context: dict[str, object] = Field(default_factory=dict)


class AnalyzeJobMarketOutput(SkillOutput):
    trend: str = ""
    top_skills: list[str] = []
    # Only populated for fund_recommendation_v1. Existing job callers keep the
    # previous two-field result shape.
    fund_landscape: list[dict[str, object]] = Field(default_factory=list, max_length=12)


PROMPT_TEMPLATE = """
You are job_analyst summarizing the job market for security roles.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

When ``domain`` is ``fund``, analyse only the supplied fund evidence as an
opportunity landscape: programme name, direction, official source, published
deadline text, and the skills or project evidence it expects. Do not infer
amounts, availability, or deadlines that the evidence does not state. Return
``fund_landscape`` entries only when those facts are supported.

Return JSON matching:
{output_schema_hint}
"""


class AnalyzeJobMarket(BaseSkill):
    name = "AnalyzeJobMarket"
    # Compatibility extension of the existing frozen binding; this does not
    # create a twenty-ninth Skill Catalog binding.
    applicable_domains = ["job", "fund"]
    output_schema = AnalyzeJobMarketOutput
