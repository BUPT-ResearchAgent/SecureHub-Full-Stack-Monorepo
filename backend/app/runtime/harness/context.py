# Status: real

"""Execution context passed to every skill running inside the harness.

The context bundles:
- the active user / workflow identifiers
- the persona summary used as prompt scaffolding
- streaming flag (so skills can yield tokens to SSE)
- a session-scoped agent run logger
- an optional SSE event sink that the workflow layer wires up
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.core.config import Settings, get_settings
from app.runtime.harness.types import EvidenceCard

EventEmitter = Callable[[dict[str, Any]], Awaitable[None]]
RunLogger = Callable[..., Awaitable[None]]


async def _noop_emit(_event: dict[str, Any]) -> None:
    return None


async def _noop_logger(**_kwargs: Any) -> None:
    return None


@dataclass
class HarnessContext:
    """Execution context for a single skill invocation."""

    user_id: str | None = None
    workflow_name: str = "course_learning"
    persona_summary: str = ""
    stream: bool = False
    config: Settings = field(default_factory=get_settings)
    parent_run_id: UUID | str | None = None

    # Side effects pluggable by the workflow / api layer
    emit: EventEmitter = field(default=_noop_emit)
    log_run: RunLogger = field(default=_noop_logger)

    # Per-run accumulators (populated by harness, read by callers)
    last_evidence: list[EvidenceCard] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)

    def child(self, **overrides: Any) -> "HarnessContext":
        """Return a shallow-cloned context with field overrides."""
        return HarnessContext(
            user_id=overrides.get("user_id", self.user_id),
            workflow_name=overrides.get("workflow_name", self.workflow_name),
            persona_summary=overrides.get("persona_summary", self.persona_summary),
            stream=overrides.get("stream", self.stream),
            config=overrides.get("config", self.config),
            parent_run_id=overrides.get("parent_run_id", self.parent_run_id),
            emit=overrides.get("emit", self.emit),
            log_run=overrides.get("log_run", self.log_run),
            last_evidence=overrides.get("last_evidence", []),
            extras=overrides.get("extras", dict(self.extras)),
        )
