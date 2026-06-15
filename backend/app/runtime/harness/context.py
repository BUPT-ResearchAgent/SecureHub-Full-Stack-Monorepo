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
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.config import Settings, get_settings
from app.runtime.harness.types import EvidenceCard

EventEmitter = Callable[[dict[str, Any]], Awaitable[None]]
LegacySseWriter = Callable[[str, object], Awaitable[None]]
RunLogger = Callable[..., Awaitable[None]]


@dataclass
class HarnessConfig:
    """Compatibility config used by the older BaseSkill harness tests."""

    min_evidence: int = 3
    mock_mode: bool = False
    llm_provider: str = "xfyun"
    RETRIEVAL_TOP_K: int = 8
    RERANK_TOP_K: int = 5

    @property
    def MIN_EVIDENCE(self) -> int:
        return self.min_evidence


async def _noop_emit(_event: dict[str, Any]) -> None:
    return None


async def _noop_logger(**_kwargs: Any) -> None:
    return None


class HarnessContext:
    """Execution context for a single skill invocation.

    The PR 24 harness emits dict-shaped events, while the existing dev tests use
    the older ``emit(event, data)`` convention. This context accepts both forms
    so the merged runtime can keep both APIs alive during the migration.
    """

    def __init__(
        self,
        user_id: str | None = None,
        workflow_name: str = "course_learning",
        persona_summary: str = "",
        stream: bool = False,
        config: Settings | HarnessConfig | None = None,
        parent_run_id: UUID | str | None = None,
        *,
        emit: EventEmitter | None = None,
        log_run: RunLogger | None = None,
        sse_writer: LegacySseWriter | None = None,
        course_id: str | None = None,
        last_evidence: list[EvidenceCard] | None = None,
        evidence_chunk_ids: list[str] | None = None,
        logged_runs: list[dict[str, Any]] | None = None,
        extras: dict[str, Any] | None = None,
        llm: Any | None = None,
        quality_checker: Any | None = None,
        storage_service: Any | None = None,
    ) -> None:
        self.user_id = user_id
        self.workflow_name = workflow_name
        self.persona_summary = persona_summary
        self.stream = stream
        self.config = config or get_settings()
        self.parent_run_id = parent_run_id
        self.course_id = course_id
        self.sse_writer = sse_writer
        self._event_sink = emit or _noop_emit
        self._run_logger = log_run or _noop_logger

        self.last_evidence = list(last_evidence or [])
        self.evidence_chunk_ids = list(evidence_chunk_ids or [])
        self.logged_runs = logged_runs if logged_runs is not None else []
        self.extras = dict(extras or {})
        self.llm = llm
        self.quality_checker = quality_checker
        self.storage_service = storage_service

    async def emit(self, *args: Any) -> None:
        """Emit either a dict event or the legacy ``(event, data)`` pair."""
        if len(args) == 1 and isinstance(args[0], dict):
            payload = dict(args[0])
            event_name = str(payload.get("event", "message"))
            await self._event_sink(payload)
            if self.sse_writer is not None:
                await self.sse_writer(event_name, payload)
            return

        if len(args) == 2:
            event_name = str(args[0])
            data = args[1]
            payload = data if isinstance(data, dict) else {"data": data}
            await self._event_sink({"event": event_name, **payload})
            if self.sse_writer is not None:
                await self.sse_writer(event_name, data)
            return

        raise TypeError("HarnessContext.emit expects event dict or (event, data)")

    async def log_run(self, **kwargs: Any) -> None:
        self.logged_runs.append(dict(kwargs))
        await self._run_logger(**kwargs)

    def child(self, **overrides: Any) -> "HarnessContext":
        """Return a shallow-cloned context with field overrides."""
        return HarnessContext(
            user_id=overrides.get("user_id", self.user_id),
            workflow_name=overrides.get("workflow_name", self.workflow_name),
            persona_summary=overrides.get("persona_summary", self.persona_summary),
            stream=overrides.get("stream", self.stream),
            config=overrides.get("config", self.config),
            parent_run_id=overrides.get("parent_run_id", self.parent_run_id),
            emit=overrides.get("emit", self._event_sink),
            log_run=overrides.get("log_run", self._run_logger),
            sse_writer=overrides.get("sse_writer", self.sse_writer),
            course_id=overrides.get("course_id", self.course_id),
            last_evidence=overrides.get("last_evidence", []),
            evidence_chunk_ids=overrides.get("evidence_chunk_ids", self.evidence_chunk_ids),
            logged_runs=overrides.get("logged_runs", self.logged_runs),
            extras=overrides.get("extras", dict(self.extras)),
            llm=overrides.get("llm", self.llm),
            quality_checker=overrides.get("quality_checker", self.quality_checker),
            storage_service=overrides.get("storage_service", self.storage_service),
        )
