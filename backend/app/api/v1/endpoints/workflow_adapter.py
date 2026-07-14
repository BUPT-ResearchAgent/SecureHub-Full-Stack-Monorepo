# Status: real

"""Thin compatibility helpers for product endpoints backed by durable roots.

Product routes are deliberately limited to authentication, DTO mapping and
response compatibility. They never execute a Skill, create a task queue, or
invent a second public run identifier.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from typing import Any, NoReturn
from uuid import UUID

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.db.session import get_sessionmaker
from app.schemas.agent_control import (
    WorkflowRunResponse,
    WorkflowRunStartRequest,
    WorkflowRunStartResponse,
)
from app.services.workflow_application_service import (
    WorkflowApplicationError,
    WorkflowApplicationService,
)
from app.streaming.agent_events import workflow_event_response
from app.streaming.sse_gateway import WorkflowSSEGateway


# Existing synchronous product DTOs can wait briefly for a fast local result,
# but must return the durable root instead of reporting queued work as success.
SYNC_COMPAT_WAIT_SECONDS = 0.25
_TERMINAL_STATUSES = frozenset({"succeeded", "failed", "blocked", "cancelled"})


def workflow_service(request: Request) -> WorkflowApplicationService:
    supervisor = getattr(request.app.state, "runtime_supervisor", None)
    return WorkflowApplicationService(
        get_sessionmaker(),
        wakeup=supervisor.notify if supervisor is not None else None,
        live_notifier=supervisor.notifier if supervisor is not None else None,
    )


async def start_product_workflow(
    service: WorkflowApplicationService,
    *,
    workflow: str,
    actor_user_id: UUID | str,
    input_payload: Mapping[str, Any],
    course_id: UUID | str | None = None,
    mode: str = "real",
    provider: str | None = None,
    model: str | None = None,
    idempotency_key: str | None = None,
) -> WorkflowRunStartResponse:
    """Create exactly one durable root through the shared application service."""
    request = WorkflowRunStartRequest(
        workflow=workflow,
        user_id=str(actor_user_id),
        course_id=str(course_id) if course_id is not None else None,
        input=dict(input_payload),
        mode=mode,
        provider=provider,
        model=model,
        stream=True,
    )
    try:
        return await service.start(
            request,
            idempotency_key=idempotency_key,
            actor_user_id=actor_user_id,
        )
    except WorkflowApplicationError as exc:
        raise_application_error(exc)
    except Exception as exc:  # PostgreSQL/root persistence remains mandatory.
        raise HTTPException(
            status_code=503,
            detail={"code": "INTERNAL", "message": "workflow runtime is temporarily unavailable"},
        ) from exc


def root_location(start: WorkflowRunStartResponse) -> str:
    return f"/api/v1/workflow-runs/{start.run_id}"


def attach_root_headers(
    response: StreamingResponse | JSONResponse,
    start: WorkflowRunStartResponse,
) -> StreamingResponse | JSONResponse:
    response.headers["X-Workflow-Run-ID"] = str(start.run_id)
    response.headers["X-Workflow-Events-URL"] = start.events_url
    response.headers["Location"] = root_location(start)
    return response


def durable_sse_response(
    service: WorkflowApplicationService,
    start: WorkflowRunStartResponse,
    *,
    actor_user_id: UUID | str,
) -> StreamingResponse:
    """Expose one PostgreSQL-backed event stream for a committed root."""
    response = workflow_event_response(
        WorkflowSSEGateway(service).stream(
            start.run_id,
            actor_user_id=actor_user_id,
        )
    )
    return attach_root_headers(response, start)  # type: ignore[return-value]


def accepted_root_response(start: WorkflowRunStartResponse) -> JSONResponse:
    """Return the frozen 202 compatibility shape for unfinished sync calls."""
    response = JSONResponse(status_code=202, content=start.model_dump(mode="json"))
    return attach_root_headers(response, start)  # type: ignore[return-value]


def completed_root_response(start: WorkflowRunStartResponse, content: Mapping[str, Any]) -> JSONResponse:
    """Return a synchronous compatibility DTO without losing its durable root.

    A product adapter may observe a very fast terminal run before its short
    compatibility wait expires.  That does not make the root disposable: the
    caller still needs the same status/events URLs for refresh and replay.
    """
    response = JSONResponse(status_code=200, content=dict(content))
    return attach_root_headers(response, start)  # type: ignore[return-value]


async def wait_for_terminal(
    service: WorkflowApplicationService,
    run_id: UUID | str,
    *,
    actor_user_id: UUID | str,
    timeout_seconds: float = SYNC_COMPAT_WAIT_SECONDS,
) -> WorkflowRunResponse | None:
    """Observe durable state only; this helper never launches execution itself."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            result = await service.get(run_id, actor_user_id=actor_user_id)
        except WorkflowApplicationError as exc:
            raise_application_error(exc)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail={"code": "INTERNAL", "message": "workflow runtime is temporarily unavailable"},
            ) from exc
        if result.status in _TERMINAL_STATUSES:
            return result
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        await asyncio.sleep(min(0.025, remaining))


def require_successful_terminal(result: WorkflowRunResponse) -> dict[str, Any]:
    """Return a completed output or surface the runtime's sanitised failure."""
    if result.status != "succeeded":
        error = dict(result.error or {})
        code = str(error.get("code") or result.status.upper())
        message = str(error.get("message") or f"workflow run finished as {result.status}")
        status_code = 409 if result.status == "cancelled" else _status_for_error(code)
        raise HTTPException(status_code=status_code, detail={"code": code, "message": message})

    final = result.final_output
    if not isinstance(final, dict):
        raise HTTPException(
            status_code=500,
            detail={"code": "WORKFLOW_OUTPUT_INVALID", "message": "successful workflow has no persisted output"},
        )
    output = final.get("output", final)
    if not isinstance(output, dict):
        raise HTTPException(
            status_code=500,
            detail={"code": "WORKFLOW_OUTPUT_INVALID", "message": "workflow output is not an object"},
        )
    return output


def raise_application_error(exc: WorkflowApplicationError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


def _status_for_error(code: str) -> int:
    if code in {"INVALID_INPUT", "INSUFFICIENT_EVIDENCE", "STRICT_PARSE_FAILED", "QUALITY_REJECTED"}:
        return 422
    if code in {"PROVIDER_UNAVAILABLE", "AGENT_RUN_PERSIST_FAILED", "ARTIFACT_PERSIST_FAILED"}:
        return 503
    if code == "PROVIDER_UNKNOWN_OUTCOME":
        return 409
    return 500


__all__ = [
    "SYNC_COMPAT_WAIT_SECONDS",
    "accepted_root_response",
    "completed_root_response",
    "durable_sse_response",
    "require_successful_terminal",
    "start_product_workflow",
    "wait_for_terminal",
    "workflow_service",
]
