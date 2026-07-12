# Status: real
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.
# Declarative Skill: SkillExecutor owns ctx.log_run for this contract.

from pydantic import Field, model_validator

from app.agents.base import BaseSkill
from app.agents.skill_contracts import SkillInput, SkillOutput
from app.runtime.contracts import QualityDefect


class QualityCheckInput(SkillInput):
    artifact: dict[str, object] = Field(default_factory=dict)


class QualityCheckOutput(SkillOutput):
    accept: bool = False
    defects: list[QualityDefect] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_a_consistent_decision(self) -> "QualityCheckOutput":
        if self.accept and self.defects:
            raise ValueError("accepted QualityCheck output cannot include defects")
        if not self.accept and not self.defects:
            raise ValueError("rejected QualityCheck output requires at least one defect")
        return self


PROMPT_TEMPLATE = """
You are outcome_evaluator checking generated output against evidence.

[Evidence]
{evidence_text}

[Persona]
{persona_text}

[Task]
{task_instruction}

[Generated artifacts to evaluate]
{artifact_text}

Evaluate the generated artifact above against the evidence and the requested
workflow task. Check only the artifact types that are actually present: a
persona, tutor answer, assessment, learning path, course document, quiz, lab,
or reading list may each be valid on its own. Do not require an unrelated
learning path, document, or quiz. Check factual support, internal consistency,
instructional relevance, and safety. The server owns evidence_chunk_ids; use
their presence as citation linkage and do not invent or rewrite them. Set
accept=true with defects=[] when there are no critical defects. Otherwise set
accept=false and return a non-empty defects list. Each defect must use exactly
the schema's code/message fields: code is one of evidence_missing,
fact_conflict, schema_invalid, instructional_mismatch, citation_mismatch, or
safety_violation; message is a concise explanation. Optional target_node and
resource_type may identify the affected producer. Do not use alternate keys
such as type, detail, issue, or reason.

Return JSON matching:
{output_schema_hint}
"""


class QualityCheck(BaseSkill):
    name = "QualityCheck"
    applicable_domains = ["course_websec"]
    output_schema = QualityCheckOutput
