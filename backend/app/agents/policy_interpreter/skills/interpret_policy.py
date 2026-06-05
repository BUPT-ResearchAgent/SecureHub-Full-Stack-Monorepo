# Status: [planned]

from app.agents.base import BaseSkill, SkillContext
from app.agents.planned_skill import PlannedSkillInput, PlannedSkillOutput, prepare_planned_skill_output


class InterpretPolicyInput(PlannedSkillInput):
    target_type: str = "course"


class InterpretPolicyOutput(PlannedSkillOutput):
    summary: str = ""
    capability_mapping: dict[str, str] = {}
    compliance_risks: list[str] = []
    suggestions: list[str] = []
    citations: list[str] = []


PROMPT_TEMPLATE = """
You are policy_interpreter. Use only retrieved policy evidence.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

Return JSON matching:
{output_schema_hint}
"""


class InterpretPolicy(BaseSkill):
    name = "InterpretPolicy"
    applicable_domains = ["policy"]
    output_schema = InterpretPolicyOutput

    async def run(self, inp: InterpretPolicyInput, ctx: SkillContext) -> InterpretPolicyOutput:
        out = await prepare_planned_skill_output(
            self,
            inp,
            ctx,
            prompt_template=PROMPT_TEMPLATE,
            output_model=InterpretPolicyOutput,
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
