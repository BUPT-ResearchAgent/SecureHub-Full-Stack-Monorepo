# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput


class GenerateProposalInput(SkillInput):
    topic: str | None = None
    structure: str = "innovation_competition"


class GenerateProposalOutput(SkillOutput):
    markdown: str = ""
    sections: list[str] = []


PROMPT_TEMPLATE = """
You are doc_archivist drafting a proposal document.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class GenerateProposal(BaseSkill):
    name = "GenerateProposal"
    applicable_domains = ["paper", "policy", "competition"]
    output_schema = GenerateProposalOutput
