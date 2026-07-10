# Status: partial-real

"""Application service for the fixed workflow Run API."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.runtime.capability_manifest import list_agents, register_agents
from app.runtime.harness.live_adapters import (
    StrictProviderUnavailable,
    get_strict_deepseek_provider,
)
from app.runtime.run_registry import (
    GLOBAL_RUN_REGISTRY,
    RunRegistry,
    WorkflowRunNotActive,
    WorkflowRunNotFound,
)
from app.runtime.workflows.course_learning_minimal import (
    FIXTURE_MODEL,
    FIXTURE_PROVIDER,
    WORKFLOW_NAME,
    run_course_learning_minimal,
    workflow_nodes,
)
from app.schemas.agent_control import (
    AgentManifestItem,
    AgentManifestResponse,
    WorkflowRunCancelResponse,
    WorkflowRunResponse,
    WorkflowRunStartRequest,
    WorkflowRunStartResponse,
)
from app.services.agent.agent_run_service import (
    AgentRunInvalidUserId,
    AgentRunPrerequisitesUnavailable,
    AgentRunService,
)


@dataclass
class WorkflowControlError(RuntimeError):
    code: str
    message: str
    status_code: int


class AgentControlService:
    """Thin orchestration layer over the process-local RunRegistry."""

    def __init__(
        self,
        registry: RunRegistry | None = None,
        *,
        sessionmaker: Any | None = None,
    ) -> None:
        self.registry = registry or GLOBAL_RUN_REGISTRY
        self._sessionmaker = sessionmaker
        self._real_start_lock = asyncio.Lock()

    async def manifest(self) -> AgentManifestResponse:
        register_agents()
        agents = [AgentManifestItem.model_validate(agent.manifest()) for agent in list_agents()]
        if len(agents) != 9:
            raise WorkflowControlError(
                code="AGENT_MANIFEST_INVALID",
                message="SecureHub must expose exactly nine fixed agents",
                status_code=500,
            )
        return AgentManifestResponse(agents=agents, total=len(agents))

    async def start(self, request: WorkflowRunStartRequest) -> WorkflowRunStartResponse:
        if request.workflow != WORKFLOW_NAME:
            raise WorkflowControlError(
                code="INVALID_WORKFLOW",
                message=f"unsupported workflow: {request.workflow}",
                status_code=422,
            )
        if request.mode == "fixture":
            record = await self.registry.create(
                workflow=WORKFLOW_NAME,
                user_id=request.user_id,
                mode="fixture",
                provider=FIXTURE_PROVIDER,
                model=FIXTURE_MODEL,
                input_payload=request.model_dump(mode="json"),
                nodes=workflow_nodes(),
            )
            return await self._launch(record.run_id)
        return await self._start_real(request)

    async def _start_real(self, request: WorkflowRunStartRequest) -> WorkflowRunStartResponse:
        if request.provider != "deepseek":
            raise WorkflowControlError(
                code="INVALID_PROVIDER",
                message="Agent-Run-2 real mode requires provider=deepseek",
                status_code=422,
            )

        try:
            user_id = AgentRunService.normalize_user_id(request.user_id)
        except AgentRunInvalidUserId as exc:
            raise WorkflowControlError(
                code="INVALID_USER_ID",
                message="user_id must be a UUID for real workflow execution",
                status_code=422,
            ) from exc

        settings = get_settings()
        if not settings.AGENT_RUN_REAL_ENABLED:
            raise WorkflowControlError(
                code="REAL_MODE_DISABLED",
                message="server-side AGENT_RUN_REAL_ENABLED is false",
                status_code=503,
            )

        await self._validate_real_prerequisites(user_id)

        try:
            provider = get_strict_deepseek_provider()
        except StrictProviderUnavailable as exc:
            raise WorkflowControlError(
                code="PROVIDER_UNAVAILABLE",
                message=str(exc),
                status_code=503,
            ) from exc

        async with self._real_start_lock:
            active_count = await self.registry.active_count(mode="real")
            if active_count >= settings.AGENT_RUN_REAL_MAX_CONCURRENCY:
                raise WorkflowControlError(
                    code="REAL_CONCURRENCY_LIMIT",
                    message="real workflow concurrency limit reached",
                    status_code=429,
                )
            record = await self.registry.create(
                workflow=WORKFLOW_NAME,
                user_id=str(user_id),
                mode="real",
                provider="deepseek",
                model=provider.model_name,
                input_payload=request.model_dump(mode="json"),
                nodes=workflow_nodes(),
            )
        return await self._launch(record.run_id)

    async def _validate_real_prerequisites(self, user_id: UUID) -> None:
        try:
            sessionmaker = self._sessionmaker or get_sessionmaker()
            async with sessionmaker() as session:
                service = AgentRunService(session)
                await service.ensure_real_workflow_prerequisites(
                    user_id=user_id,
                    nodes=workflow_nodes(),
                )
        except AgentRunInvalidUserId as exc:
            raise WorkflowControlError(
                code="INVALID_USER_ID",
                message="user_id must be a UUID for real workflow execution",
                status_code=422,
            ) from exc
        except AgentRunPrerequisitesUnavailable as exc:
            raise WorkflowControlError(
                code="REAL_PREREQUISITES_UNAVAILABLE",
                message="real workflow database prerequisites are unavailable",
                status_code=503,
            ) from exc
        except Exception as exc:
            raise WorkflowControlError(
                code="REAL_PREREQUISITES_UNAVAILABLE",
                message="real workflow database prerequisites are unavailable",
                status_code=503,
            ) from exc

    async def _launch(self, run_id: UUID) -> WorkflowRunStartResponse:
        record = await self.registry.get(run_id)
        task = asyncio.create_task(
            run_course_learning_minimal(record.run_id, self.registry),
            name=f"securehub-workflow-{record.run_id}",
        )
        await self.registry.attach_task(record.run_id, task)
        return WorkflowRunStartResponse(
            run_id=record.run_id,
            workflow=record.workflow,
            status=record.status,
            events_url=f"/api/v1/workflow-runs/{record.run_id}/events",
            cancel_url=f"/api/v1/workflow-runs/{record.run_id}/cancel",
            mode=record.mode,
            provider=record.provider,
            model=record.model,
        )

    async def get(self, run_id: UUID) -> WorkflowRunResponse:
        try:
            return WorkflowRunResponse.model_validate(await self.registry.snapshot(run_id))
        except WorkflowRunNotFound as exc:
            raise WorkflowControlError(
                code="RUN_NOT_FOUND",
                message=f"workflow run not found: {run_id}",
                status_code=404,
            ) from exc

    async def events(
        self,
        run_id: UUID,
        *,
        after_event_id: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        try:
            await self.registry.get(run_id)
        except WorkflowRunNotFound as exc:
            raise WorkflowControlError(
                code="RUN_NOT_FOUND",
                message=f"workflow run not found: {run_id}",
                status_code=404,
            ) from exc
        return self.registry.iter_events(run_id, after_event_id=after_event_id)

    async def cancel(self, run_id: UUID) -> WorkflowRunCancelResponse:
        try:
            record = await self.registry.request_cancel(run_id)
        except WorkflowRunNotFound as exc:
            raise WorkflowControlError(
                code="RUN_NOT_FOUND",
                message=f"workflow run not found: {run_id}",
                status_code=404,
            ) from exc
        except WorkflowRunNotActive as exc:
            raise WorkflowControlError(
                code="RUN_NOT_ACTIVE",
                message=f"workflow run is already terminal: {exc}",
                status_code=409,
            ) from exc
        return WorkflowRunCancelResponse(run_id=record.run_id, status=record.status)
