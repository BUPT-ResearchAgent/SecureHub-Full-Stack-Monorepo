# Status: real

from app.agents._skill_helper import run_through_harness
from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput


class GenerateProposalInput(PlannedSkillInput):
    topic: str | None = None
    structure: str = "innovation_competition"


class GenerateProposalOutput(PlannedSkillOutput):
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

    async def run(self, inp: GenerateProposalInput, ctx: SkillContext) -> GenerateProposalOutput:
        return await run_through_harness(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=GenerateProposalOutput,
            agent_name="doc_archivist",
            capability_dim="doc",
        )  # type: ignore[return-value]
