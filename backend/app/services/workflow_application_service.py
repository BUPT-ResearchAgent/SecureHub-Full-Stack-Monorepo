# Status: real

"""Application service for durable WorkflowRun control operations.

HTTP product adapters call this service only for DTO/auth mapping and control.
It creates a durable root but never executes a Skill or owns a process-local
queue; RuntimeWorker claims the root through PostgreSQL.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db.models.workflow_runtime import WorkflowApproval, WorkflowProviderCall, WorkflowRun, WorkflowStepAttempt
from app.repositories.identity.provider_credentials import ProviderCredentialRepository
from app.runtime.contracts import EventEnvelope, ExecutionMode, RunStatus, RuntimeSemanticVersion
from app.runtime.persistence.approval_store import ApprovalNotFoundError, ApprovalStore
from app.runtime.persistence.checkpoint_store import CheckpointStore
from app.runtime.persistence.event_store import EventStore
from app.runtime.persistence.run_store import RunStore
from app.runtime.observability import RuntimeMetricsService
from app.runtime.skill_catalog import build_production_skill_catalog
from app.runtime.state_machine import InvalidStateTransition, SecureHubStateMachine
from app.runtime.versioning.compatibility import CompatibilityPolicy
from app.runtime.versioning.compatibility import CompatibilityDecision
from app.runtime.versioning.checkpoint_migrations import (
    CheckpointMigrationRegistry,
    build_runtime_checkpoint_migrations,
)
from app.runtime.workflow_registry import WorkflowRegistry
from app.schemas.agent_control import (
    WorkflowNodeResponse,
    WorkflowRunCancelResponse,
    WorkflowApprovalResponse,
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
    from app.runtime.workflows.course_learning_full_v1 import COURSE_LEARNING_FULL_V1
    from app.runtime.workflows.course_learning_full_v2 import COURSE_LEARNING_FULL_V2
    from app.runtime.workflows.fund_recommendation_v1 import FUND_RECOMMENDATION_V1
    from app.runtime.workflows.product_workflows import PRODUCT_WORKFLOWS
    from app.runtime.workflows.resource_generate_v1 import RESOURCE_GENERATE_V1
    from app.runtime.workflows.tutor_routing_v2 import TUTOR_ROUTING_V2
    from app.runtime.workflows.tutor_routing_v3 import TUTOR_ROUTING_V3

    registry = WorkflowRegistry()
    for definition in (
        RESOURCE_GENERATE_V1,
        COURSE_LEARNING_FULL_V1,
        COURSE_LEARNING_FULL_V2,
        TUTOR_ROUTING_V2,
        TUTOR_ROUTING_V3,
        FUND_RECOMMENDATION_V1,
        *PRODUCT_WORKFLOWS,
    ):
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
        checkpoint_migrations: CheckpointMigrationRegistry | None = None,
    ) -> None:
        self.sessionmaker = sessionmaker
        self.workflow_registry = workflow_registry or build_default_workflow_registry()
        self.wakeup = wakeup
        self.live_notifier = live_notifier
        self.runtime_build_sha = runtime_build_sha
        self.skill_catalog = build_production_skill_catalog()
        self.checkpoint_migrations = checkpoint_migrations or build_runtime_checkpoint_migrations()
        self.compatibility_policy = CompatibilityPolicy(self.checkpoint_migrations)

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
            credential_id = None
            if request.mode == ExecutionMode.REAL and provider in {"deepseek", "xfyun"}:
                # Resolve the active key once while the root is created. The
                # worker receives only its opaque ID and will never consult a
                # later active-key selection for this root.
                active_credential = await ProviderCredentialRepository(session).get_active(
                    UUID(str(request.user_id)), provider
                )
                credential_id = active_credential.id if active_credential is not None else None
            if definition.name == "tutor_routing_v3":
                validated_input["persona_summary"] = await self._tutor_persona_summary(session, request.user_id)
            if definition.name == "assessment_update_v2":
                await self._validate_assessment_quiz_artifact(
                    session,
                    user_id=request.user_id,
                    course_id=validated_input.get("course_id"),
                    quiz_artifact_id=validated_input.get("quiz_artifact_id"),
                    mode=request.mode,
                )
                capability_dimensions, persona_dimension_keys = await self._assessment_feedback_constraints(
                    session, request.user_id
                )
                # These are server-owned constraints, not caller-controlled DTO
                # fields. They make the mutation target explicit to the two
                # generative Skills before the final atomic action validates it.
                validated_input["capability_dimensions"] = capability_dimensions
                validated_input["persona_dimension_keys"] = persona_dimension_keys
            if definition.name == "fund_recommendation_v1":
                # A generic workflow start must not provide a second, caller-
                # controlled profile snapshot. Rehydrate it from the same
                # durable sources used by the authenticated product adapter.
                validated_input.update(await self._hydrate_fund_profile(session, request.user_id, validated_input))
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
                    credential_id=credential_id,
                    input_payload=validated_input,
                    budget=self._initial_budget(request.budget, mode=request.mode),
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
                credential_id=credential_id,
                budget=dict(request.budget or {}),
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

    async def metrics(self, run_id: UUID | str, *, actor_user_id: UUID | str | None = None) -> dict[str, Any]:
        async with self.sessionmaker() as session:
            run = await RunStore(session).get_run(run_id)
            assert run is not None
            self._assert_owner(run, actor_user_id)
            return await RuntimeMetricsService(session).snapshot(workflow_run_id=run.id)

    async def cancel(
        self, run_id: UUID | str, *, actor_user_id: UUID | str | None = None
    ) -> WorkflowRunCancelResponse:
        async with self.sessionmaker() as session:
            store = RunStore(session)
            run = await store.get_run(run_id)
            assert run is not None
            self._assert_owner(run, actor_user_id)
            run = await store.request_cancel(run.id)
            await ApprovalStore(session).audit(run.id, action="cancel_requested", actor_id=actor_user_id)
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
            await ApprovalStore(session).audit(run.id, action="pause_requested", actor_id=actor_user_id)
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
            compatibility = await self._resume_compatibility(session, run)
            if compatibility.status == "incompatible":
                raise WorkflowApplicationError(
                    "SEMANTIC_VERSION_INCOMPATIBLE",
                    "run checkpoint is incompatible with the current runtime definition",
                    status_code=409,
                )
            run = await store.transition_run(
                run.id,
                expected_state_version=run.state_version,
                lease_epoch=None,
                status=RunStatus.QUEUED,
                changes={"lease_owner": None, "lease_expires_at": None},
                event_type="progress",
                event_payload={"root_status": "queued", "status": "queued", "resume_requested": True},
            )
            await ApprovalStore(session).audit(
                run.id,
                action="resume_requested",
                actor_id=actor_user_id,
                details={"compatibility": compatibility.status},
            )
            await session.commit()
        if self.wakeup is not None:
            result = self.wakeup(run.id)
            if hasattr(result, "__await__"):
                await result
        return WorkflowRunControlResponse(run_id=run.id, status=run.status, compatibility=compatibility.status)

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
            await ApprovalStore(session).audit(run.id, action="provider_retry_requested", actor_id=actor_user_id)
            await session.commit()
        if self.wakeup is not None:
            result = self.wakeup(run.id)
            if hasattr(result, "__await__"):
                await result
        return WorkflowRunControlResponse(run_id=run.id, status=run.status, compatibility="compatible")

    async def decide_approval(
        self,
        run_id: UUID | str,
        approval_id: UUID | str,
        *,
        approved: bool,
        decision: dict[str, Any] | None = None,
        actor_user_id: UUID | str | None = None,
    ) -> WorkflowApprovalResponse:
        async with self.sessionmaker() as session:
            store = RunStore(session)
            run = await store.get_run(run_id)
            assert run is not None
            self._assert_owner(run, actor_user_id)
            approvals = ApprovalStore(session)
            try:
                # Verify the URL root before mutating the approval. Otherwise
                # a valid owner of one run could consume a pending approval
                # belonging to another root and then receive a misleading 404.
                existing = await approvals.get(approval_id)
                if existing.workflow_run_id != run.id:
                    raise WorkflowApplicationError("APPROVAL_NOT_FOUND", "approval not found", status_code=404)
                approval = await approvals.decide(
                    approval_id,
                    approved=approved,
                    actor_id=actor_user_id,
                    decision=decision,
                )
            except ApprovalNotFoundError as exc:
                raise WorkflowApplicationError("APPROVAL_NOT_FOUND", "approval not found", status_code=404) from exc
            if approved and run.status == RunStatus.WAITING_APPROVAL:
                compatibility = await self._resume_compatibility(session, run)
                if compatibility.status == "incompatible":
                    raise WorkflowApplicationError(
                        "SEMANTIC_VERSION_INCOMPATIBLE",
                        "approval cannot resume an incompatible checkpoint",
                        status_code=409,
                    )
                run = await store.transition_run(
                    run.id,
                    expected_state_version=run.state_version,
                    lease_epoch=None,
                    status=RunStatus.QUEUED,
                    changes={"lease_owner": None, "lease_expires_at": None, "error": {}},
                    event_type="progress",
                    event_payload={
                        "root_status": "queued",
                        "status": "queued",
                        "approval_id": str(approval.id),
                        "approval_kind": approval.kind,
                        "approval_granted": True,
                    },
                )
            elif not approved and run.status not in {RunStatus.BLOCKED, RunStatus.CANCELLED, RunStatus.SUCCEEDED, RunStatus.FAILED}:
                run = await store.transition_run(
                    run.id,
                    expected_state_version=run.state_version,
                    lease_epoch=None,
                    status=RunStatus.BLOCKED,
                    changes={"error": {"code": "APPROVAL_REJECTED", "message": "required workflow approval was rejected"}},
                    event_type="error",
                    event_payload={
                        "code": "APPROVAL_REJECTED",
                        "message": "required workflow approval was rejected",
                        "terminal": True,
                        "status": "blocked",
                    },
                )
            await session.commit()
        if approved and run.status == RunStatus.QUEUED and self.wakeup is not None:
            result = self.wakeup(run.id)
            if hasattr(result, "__await__"):
                await result
        return WorkflowApprovalResponse(
            approval_id=approval.id,
            run_id=approval.workflow_run_id,
            node_id=approval.node_id,
            kind=approval.kind,
            status=approval.status,
            request=dict(approval.request or {}),
            decision=dict(approval.decision or {}),
        )

    async def _resume_compatibility(self, session: AsyncSession, run: WorkflowRun):
        try:
            version = int(str(run.workflow_version or "1").removeprefix("v"))
            definition = self.workflow_registry.get(run.workflow_name, version)
        except Exception as exc:
            raise WorkflowApplicationError("INVALID_WORKFLOW", "stored workflow definition is unavailable", status_code=409) from exc
        checkpoint = await CheckpointStore(session).latest(run.id)
        if checkpoint is None:
            # A legacy/control-plane pause can exist before RuntimeEngine had
            # reached a checkpoint boundary. There is no state to reinterpret;
            # requeueing remains safe and the engine still validates the root
            # before it executes any side effect.
            return CompatibilityDecision("compatible")
        target = RuntimeSemanticVersion(
            workflow_definition_digest=definition.definition_digest,
            catalog_version=definition.catalog_version,
            provider_policy_version=definition.provider_policy_version,
            checkpoint_schema_version=definition.checkpoint_schema_version,
            runtime_build_sha=self.runtime_build_sha,
        )
        decision = self.compatibility_policy.assess(run, checkpoint, target)
        if decision.status != "migratable":
            return decision
        try:
            migrated_state = self.checkpoint_migrations.migrate(
                checkpoint.checkpoint_schema_version,
                target.checkpoint_schema_version,
                dict(checkpoint.state_json or {}),
            )
            migrated = await CheckpointStore(session).migrate(
                checkpoint,
                checkpoint_schema_version=target.checkpoint_schema_version,
                state_json=migrated_state,
                runtime_build_sha=target.runtime_build_sha,
            )
            await ApprovalStore(session).audit(
                run.id,
                action="checkpoint_migrated",
                details={
                    "from_schema": checkpoint.checkpoint_schema_version,
                    "to_schema": target.checkpoint_schema_version,
                    "source_checkpoint_seq": checkpoint.checkpoint_seq,
                    "target_checkpoint_seq": migrated.checkpoint_seq,
                },
            )
        except (TypeError, ValueError) as exc:
            raise WorkflowApplicationError(
                "SEMANTIC_VERSION_INCOMPATIBLE",
                "registered checkpoint migration rejected the stored state",
                status_code=409,
            ) from exc
        return CompatibilityDecision("compatible", ("explicit_checkpoint_migration_applied",))

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
        elif workflow_name in {"tutor_routing_v1", "tutor_routing_v2", "tutor_routing_v3"}:
            payload.setdefault("question", payload.get("query", "Tutor question"))
        elif workflow_name in {"assessment_update_v1", "assessment_update_v2"}:
            payload.setdefault("answers", [])
        elif workflow_name in {"course_learning_full_v1", "course_learning_full_v2"}:
            payload.setdefault("query", "Generate a parallel course resource pack")
        elif workflow_name == "fund_recommendation_v1":
            # These are server-owned fields. Dropping them before input-model
            # validation also avoids persisting an untrusted browser snapshot.
            payload.pop("profile_snapshot", None)
            payload.pop("persona_summary", None)
            payload["domain"] = "fund"
        return payload

    @staticmethod
    async def _hydrate_fund_profile(
        session: AsyncSession,
        user_id: str,
        validated_input: dict[str, Any],
    ) -> dict[str, Any]:
        from app.schemas.fund_recommendation import FundRecommendationRequest
        from app.services.fund_recommendation_service import FundRecommendationService

        try:
            parsed_user_id = UUID(str(user_id))
            product_request = FundRecommendationRequest(
                query=str(validated_input.get("query") or ""),
                course_context=validated_input.get("course_context") or {},
            )
        except Exception as exc:
            raise WorkflowApplicationError(
                "INVALID_INPUT",
                "fund recommendation input does not contain a valid course context",
                status_code=422,
            ) from exc
        return await FundRecommendationService(session).prepare_root_input(
            user_id=parsed_user_id,
            request=product_request,
        )

    @staticmethod
    async def _tutor_persona_summary(session: AsyncSession, user_id: str) -> str:
        """Persist only the bounded, relevant persona snapshot for a new tutor root."""
        from app.db.models.identity.user_profile import UserProfile

        try:
            parsed = UUID(str(user_id))
        except (TypeError, ValueError):
            return ""
        profile = await session.get(UserProfile, parsed)
        if profile is None:
            return ""
        allowed = {
            # Current durable demo/persona keys.
            "knowledge_basis",
            "easy_mistakes",
            "learning_pace",
            "interest_anchors",
            "career_goal",
            "base_knowledge",
            "cognitive_style",
            "weak_points",
            "preferred_modality",
            "time_budget",
            "target_direction",
            "motivation",
        }
        snapshot = {
            str(key): value
            for key, value in dict(profile.dimensions or {}).items()
            if key in allowed
        }
        return json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))[:800]

    @staticmethod
    async def _assessment_feedback_constraints(
        session: AsyncSession, user_id: str
    ) -> tuple[list[str], list[str]]:
        """Load only stable mutation keys for the v2 assessment feedback root."""
        from app.db.models.identity.user_capability import UserCapability
        from app.db.models.identity.user_profile import UserProfile

        try:
            parsed = UUID(str(user_id))
        except (TypeError, ValueError):
            return [], []
        capability_dimensions = sorted(
            {
                str(value).strip()
                for value in (
                    await session.scalars(
                        select(UserCapability.dimension).where(UserCapability.user_id == parsed)
                    )
                ).all()
                if str(value).strip()
            }
        )
        # assessment_update_v2 is the course-websec feedback workflow. Its
        # atomic action may update only the course's canonical capability;
        # other profile dimensions remain available to their owning workflows.
        capability_dimensions = [
            dimension for dimension in capability_dimensions if dimension == "web_security"
        ]
        profile = await session.get(UserProfile, parsed)
        persona_dimension_keys = sorted(
            {
                str(key).strip()
                for key in dict(profile.dimensions or {}).keys()
                if str(key).strip()
            }
        ) if profile is not None else []
        return capability_dimensions, persona_dimension_keys

    @staticmethod
    async def _validate_assessment_quiz_artifact(
        session: AsyncSession,
        *,
        user_id: str,
        course_id: Any,
        quiz_artifact_id: Any,
        mode: ExecutionMode,
    ) -> None:
        """Require a real assessment to cite an active, owned quiz Artifact.

        The generated-resource row is the existing durable artifact truth. It
        prevents a browser-provided ID from being projected as a quiz attempt
        when it belongs to another learner/course or was never quality-ready.
        Fixture roots deliberately remain isolated for PresenterMode.
        """
        if mode == ExecutionMode.FIXTURE:
            return

        from app.db.models.resource.generated_resource import GeneratedResource

        try:
            parsed_user_id = UUID(str(user_id))
            parsed_course_id = UUID(str(course_id))
            parsed_artifact_id = UUID(str(quiz_artifact_id))
        except (TypeError, ValueError) as exc:
            raise WorkflowApplicationError(
                "INVALID_ASSESSMENT_ARTIFACT",
                "a real assessment requires a generated quiz artifact",
                status_code=422,
            ) from exc

        artifact = await session.get(GeneratedResource, parsed_artifact_id)
        if (
            artifact is None
            or artifact.user_id != parsed_user_id
            or artifact.course_id != parsed_course_id
            or artifact.resource_type != "quiz"
            or artifact.status != "active"
            or not artifact.evidence_chunk_ids
        ):
            raise WorkflowApplicationError(
                "INVALID_ASSESSMENT_ARTIFACT",
                "the quiz artifact is unavailable for this learner and course",
                status_code=422,
            )

    @staticmethod
    def _initial_budget(
        value: dict[str, Any] | None,
        *,
        mode: ExecutionMode,
    ) -> dict[str, Any]:
        requested = dict(value or {})
        supplied_limits = requested.get("limits")
        limits = dict(supplied_limits) if isinstance(supplied_limits, dict) else dict(requested)
        if (
            mode == ExecutionMode.REAL
            and "max_provider_tokens" not in limits
            and "max_tokens" not in limits
        ):
            limits["max_provider_tokens"] = get_settings().AGENT_RUN_REAL_MAX_TOKENS
        return {
            "limits": limits,
            "requested": requested,
        }

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
        credential_id: UUID | None,
        budget: dict[str, Any],
    ) -> None:
        if (
            dict(run.input_payload or {}) != input_payload
            or str(run.mode) != str(mode)
            or run.requested_provider != provider
            or run.requested_model != model
            or run.credential_id != credential_id
            or dict(run.budget or {}).get("requested", dict(run.budget or {})) != budget
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
