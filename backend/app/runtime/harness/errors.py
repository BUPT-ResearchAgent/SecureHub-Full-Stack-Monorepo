# Status: real

"""Harness-level exceptions.

These are the canonical error classes raised inside the skill harness. They map
1:1 to SSE error event codes consumed by the frontend.
"""


class HarnessError(RuntimeError):
    """Base class for harness-managed errors. Carries an SSE-friendly code."""

    code: str = "harness_error"

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.code)
        self.message = message or self.code


class InsufficientEvidence(HarnessError):
    """Evidence floor not met: refuse to call LLM (rule §3.6)."""

    code = "insufficient_evidence"


class ToolUnavailable(HarnessError):
    """A required tool (LLM provider, RAG, storage) could not be reached."""

    code = "tool_unavailable"


class LLMOutputInvalid(HarnessError):
    """A strict provider response was not valid JSON for the required schema."""

    code = "llm_output_invalid"


class AgentRunPersistenceFailed(HarnessError):
    """A strict real skill could not verify its ``agent_runs`` write."""

    code = "agent_run_persist_failed"


class CancellationRequested(HarnessError):
    """Cooperative cancellation signal propagated through a streaming skill."""

    code = "cancellation_requested"


class SafetyBlocked(HarnessError):
    """Input or output guardrail flagged the request as unsafe."""

    code = "safety_blocked"


class GuardrailViolation(HarnessError):
    """Generic guardrail rejection that does not fit input/output filters."""

    code = "guardrail_violation"


class QualityCheckFailed(HarnessError):
    """outcome_evaluator.QualityCheck rejected the produced artifact."""

    code = "quality_check_failed"


class SkillTimeout(HarnessError):
    """Legacy timeout error name kept for older imports."""

    code = "skill_timeout"


class QualityRejected(QualityCheckFailed):
    """Legacy alias for quality-check rejection."""


class GuardrailBlocked(GuardrailViolation):
    """Legacy alias for guardrail rejection."""
