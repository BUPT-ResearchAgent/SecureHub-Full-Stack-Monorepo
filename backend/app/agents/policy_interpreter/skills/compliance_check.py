# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class ComplianceCheckInput(PlannedSkillInput):
    target: dict[str, str] = {}


class ComplianceCheckOutput(PlannedSkillOutput):
    risk_score: float = 0.0
    items: list[dict[str, str]] = []


PROMPT_TEMPLATE = """
You are policy_interpreter running ComplianceCheck.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class ComplianceCheck(BaseSkill):
    name = "ComplianceCheck"
    applicable_domains = ["policy"]
    output_schema = ComplianceCheckOutput

    async def run(self, inp: ComplianceCheckInput, ctx: SkillContext) -> ComplianceCheckOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=ComplianceCheckOutput,
        )
        await ctx.log_run(
            agent_id=self.agent_id,
            skill_id=self.skill_id,
            input_summary=inp.model_dump(),
            output_summary=out.model_dump(),
            evidence_chunk_ids=out.evidence_chunk_ids,
            quality_score=out.quality_score,
        )
        return out
