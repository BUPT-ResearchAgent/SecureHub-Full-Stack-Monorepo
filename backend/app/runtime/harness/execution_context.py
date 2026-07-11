# Status: real

"""Immutable per-step execution identity for the canonical SkillExecutor."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import inspect
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.runtime.contracts import ExecutionMode, ProviderSelection


EmitEvent = Callable[[str, dict[str, Any]], Awaitable[None]]
CancellationCheck = Callable[[], bool | Awaitable[bool]]


async def _noop_emit(_event_type: str, _payload: dict[str, Any]) -> None:
    return None


def _not_cancelled() -> bool:
    return False


@dataclass(frozen=True)
class ExecutionContext:
    workflow_run_id: UUID | str
    step_attempt_id: UUID | str
    agent_run_id: UUID | str
    user_id: UUID | str | None
    mode: ExecutionMode
    provider_selection: ProviderSelection = field(default_factory=ProviderSelection)
    lease_epoch: int = 0
    course_id: UUID | str | None = None
    persona_summary: str = ""
    stream: bool = True
    emit: EmitEvent = _noop_emit
    cancellation_requested: CancellationCheck = _not_cancelled
    extras: dict[str, Any] = field(default_factory=dict)

    async def require_not_cancelled(self) -> None:
        cancelled = self.cancellation_requested()
        if inspect.isawaitable(cancelled):
            cancelled = await cancelled
        if cancelled:
            raise ExecutionCancelled("workflow cancellation requested")


class ExecutionCancelled(RuntimeError):
    code = "RUN_CANCELLED"


__all__ = ["ExecutionCancelled", "ExecutionContext"]
