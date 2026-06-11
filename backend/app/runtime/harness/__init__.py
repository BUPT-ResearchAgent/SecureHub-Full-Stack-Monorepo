# Status: real

"""Skill execution harness.

Implements the unified skill execution chain mandated by the project ironclad rules:

    validate -> rag.retrieve -> evidence_floor -> compose prompt -> LLM ->
    parse output -> safety review -> quality_check (optional) -> log_run

Every generative skill in SecureHub MUST run through this harness so that:
- evidence floor is enforced (>= MIN_EVIDENCE chunks)
- evidence_chunk_ids are propagated to outputs
- agent_runs is written for every invocation
- guardrails + quality check are applied
- mock / fixture fallback is available when no LLM API key is configured
"""

from app.runtime.harness.base import Harness, SkillSpec, run_skill
from app.runtime.harness.context import HarnessContext
from app.runtime.harness.errors import (
    GuardrailViolation,
    HarnessError,
    InsufficientEvidence,
    QualityCheckFailed,
    SafetyBlocked,
    ToolUnavailable,
)
from app.runtime.harness.types import EvidenceCard, RunStatus, SkillIO

__all__ = [
    "Harness",
    "HarnessContext",
    "SkillSpec",
    "SkillIO",
    "EvidenceCard",
    "RunStatus",
    "GuardrailViolation",
    "HarnessError",
    "InsufficientEvidence",
    "QualityCheckFailed",
    "SafetyBlocked",
    "ToolUnavailable",
    "run_skill",
]
