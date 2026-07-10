# Status: partial-real

"""HTTP controls for a fixed multi-agent workflow run.

This router controls workflow instances only.  It never creates, removes, or
renames the fixed nine SecureHub business agents.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.schemas.agent_control import (
    AgentManifestResponse,
    WorkflowRunCancelResponse,
    WorkflowRunResponse,
    WorkflowRunStartRequest,
    WorkflowRunStartResponse,
)
from app.services.agent_control_service import AgentControlService, WorkflowControlError
from app.streaming.agent_events import agent_event_response


router = APIRouter()
_service = AgentControlService()


def _raise_control_error(exc: WorkflowControlError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    ) from exc


@router.get("/agents/manifest", response_model=AgentManifestResponse)
async def get_agent_manifest() -> AgentManifestResponse:
    try:
        return await _service.manifest()
    except WorkflowControlError as exc:
        _raise_control_error(exc)


@router.post(
    "/workflow-runs",
    response_model=WorkflowRunStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_workflow_run(payload: WorkflowRunStartRequest) -> WorkflowRunStartResponse:
    try:
        return await _service.start(payload)
    except WorkflowControlError as exc:
        _raise_control_error(exc)


@router.get("/workflow-runs/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(run_id: UUID) -> WorkflowRunResponse:
    try:
        return await _service.get(run_id)
    except WorkflowControlError as exc:
        _raise_control_error(exc)


@router.get("/workflow-runs/{run_id}/events")
async def stream_workflow_run_events(run_id: UUID) -> StreamingResponse:
    try:
        events = await _service.events(run_id)
    except WorkflowControlError as exc:
        _raise_control_error(exc)
    return agent_event_response(events)


@router.post(
    "/workflow-runs/{run_id}/cancel",
    response_model=WorkflowRunCancelResponse,
)
async def cancel_workflow_run(run_id: UUID) -> WorkflowRunCancelResponse:
    try:
        return await _service.cancel(run_id)
    except WorkflowControlError as exc:
        _raise_control_error(exc)


__all__ = ["router"]
