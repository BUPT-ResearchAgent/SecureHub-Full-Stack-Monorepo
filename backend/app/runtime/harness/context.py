# Status: real

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class HarnessConfig:
    min_evidence: int = 3
    mock_mode: bool = False
    llm_provider: str = "xfyun"


@dataclass(slots=True)
class HarnessContext:
    user_id: str | None = None
    course_id: str | None = None
    persona_summary: str = ""
    stream: bool = False
    sse_writer: Callable[[str, dict[str, Any] | list[dict[str, Any]]], Awaitable[None]] | None = None
    config: HarnessConfig = field(default_factory=HarnessConfig)
    parent_run_id: str | None = None
    evidence_chunk_ids: list[str] = field(default_factory=list)
    logged_runs: list[dict[str, Any]] = field(default_factory=list)
    llm: Any = None
    quality_checker: Any = None
    storage_service: Any = None

    async def log_run(self, **kwargs: Any) -> str:
        run_id = str(kwargs.get("run_id") or uuid4())
        payload = {"id": run_id, **kwargs}
        if self.config.mock_mode:
            print(f"[harness.log_run] {payload}")
        self.logged_runs.append(payload)
        return run_id

    async def emit(self, event: str, data: dict[str, Any] | list[dict[str, Any]]) -> None:
        if self.sse_writer is not None:
            await self.sse_writer(event, data)
