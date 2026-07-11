# Status: real

"""Application service for durable WorkflowRun control operations.

HTTP product adapters call this service only for DTO/auth mapping and control.
It creates a durable root but never executes a Skill or owns a process-local
queue; RuntimeWorker claims the root through PostgreSQL.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db.models.workflow_runtime import WorkflowProviderCall, WorkflowRun, WorkflowStepAttempt
from app.runtime.contracts import EventEnvelope, ExecutionMode, RunStatus
from app.runtime.persistence.event_store import EventStore
from app.runtime.persistence.run_store import RunStore
from app.runtime.skill_catalog import build_production_skill_catalog
from app.runtime.state_machine import InvalidStateTransition, SecureHubStateMachine
from app.runtime.workflow_registry import WorkflowRegistry
from app.schemas.agent_control import (
    WorkflowNodeResponse,
    WorkflowRunCancelResponse,
    WorkflowRunControlResponse,
    WorkflowRunResponse,
    WorkflowRunStartRequest,
    WorkflowRunStartResponse,
)


Wakeup = Callable[[UUID], Awaitable[None] | None]


class WorkflowApplicationError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(message)


def build_default_workflow_registry() -> WorkflowRegistry:
    from app.runtime.workflows.product_workflows import PRODUCT_WORKFLOWS
    from app.runtime.workflows.resource_generate_v1 import RESOURCE_GENERATE_V1

    registry = WorkflowRegistry()
    for definition in (RESOURCE_GENERATE_V1, *PRODUCT_WORKFLOWS):
        registry.register(definition)
    return registry


class WorkflowApplicationService:
    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        *,
        workflow_registry: WorkflowRegistry | None = None,
        wakeup: Wakeup | None = None,
        live_notifier: Any | None = None,
        runtime_build_sha: str = "dev",
    ) -> None:
        self.sessionmaker = sessionmaker
        self.workflow_registry = workflow_registry or build_default_workflow_registry()
        self.wakeup = wakeup
        self.live_notifier = live_notifier
        self.runtime_build_sha = runtime_build_sha
        self.skill_catalog = build_production_skill_catalog()

    async def start(
        self,
        request: WorkflowRunStartRequest,
        *,
        idempotency_key: str | None = None,
        actor_user_id: UUID | str | None = None,
    ) -> WorkflowRunStartResponse:
        self._assert_actor(request.user_id, actor_user_id)
        key = self._require_idempotency_key(idempotency_key)
        try:
            definition = self.workflow_registry.get(request.workflow)
        except Exception as exc:
            raise WorkflowApplicationError("INVALID_WORKFLOW", f"unsupported workflow: {request.workflow}", status_code=422) from exc
        input_payload = self._normalise_input(definition.name, request)
        try:
            validated_input = definition.input_model.model_validate(input_payload).model_dump(mode="json")
        except Exception as exc:
            raise WorkflowApplicationError("INVALID_INPUT", "workflow input does not match the frozen definition", status_code=422) from exc

        provider, model = self._provider_selection(request)
        async with self.sessionmaker() as session:
            run_store = RunStore(session)
            # Avoid appending a second queued event for an idempotent replay.
            existing = await self._existing_idempotency(session, request.user_id, definition.name, key)
            created = False
            if existing is None:
                created_result = await run_store.create_run(
                    workflow_name=definition.name,
                    workflow_version=str(definition.version),
                    workflow_definition_digest=definition.definition_digest,
                    catalog_version=definition.catalog_version,
                    provider_policy_version=definition.provider_policy_version,
                    checkpoint_schema_version=definition.checkpoint_schema_version,
                    runtime_build_sha=self.runtime_build_sha,
                    user_id=request.user_id,
                    mode=request.mode,
                    requested_provider=provider,
                    requested_model=model,
                    input_payload=validated_input,
                    idempotency_key=key,
                    return_created=True,
                )
                assert isinstance(created_result, tuple)
                run, created = created_result
            else:
                run = existing
            self._assert_idempotency_request_matches(
                run,
                input_payload=validated_input,
                mode=request.mode,
                provider=provider,
                model=model,
            )
            if created:
                await EventStore(session).append_event(
                    run.id,
                    "progress",
                    {
                        "root_status": "queued",
                        "status": "queued",
                        "workflow": definition.name,
                        "mode": request.mode,
                        "requested_provider": provider,
                        "requested_model": model,
                    },
                )
                await session.commit()
            response = self._start_response(run)
        if created and self.wakeup is not None:
            result = self.wakeup(run.id)
            if hasattr(result, "__await__"):
                await result
        return response

    async def get(self, run_id: UUID | str, *, actor_user_id: UUID | str | None = None) -> WorkflowRunResponse:
        async with self.sessionmaker() as session:
            run = await RunStore(session).get_run(run_id)
            assert run is not None
            self._assert_owner(run, actor_user_id)
            rows = list(
                (
                    await session.execute(
                        select(WorkflowStepAttempt)
                        .where(WorkflowStepAttempt.workflow_run_id == run.id)
                        .order_by(WorkflowStepAttempt.created_at.asc())
                    )
                ).scalars().all()
            )
            actual = await session.scalar(
                select(WorkflowProviderCall)
                .where(WorkflowProviderCall.workflow_run_id == run.id)
                .order_by(WorkflowProviderCall.started_at.desc())
                .limit(1)
            )
            nodes = [self._node_response(row) for row in rows]
            return WorkflowRunResponse(
                run_id=run.id,
                workflow=run.workflow_name,
                workflow_version=run.workflow_version,
                status=run.status,
                mode=run.mode,
                requested_provider=run.requested_provider,
                requested_model=run.requested_model,
                actual_provider=actual.provider if actual else None,
                actual_model=actual.model if actual else None,
                provider=actual.provider if actual else run.requested_provider,
                model=actual.model if actual else run.requested_model,
                created_at=run.created_at,
                started_at=run.started_at,
                finished_at=run.finished_at,
                cancel_requested=run.cancel_requested_at is not None,
                child_runs=nodes,
                nodes=nodes,
                child_run_count=len(nodes),
                final_output=dict(run.output_ref or {}) or None,
                error=dict(run.error or {}) or None,
            )

    async def replay(
        self,
        run_id: UUID | str,
        *,
        after_sequence: int = 0,
        until_sequence: int | None = None,
        actor_user_id: UUID | str | None = None,
    ) -> list[EventEnvelope]:
        if after_sequence < 0:
            raise WorkflowApplicationError("INVALID_EVENT_CURSOR", "event cursor must be non-negative", status_code=422)
        async with self.sessionmaker() as session:
            run = await RunStore(session).get_run(run_id)
            assert run is not None
            self._assert_owner(run, actor_user_id)
            rows = await EventStore(session).replay_events(run.id, after_sequence=after_sequence, limit=10_000)
            envelopes = [await EventStore(session).event_envelope(row) for row in rows]
            if until_sequence is not None:
                envelopes = [event for event in envelopes if event.sequence <= until_sequence]
            return envelopes

    async def cancel(
        self, run_id: UUID | str, *, actor_user_id: UUID | str | None = None
    ) -> WorkflowRunCancelResponse:
        async with self.sessionmaker() as session:
            store = RunStore(session)
            run = await store.get_run(run_id)
            assert run is not None
            self._assert_owner(run, actor_user_id)
            run = await store.request_cancel(run.id)
            await session.commit()
            return WorkflowRunCancelResponse(run_id=run.id, status=run.status, cancel_requested=True)

    async def pause(self, run_id: UUID | str, *, actor_user_id: UUID | str | None = None) -> WorkflowRunControlResponse:
        async with self.sessionmaker() as session:
            store = RunStore(session)
            run = await store.get_run(run_id)
            assert run is not None
            self._assert_owner(run, actor_user_id)
            if run.status == RunStatus.PAUSED:
                return WorkflowRunControlResponse(run_id=run.id, status=run.status, compatibility="compatible")
            try:
                SecureHubStateMachine.assert_run_transition(run.status, RunStatus.PAUSING)
            except InvalidStateTransition as exc:
                raise WorkflowApplicationError("RUN_NOT_ACTIVE", "run cannot be paused in its current state", status_code=409) from exc
            run = await store.transition_run(
                run.id,
                expected_state_version=run.state_version,
                lease_epoch=None,
                status=RunStatus.PAUSING,
                event_type="progress",
                event_payload={"root_status": "pausing", "status": "pausing"},
            )
            await session.commit()
            return WorkflowRunControlResponse(run_id=run.id, status=run.status, compatibility="compatible")

    async def resume(self, run_id: UUID | str, *, actor_user_id: UUID | str | None = None) -> WorkflowRunControlResponse:
        async with self.sessionmaker() as session:
            store = RunStore(session)
            run = await store.get_run(run_id)
            assert run is not None
            self._assert_owner(run, actor_user_id)
            if run.status == RunStatus.WAITING_APPROVAL:
                raise WorkflowApplicationError(
                    "RUN_REQUIRES_RETRY",
                    "provider outcome is unknown; use retry to create an explicit new provider attempt",
                    status_code=409,
                )
            if run.status != RunStatus.PAUSED:
                raise WorkflowApplicationError("RUN_NOT_RESUMABLE", "run is not paused", status_code=409)
            run = await store.transition_run(
                run.id,
                expected_state_version=run.state_version,
                lease_epoch=None,
                status=RunStatus.QUEUED,
                changes={"lease_owner": None, "lease_expires_at": None},
                event_type="progress",
                event_payload={"root_status": "queued", "status": "queued", "resume_requested": True},
            )
            await session.commit()
        if self.wakeup is not None:
            result = self.wakeup(run.id)
            if hasattr(result, "__await__"):
                await result
        return WorkflowRunControlResponse(run_id=run.id, status=run.status, compatibility="compatible")

    async def retry(self, run_id: UUID | str, *, actor_user_id: UUID | str | None = None) -> WorkflowRunControlResponse:
        """Approve exactly one new attempt after an unknown provider outcome.

        The unknown journal rows remain immutable. RuntimeEngine observes this
        durable intent on the re-queued root and creates a later step/provider
        attempt; it never replays the opaque external request in-place.
        """
        async with self.sessionmaker() as session:
            store = RunStore(session)
            run = await store.get_run(run_id)
            assert run is not None
            self._assert_owner(run, actor_user_id)
            if run.status != RunStatus.WAITING_APPROVAL:
                raise WorkflowApplicationError(
                    "RUN_NOT_RETRYABLE",
                    "only a run awaiting provider-outcome approval can be retried",
                    status_code=409,
                )
            unknown_calls = list(
                (
                    await session.execute(
                        select(WorkflowProviderCall)
                        .where(
                            WorkflowProviderCall.workflow_run_id == run.id,
                            WorkflowProviderCall.status == "unknown",
                        )
                        .order_by(WorkflowProviderCall.started_at.asc())
                    )
                ).scalars().all()
            )
            if not unknown_calls:
                raise WorkflowApplicationError(
                    "RUN_NOT_RETRYABLE",
                    "waiting-approval root has no unknown provider call to retry",
                    status_code=409,
                )
            prior_budget = dict(run.budget or {})
            retry_count = int(prior_budget.get("provider_retry_count") or 0) + 1
            retry_intent = {
                "provider_retry_count": retry_count,
                "provider_retry_requested_at": datetime.now(timezone.utc).isoformat(),
                "unknown_provider_call_ids": [str(call.id) for call in unknown_calls],
                "next_provider_attempt": max(int(call.attempt) for call in unknown_calls) + 1,
            }
            run = await store.transition_run(
                run.id,
                expected_state_version=run.state_version,
                lease_epoch=None,
                status=RunStatus.QUEUED,
                changes={
                    "budget": {**prior_budget, **retry_intent},
                    "error": {},
                    "lease_owner": None,
                    "lease_expires_at": None,
                },
                event_type="progress",
                event_payload={
                    "root_status": "queued",
                    "status": "queued",
                    "provider_retry_requested": True,
                    "retry_attempt": retry_count,
                    "unknown_provider_call_ids": retry_intent["unknown_provider_call_ids"],
                },
            )
            await session.commit()
        if self.wakeup is not None:
            result = self.wakeup(run.id)
            if hasattr(result, "__await__"):
                await result
        return WorkflowRunControlResponse(run_id=run.id, status=run.status, compatibility="compatible")

    @staticmethod
    def _normalise_input(workflow_name: str, request: WorkflowRunStartRequest) -> dict[str, Any]:
        payload = dict(request.input)
        payload.setdefault("user_id", request.user_id)
        if request.course_id is not None:
            payload.setdefault("course_id", request.course_id)
        if workflow_name == "profile_build_v1":
            if "history" in payload and "dialogue_turns" not in payload:
                payload["dialogue_turns"] = payload.pop("history")
            payload.setdefault("message", "Build a learning persona")
        elif workflow_name == "course_plan_v1":
            payload.setdefault("query", "Generate a personalised learning path")
        elif workflow_name == "resource_generate_v1":
            resource_type = payload.setdefault("resource_type", "doc")
            payload.setdefault("query", f"Generate {resource_type} resource")
        elif workflow_name == "tutor_routing_v1":
            payload.setdefault("question", payload.get("query", "Tutor question"))
        elif workflow_name == "assessment_update_v1":
            payload.setdefault("answers", [])
        return payload

    @staticmethod
    def _provider_selection(request: WorkflowRunStartRequest) -> tuple[str | None, str | None]:
        if request.mode == ExecutionMode.FIXTURE:
            return "fixture", request.model or "fixture-v1"
        settings = get_settings()
        if not settings.AGENT_RUN_REAL_ENABLED:
            raise WorkflowApplicationError(
                "REAL_MODE_DISABLED",
                "real workflow execution is disabled by server policy",
                status_code=503,
            )
        provider = request.provider or settings.LLM_PROVIDER
        if provider == "fixture":
            raise WorkflowApplicationError("INVALID_PROVIDER", "real mode cannot select fixture", status_code=422)
        model = request.model
        if model is None:
            model = settings.DEEPSEEK_MODEL if provider == "deepseek" else settings.XFYUN_MODEL if provider == "xfyun" else None
        return provider, model

    @staticmethod
    async def _existing_idempotency(
        session: AsyncSession, user_id: str, workflow_name: str, key: str | None
    ) -> WorkflowRun | None:
        if not key:
            return None
        try:
            parsed = UUID(str(user_id))
        except (TypeError, ValueError):
            return None
        return await session.scalar(
            select(WorkflowRun).where(
                WorkflowRun.user_id == parsed,
                WorkflowRun.workflow_name == workflow_name,
                WorkflowRun.idempotency_key == key,
            )
        )

    @staticmethod
    def _node_response(row: WorkflowStepAttempt) -> WorkflowNodeResponse:
        return WorkflowNodeResponse(
            node_id=row.node_id,
            status=row.status,
            agent_name=row.agent_name,
            skill_name=row.skill_name,
            step_attempt_id=row.id,
            agent_run_id=row.agent_run_id,
            attempt=row.attempt,
            started_at=row.started_at,
            finished_at=row.finished_at,
            duration_ms=row.duration_ms,
            quality_score=row.quality_score,
            error_code=row.error_code,
        )

    @staticmethod
    def _start_response(run: WorkflowRun) -> WorkflowRunStartResponse:
        return WorkflowRunStartResponse(
            run_id=run.id,
            workflow=run.workflow_name,
            status=run.status,
            events_url=f"/api/v1/workflow-runs/{run.id}/events",
            cancel_url=f"/api/v1/workflow-runs/{run.id}/cancel",
            mode=run.mode,
            requested_provider=run.requested_provider,
            requested_model=run.requested_model,
            provider=run.requested_provider,
            model=run.requested_model,
        )

    @staticmethod
    def _assert_actor(request_user_id: str, actor_user_id: UUID | str | None) -> None:
        if actor_user_id is not None and str(actor_user_id) != str(request_user_id):
            raise WorkflowApplicationError("RUN_FORBIDDEN", "actor cannot create a run for another user", status_code=403)

    @staticmethod
    def _require_idempotency_key(idempotency_key: str | None) -> str:
        key = str(idempotency_key or "").strip()
        if not key:
            raise WorkflowApplicationError(
                "IDEMPOTENCY_KEY_REQUIRED",
                "Idempotency-Key is required when starting a workflow run",
                status_code=422,
            )
        if len(key) > 128:
            raise WorkflowApplicationError(
                "IDEMPOTENCY_KEY_INVALID",
                "Idempotency-Key exceeds 128 characters",
                status_code=422,
            )
        return key

    @staticmethod
    def _assert_idempotency_request_matches(
        run: WorkflowRun,
        *,
        input_payload: dict[str, Any],
        mode: ExecutionMode | str,
        provider: str | None,
        model: str | None,
    ) -> None:
        if (
            dict(run.input_payload or {}) != input_payload
            or str(run.mode) != str(mode)
            or run.requested_provider != provider
            or run.requested_model != model
        ):
            raise WorkflowApplicationError(
                "IDEMPOTENCY_KEY_REUSED",
                "Idempotency-Key is already bound to a different workflow request",
                status_code=409,
            )

    @staticmethod
    def _assert_owner(run: WorkflowRun, actor_user_id: UUID | str | None) -> None:
        if actor_user_id is not None and str(run.user_id) != str(actor_user_id):
            # Do not disclose whether an unowned root exists.
            raise WorkflowApplicationError("RUN_NOT_FOUND", "workflow run not found", status_code=404)


__all__ = ["WorkflowApplicationError", "WorkflowApplicationService", "build_default_workflow_registry"]
