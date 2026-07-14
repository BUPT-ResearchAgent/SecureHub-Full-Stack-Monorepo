# Status: real

"""Durable Workflow Run control API.

This router is deliberately a thin auth/DTO adapter.  RuntimeEngine and the
PostgreSQL stores own execution, lifecycle, replay and recovery semantics.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from app.db.seeds._constants import agent_id
from app.db.session import get_sessionmaker
from app.deps import CurrentUserDep
from app.runtime.capability_manifest import list_agents, register_agents
from app.runtime.skill_catalog import assert_catalog_integrity, build_production_skill_catalog
from app.schemas.agent_control import (
    AgentManifestItem,
    AgentManifestResponse,
    WorkflowApprovalDecisionRequest,
    WorkflowApprovalResponse,
    WorkflowRunCancelResponse,
    WorkflowRunControlResponse,
    WorkflowRunResponse,
    WorkflowRunStartRequest,
    WorkflowRunStartResponse,
)
from app.services.workflow_application_service import WorkflowApplicationError, WorkflowApplicationService
from app.streaming.agent_events import workflow_event_response
from app.streaming.sse_gateway import WorkflowSSEGateway


router = APIRouter()


def _service(request: Request | None = None) -> WorkflowApplicationService:
    supervisor = getattr(request.app.state, "runtime_supervisor", None) if request is not None else None
    return WorkflowApplicationService(
        get_sessionmaker(),
        wakeup=supervisor.notify if supervisor is not None else None,
        live_notifier=supervisor.notifier if supervisor is not None else None,
    )


def _raise_application_error(exc: WorkflowApplicationError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


def _cursor(after_sequence: int | None, after_event_id: int | None, last_event_id: str | None) -> int:
    values = [value for value in (after_sequence, after_event_id) if value is not None]
    if last_event_id is not None:
        try:
            parsed = int(last_event_id)
        except ValueError as exc:
            raise HTTPException(422, detail={"code": "INVALID_EVENT_CURSOR", "message": "Last-Event-ID must be a non-negative integer"}) from exc
        values.append(parsed)
    if any(value < 0 for value in values):
        raise HTTPException(422, detail={"code": "INVALID_EVENT_CURSOR", "message": "event cursor must be non-negative"})
    if len(set(values)) > 1:
        raise HTTPException(422, detail={"code": "INVALID_EVENT_CURSOR", "message": "event cursors must match when supplied together"})
    return values[0] if values else 0


@router.get("/agents/manifest", response_model=AgentManifestResponse)
async def get_agent_manifest() -> AgentManifestResponse:
    register_agents()
    catalog = build_production_skill_catalog()
    assert_catalog_integrity(catalog)
    agents: list[AgentManifestItem] = []
    for agent in list_agents():
        # BaseAgent.manifest() includes its legacy skill list. The frozen
        # catalog is authoritative, so replace that field before validation
        # instead of passing the keyword twice.
        manifest = dict(agent.manifest())
        manifest["stable_id"] = agent_id(agent.name)
        manifest["skills"] = sorted(
            skill_name for agent_name, skill_name in catalog if agent_name == agent.name
        )
        agents.append(AgentManifestItem.model_validate(manifest))
    return AgentManifestResponse(agents=agents, total=len(agents))


@router.post(
    "/workflow-runs",
    response_model=WorkflowRunStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_workflow_run(
    payload: WorkflowRunStartRequest,
    request: Request,
    current_user_id: CurrentUserDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> WorkflowRunStartResponse:
    # The authenticated identity is the owner; a caller cannot submit another
    # user's UUID merely by changing the DTO field.
    owned_payload = payload.model_copy(update={"user_id": str(current_user_id)})
    try:
        return await _service(request).start(
            owned_payload,
            idempotency_key=idempotency_key,
            actor_user_id=current_user_id,
        )
    except WorkflowApplicationError as exc:
        _raise_application_error(exc)


@router.get("/workflow-runs/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(run_id: UUID, request: Request, current_user_id: CurrentUserDep) -> WorkflowRunResponse:
    try:
        return await _service(request).get(run_id, actor_user_id=current_user_id)
    except WorkflowApplicationError as exc:
        _raise_application_error(exc)


@router.get("/workflow-runs/{run_id}/metrics")
async def get_workflow_run_metrics(run_id: UUID, request: Request, current_user_id: CurrentUserDep) -> dict[str, object]:
    try:
        return await _service(request).metrics(run_id, actor_user_id=current_user_id)
    except WorkflowApplicationError as exc:
        _raise_application_error(exc)


@router.get("/workflow-runs/{run_id}/events")
async def stream_workflow_run_events(
    run_id: UUID,
    request: Request,
    current_user_id: CurrentUserDep,
    after_sequence: int | None = Query(default=None, ge=0),
    after_event_id: int | None = Query(default=None, ge=0),
    until_sequence: int | None = Query(default=None, ge=1),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    cursor = _cursor(after_sequence, after_event_id, last_event_id)
    service = _service(request)
    try:
        # Authorise before returning a long-lived response so ownership does
        # not become a side channel.
        await service.get(run_id, actor_user_id=current_user_id)
    except WorkflowApplicationError as exc:
        _raise_application_error(exc)
    return workflow_event_response(
        WorkflowSSEGateway(service).stream(
            run_id,
            after_sequence=cursor,
            until_sequence=until_sequence,
            actor_user_id=current_user_id,
        )
    )


@router.post("/workflow-runs/{run_id}/cancel", response_model=WorkflowRunCancelResponse)
async def cancel_workflow_run(run_id: UUID, request: Request, current_user_id: CurrentUserDep) -> WorkflowRunCancelResponse:
    try:
        return await _service(request).cancel(run_id, actor_user_id=current_user_id)
    except WorkflowApplicationError as exc:
        _raise_application_error(exc)


@router.post("/workflow-runs/{run_id}/pause", response_model=WorkflowRunControlResponse)
async def pause_workflow_run(run_id: UUID, request: Request, current_user_id: CurrentUserDep) -> WorkflowRunControlResponse:
    try:
        return await _service(request).pause(run_id, actor_user_id=current_user_id)
    except WorkflowApplicationError as exc:
        _raise_application_error(exc)


@router.post("/workflow-runs/{run_id}/resume", response_model=WorkflowRunControlResponse)
async def resume_workflow_run(run_id: UUID, request: Request, current_user_id: CurrentUserDep) -> WorkflowRunControlResponse:
    try:
        return await _service(request).resume(run_id, actor_user_id=current_user_id)
    except WorkflowApplicationError as exc:
        _raise_application_error(exc)


@router.post("/workflow-runs/{run_id}/retry", response_model=WorkflowRunControlResponse)
async def retry_workflow_run(run_id: UUID, request: Request, current_user_id: CurrentUserDep) -> WorkflowRunControlResponse:
    try:
        return await _service(request).retry(run_id, actor_user_id=current_user_id)
    except WorkflowApplicationError as exc:
        _raise_application_error(exc)


@router.post("/workflow-runs/{run_id}/approvals/{approval_id}", response_model=WorkflowApprovalResponse)
async def decide_workflow_approval(
    run_id: UUID,
    approval_id: UUID,
    payload: WorkflowApprovalDecisionRequest,
    request: Request,
    current_user_id: CurrentUserDep,
) -> WorkflowApprovalResponse:
    try:
        return await _service(request).decide_approval(
            run_id,
            approval_id,
            approved=payload.approved,
            decision=payload.decision,
            actor_user_id=current_user_id,
        )
    except WorkflowApplicationError as exc:
        _raise_application_error(exc)


__all__ = ["router"]
