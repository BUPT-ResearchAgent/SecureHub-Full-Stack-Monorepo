# Status: real

"""Canonical runtime Skill execution contracts.

Only these contracts participate in production execution.  Legacy harness
objects and direct ``skill.run()`` adapters were removed in Wave 6.
"""

from app.runtime.harness.contracts import CandidateOutput, SkillDefinition
from app.runtime.harness.errors import (
    AgentRunPersistenceFailed,
)
from app.runtime.harness.context import ExecutionCancelled, ExecutionContext
from app.runtime.harness.executor import SkillExecutionError, SkillExecutor

__all__ = [
    "AgentRunPersistenceFailed",
    "CandidateOutput",
    "ExecutionCancelled",
    "ExecutionContext",
    "SkillDefinition",
    "SkillExecutionError",
    "SkillExecutor",
]
