# Status: real

"""Application service for durable WorkflowRun control operations.

HTTP product adapters call this service only for DTO/auth mapping and control.
It creates a durable root but never executes a Skill or owns a process-local
queue; RuntimeWorker claims the root through PostgreSQL.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db.models.education.education_domain import CourseEnrollment, StudentGroup, StudentGroupMember
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.db.models.learning.quiz_item import QuizItem
from app.db.models.learning.quiz_quality import QuizItemEvidence
from app.db.models.resource.generated_resource import GeneratedResource
from app.db.models.teaching.teacher_production import (
    Assessment,
    AssessmentAssignment,
    AssessmentItem,
    AssessmentSubmission,
    AssessmentVersion,
)
from app.db.seeds._constants import resolve_course_product
from app.llm.model_catalog import ModelSourceError, resolve_model_source
from app.db.models.workflow_runtime import WorkflowApproval, WorkflowProviderCall, WorkflowRun, WorkflowStepAttempt
from app.repositories.identity.provider_credentials import ProviderCredentialRepository
from app.runtime.contracts import EventEnvelope, ExecutionMode, RunStatus, RuntimeSemanticVersion
from app.runtime.guardrails.input_filter import review_input
from app.runtime.guardrails.prompt_injection_check import detect_prompt_injection
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
from app.services.learning.quiz_quality_service import QuizQualityError, QuizQualityService
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


# Every workflow below can create a root that eventually invokes course
# Skills, persists Evidence/AgentRun/Artifact state, or mutates progress.  Its
# readiness check belongs here so the generic /workflow-runs route cannot
# bypass a product endpoint's UX guard.
_COURSE_CONTENT_WORKFLOWS = frozenset(
    {
        "course_plan_v1",
        "resource_generate_v1",
        "course_learning_full_v1",
        "course_learning_full_v2",
        "tutor_routing_v1",
        "tutor_routing_v2",
        "tutor_routing_v3",
        "assessment_update_v1",
        "assessment_update_v2",
    }
)


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

        async with self.sessionmaker() as session:
            await self._preflight_course_content(
                workflow_name=definition.name,
                validated_input=validated_input,
            )
            await self._canonicalise_resource_topic(
                session,
                workflow_name=definition.name,
                validated_input=validated_input,
            )
            if definition.name == "tutor_routing_v3":
                validated_input["persona_summary"] = await self._tutor_persona_summary(session, request.user_id)
            if definition.name == "assessment_update_v2":
                artifact = await self._validate_assessment_quiz_artifact(
                    session,
                    user_id=request.user_id,
                    course_id=validated_input.get("course_id"),
                    quiz_artifact_id=validated_input.get("quiz_artifact_id"),
                    mode=request.mode,
                )
                if request.mode == ExecutionMode.REAL:
                    prepared_answers, prepared_context = await self._prepare_published_assessment_answers(
                        session,
                        user_id=request.user_id,
                        course_id=validated_input.get("course_id"),
                        artifact=artifact,
                        raw_answers=validated_input.get("answers"),
                        context=validated_input.get("context"),
                    )
                    # The root retains only a bounded, server-derived prompt
                    # projection. The full learner answers remain in the
                    # immutable published submission and are never copied
                    # into a model prompt by the browser.
                    validated_input["answers"] = prepared_answers
                    validated_input["context"] = prepared_context
                capability_dimensions, persona_dimension_keys = await self._assessment_feedback_constraints(
                    session, request.user_id
                )
                # These are server-owned constraints, not caller-controlled DTO
                # fields. They make the mutation target explicit to the two
                # generative Skills before the final atomic action validates it.
                validated_input["capability_dimensions"] = capability_dimensions
                validated_input["persona_dimension_keys"] = persona_dimension_keys
            provider, model = await self._provider_selection(session, request)
            credential_id = None
            if request.mode == ExecutionMode.REAL and provider in {"deepseek", "xfyun"}:
                # Resolve the active key once while the root is created. The
                # worker receives only its opaque ID and will never consult a
                # later active-key selection for this root.
                active_credential = await ProviderCredentialRepository(session).get_active(
                    UUID(str(request.user_id)), provider
                )
                credential_id = active_credential.id if active_credential is not None else None
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
    async def _preflight_course_content(
        *,
        workflow_name: str,
        validated_input: dict[str, Any],
    ) -> None:
        """Canonicalise a known course and reject preview roots before side effects.

        The manifest-backed lookup intentionally accepts only explicit product
        UUID/code/legacy aliases.  There is no default ``course_websec`` path:
        an unknown identifier never reaches a durable root, Provider selection,
        event stream, AgentRun, Evidence Snapshot or Artifact Saga.
        """
        if workflow_name not in _COURSE_CONTENT_WORKFLOWS:
            return
        raw_course_id = validated_input.get("course_id")
        product = resolve_course_product(str(raw_course_id) if raw_course_id is not None else None)
        if product is None:
            raise WorkflowApplicationError(
                "COURSE_NOT_FOUND",
                "课程不存在或链接已失效。",
                status_code=404,
            )
        if product.content_status != "ready":
            raise WorkflowApplicationError(
                "COURSE_CONTENT_NOT_READY",
                product.unavailable_reason or "课程内容正在建设中，暂不能启动真实学习工作流。",
                status_code=409,
            )

        # Do not trust a browser-provided domain.  The persisted root records
        # the product's canonical UUID/domain only after readiness succeeds.
        validated_input["course_id"] = str(product.id)
        validated_input["domain"] = product.domain

    @staticmethod
    async def _canonicalise_resource_topic(
        session: AsyncSession,
        *,
        workflow_name: str,
        validated_input: dict[str, Any],
    ) -> None:
        """Bind resource generation to the server-owned knowledge-point title."""
        if workflow_name != "resource_generate_v1":
            return
        raw_kp_id = validated_input.get("kp_id")
        if raw_kp_id is None:
            return
        try:
            kp_id = UUID(str(raw_kp_id))
            course_id = UUID(str(validated_input["course_id"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise WorkflowApplicationError(
                "KNOWLEDGE_POINT_NOT_FOUND",
                "知识点不存在或不属于当前课程。",
                status_code=404,
            ) from exc
        node = await session.get(KnowledgeNode, kp_id)
        canonical_domain = str(validated_input.get("domain") or "")
        if (
            node is None
            or node.course_id != course_id
            or node.domain != canonical_domain
        ):
            raise WorkflowApplicationError(
                "KNOWLEDGE_POINT_NOT_FOUND",
                "知识点不存在或不属于当前课程。",
                status_code=404,
            )

        options = validated_input.get("options")
        retry = isinstance(options, dict) and bool(options.get("retry_source_resource_id"))
        action = "Regenerate" if retry else "Generate"
        resource_type = str(validated_input.get("resource_type") or "resource")
        validated_input["query"] = (
            f'{action} {resource_type} course resource for knowledge point "{node.name}". '
            "Use only evidence relevant to this knowledge point."
        )

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

    @classmethod
    async def _prepare_published_assessment_answers(
        cls,
        session: AsyncSession,
        *,
        user_id: str,
        course_id: Any,
        artifact: GeneratedResource | None,
        raw_answers: Any,
        context: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Bind a real assessment root to one published frozen submission.

        Browser input may identify a quiz item and contain a learner answer,
        but it must never supply question text, options, grading context, or
        a trusted assessment version.  The full answer set is safety-checked
        here, matched exactly to the durable submission, then reduced to a
        bounded prompt projection.  That avoids copying a 36-question page
        into both ``query`` and ``answers`` while preserving the global
        SkillExecutor guardrail for every value that originated with a learner.
        """

        if artifact is None:
            raise WorkflowApplicationError(
                "INVALID_ASSESSMENT_ARTIFACT",
                "当前测验资源缺少可验证的持久化来源。",
                status_code=422,
            )
        try:
            parsed_user_id = UUID(str(user_id))
            parsed_course_id = UUID(str(course_id))
        except (TypeError, ValueError) as exc:
            raise WorkflowApplicationError(
                "ASSESSMENT_SCOPE_DENIED",
                "当前课程或学习者身份无效，不能更新能力画像。",
                status_code=422,
            ) from exc

        raw_context = dict(context) if isinstance(context, dict) else {}
        try:
            assignment_id = UUID(str(raw_context.get("assessment_assignment_id")))
        except (TypeError, ValueError) as exc:
            raise WorkflowApplicationError(
                "ASSESSMENT_SUBMISSION_REQUIRED",
                "请先提交当前已发布评估，再更新能力画像。",
                status_code=422,
            ) from exc

        submitted_answers = cls._normalise_assessment_answers(raw_answers, source="request")
        cls._assert_assessment_answers_safe(submitted_answers)

        assignment = await session.get(AssessmentAssignment, assignment_id)
        if assignment is None or assignment.status != "active":
            raise WorkflowApplicationError(
                "ASSESSMENT_SCOPE_DENIED",
                "当前评估已关闭、撤回或不存在，不能用于能力画像更新。",
                status_code=422,
            )
        version = await session.get(AssessmentVersion, assignment.assessment_version_id)
        assessment = await session.get(Assessment, version.assessment_id) if version is not None else None
        if (
            version is None
            or assessment is None
            or version.state != "published"
            or assessment.status != "published"
            or assessment.course_id != parsed_course_id
        ):
            raise WorkflowApplicationError(
                "ASSESSMENT_VERSION_UNAVAILABLE",
                "当前评估版本不是该课程可用的已发布冻结版本。",
                status_code=422,
            )

        artifact_content = artifact.content if isinstance(artifact.content, dict) else {}
        try:
            artifact_version_id = UUID(str(artifact_content.get("assessment_version_id")))
        except (TypeError, ValueError) as exc:
            raise WorkflowApplicationError(
                "INVALID_ASSESSMENT_ARTIFACT",
                "测验资源未关联当前评估的冻结版本。",
                status_code=422,
            ) from exc
        if artifact_version_id != version.id:
            raise WorkflowApplicationError(
                "INVALID_ASSESSMENT_ARTIFACT",
                "测验资源与当前已发布评估版本不一致。",
                status_code=422,
            )

        enrollment = await session.scalar(
            select(CourseEnrollment).where(
                CourseEnrollment.course_id == parsed_course_id,
                CourseEnrollment.student_id == parsed_user_id,
                CourseEnrollment.status == "enrolled",
            )
        )
        if enrollment is None or not await cls._assessment_assignment_allows_learner(
            session,
            assignment=assignment,
            learner_id=parsed_user_id,
            teaching_class_id=enrollment.teaching_class_id,
        ):
            raise WorkflowApplicationError(
                "ASSESSMENT_SCOPE_DENIED",
                "当前学习者不在该已发布评估的授权范围内。",
                status_code=403,
            )

        submission = await session.scalar(
            select(AssessmentSubmission).where(
                AssessmentSubmission.assignment_id == assignment.id,
                AssessmentSubmission.student_id == parsed_user_id,
            )
        )
        if submission is None or submission.status not in {"submitted", "late"}:
            raise WorkflowApplicationError(
                "ASSESSMENT_SUBMISSION_REQUIRED",
                "请先完成并提交当前已发布评估，再更新能力画像。",
                status_code=422,
            )
        persisted_answers = cls._normalise_assessment_answer_mapping(
            submission.answers,
            source="persisted submission",
        )
        if not cls._assessment_answers_match(submitted_answers, persisted_answers):
            raise WorkflowApplicationError(
                "ASSESSMENT_SUBMISSION_MISMATCH",
                "本次作答与已提交的冻结评估记录不一致；请刷新后从真实提交记录继续。",
                status_code=422,
            )

        item_rows = list(
            (
                await session.execute(
                    select(AssessmentItem, QuizItem, KnowledgeNode)
                    .join(QuizItem, QuizItem.id == AssessmentItem.quiz_item_id)
                    .join(KnowledgeNode, KnowledgeNode.id == QuizItem.kp_id)
                    .where(AssessmentItem.assessment_version_id == version.id)
                    .order_by(AssessmentItem.position)
                )
            ).all()
        )
        frozen_item_ids = {str(item.quiz_item_id) for item, _, _ in item_rows}
        if not item_rows or set(persisted_answers) != frozen_item_ids:
            raise WorkflowApplicationError(
                "ASSESSMENT_SUBMISSION_MISMATCH",
                "已提交答案不完整或不属于当前冻结评估版本。",
                status_code=422,
            )

        try:
            publishable = await QuizQualityService(session).list_publishable_items(
                course_id=parsed_course_id
            )
        except QuizQualityError as exc:
            raise WorkflowApplicationError(
                "ASSESSMENT_QUESTION_UNAVAILABLE",
                "当前评估题目尚未通过课程质量校验。",
                status_code=422,
            ) from exc
        publishable_ids = {str(item.id) for item in publishable.items}
        evidence_item_ids = {
            str(value)
            for value in (
                await session.scalars(
                    select(QuizItemEvidence.quiz_item_id).where(
                        QuizItemEvidence.quiz_item_id.in_([item.quiz_item_id for item, _, _ in item_rows])
                    )
                )
            ).all()
        }
        if not frozen_item_ids <= publishable_ids or not frozen_item_ids <= evidence_item_ids:
            raise WorkflowApplicationError(
                "ASSESSMENT_QUESTION_UNAVAILABLE",
                "当前评估题目缺少质量通过状态或 Evidence 关联。",
                status_code=422,
            )

        prompt_answers, summary = cls._assessment_prompt_projection(
            item_rows=item_rows,
            persisted_answers=persisted_answers,
        )
        # Keep the summary on a real answer reference, rather than adding a
        # synthetic "answer" that would inflate the audit's answered count.
        prompt_answers[0]["assessment_summary"] = summary
        canonical_context = {
            key: value
            for key, value in raw_context.items()
            if key not in {
                "assessment_assignment_id",
                "assessment_version_id",
                "assessment_submission_id",
                "assessment_source",
            }
        }
        canonical_context.update(
            {
                "assessment_assignment_id": str(assignment.id),
                "assessment_version_id": str(version.id),
                "assessment_submission_id": str(submission.id),
                "assessment_source": "server_verified_published_submission",
            }
        )
        return prompt_answers, canonical_context

    @staticmethod
    async def _assessment_assignment_allows_learner(
        session: AsyncSession,
        *,
        assignment: AssessmentAssignment,
        learner_id: UUID,
        teaching_class_id: UUID | None,
    ) -> bool:
        if assignment.target_type == "student":
            return assignment.student_id == learner_id
        if assignment.target_type == "class":
            return assignment.teaching_class_id is not None and assignment.teaching_class_id == teaching_class_id
        if assignment.target_type != "group" or assignment.group_id is None:
            return False
        member = await session.scalar(
            select(StudentGroupMember.id)
            .join(StudentGroup, StudentGroup.id == StudentGroupMember.group_id)
            .where(
                StudentGroupMember.group_id == assignment.group_id,
                StudentGroupMember.student_id == learner_id,
                StudentGroupMember.status == "active",
                StudentGroup.status == "active",
                StudentGroup.teaching_class_id == teaching_class_id,
            )
        )
        return member is not None

    @staticmethod
    def _normalise_assessment_answers(value: Any, *, source: str) -> dict[str, str | list[str]]:
        if not isinstance(value, list) or not value:
            raise WorkflowApplicationError(
                "ASSESSMENT_ANSWERS_INVALID",
                "请提交至少一道当前冻结评估中的真实题目答案。",
                status_code=422,
            )
        answers: dict[str, str | list[str]] = {}
        for raw in value:
            if not isinstance(raw, dict) or set(raw) - {"quiz_item_id", "answer"}:
                raise WorkflowApplicationError(
                    "ASSESSMENT_ANSWERS_INVALID",
                    "评估请求只能提交题目引用和学习者作答，不能传入题干、选项或评分上下文。",
                    status_code=422,
                )
            try:
                quiz_item_id = str(UUID(str(raw.get("quiz_item_id"))))
            except (TypeError, ValueError) as exc:
                raise WorkflowApplicationError(
                    "ASSESSMENT_ANSWERS_INVALID",
                    "每道作答都必须引用当前评估中的真实题目。",
                    status_code=422,
                ) from exc
            if quiz_item_id in answers:
                raise WorkflowApplicationError(
                    "ASSESSMENT_ANSWERS_INVALID",
                    "同一道评估题目不能重复提交。",
                    status_code=422,
                )
            answers[quiz_item_id] = WorkflowApplicationService._normalise_assessment_answer_value(
                raw.get("answer"),
                source=source,
            )
        return answers

    @staticmethod
    def _normalise_assessment_answer_mapping(value: Any, *, source: str) -> dict[str, str | list[str]]:
        if not isinstance(value, dict) or not value:
            raise WorkflowApplicationError(
                "ASSESSMENT_SUBMISSION_MISMATCH",
                f"{source} 缺少可验证的学习者作答。",
                status_code=422,
            )
        answers: dict[str, str | list[str]] = {}
        for raw_id, raw_answer in value.items():
            try:
                quiz_item_id = str(UUID(str(raw_id)))
            except (TypeError, ValueError) as exc:
                raise WorkflowApplicationError(
                    "ASSESSMENT_SUBMISSION_MISMATCH",
                    f"{source} 包含无效题目引用。",
                    status_code=422,
                ) from exc
            answers[quiz_item_id] = WorkflowApplicationService._normalise_assessment_answer_value(
                raw_answer,
                source=source,
            )
        return answers

    @staticmethod
    def _normalise_assessment_answer_value(value: Any, *, source: str) -> str | list[str]:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if (
            isinstance(value, list)
            and 0 < len(value) <= 8
            and all(isinstance(item, str) and item.strip() for item in value)
        ):
            return [item.strip() for item in value]
        raise WorkflowApplicationError(
            "ASSESSMENT_ANSWERS_INVALID",
            f"{source} 中的作答必须是非空文本或有限个文本选项。",
            status_code=422,
        )

    @staticmethod
    def _assert_assessment_answers_safe(answers: dict[str, str | list[str]]) -> None:
        text = json.dumps(
            [{"quiz_item_id": item_id, "answer": answer} for item_id, answer in answers.items()],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        review = review_input(text)
        if not review.allowed:
            raise WorkflowApplicationError(
                "ASSESSMENT_INPUT_GUARDRAIL",
                "作答内容过长，未进入评估工作流；请缩短作答后重新提交。",
                status_code=422,
            )
        if detect_prompt_injection(review.normalized_text).detected:
            raise WorkflowApplicationError(
                "ASSESSMENT_INPUT_GUARDRAIL",
                "作答内容未通过输入安全检查；请删除指令性文本后重新提交。",
                status_code=422,
            )

    @staticmethod
    def _assessment_answers_match(
        requested: dict[str, str | list[str]],
        persisted: dict[str, str | list[str]],
    ) -> bool:
        if set(requested) != set(persisted):
            return False
        return all(
            WorkflowApplicationService._assessment_answer_values_match(
                requested[item_id],
                persisted[item_id],
            )
            for item_id in requested
        )

    @staticmethod
    def _assessment_answer_values_match(expected: str | list[str], supplied: str | list[str]) -> bool:
        def normalized(value: str | list[str]) -> list[str]:
            values = value if isinstance(value, list) else value.split(";")
            return sorted(
                "".join(item.strip().lower().split())
                for item in values
                if item.strip()
            )

        return normalized(expected) == normalized(supplied)

    @staticmethod
    def _assessment_prompt_projection(
        *,
        item_rows: list[tuple[AssessmentItem, QuizItem, KnowledgeNode]],
        persisted_answers: dict[str, str | list[str]],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Create a bounded prompt view from the server-owned frozen version."""

        answers: list[dict[str, Any]] = []
        topics: dict[str, dict[str, int]] = defaultdict(
            lambda: {"objective_matched": 0, "objective_review": 0, "subjective_submitted": 0}
        )
        objective_matched = 0
        objective_review = 0
        subjective_submitted = 0
        for item, quiz_item, node in item_rows:
            item_id = str(item.quiz_item_id)
            learner_answer = persisted_answers[item_id]
            answers.append(
                {
                    "quiz_item_id": item_id,
                    "answer": WorkflowApplicationService._assessment_answer_excerpt(learner_answer),
                }
            )
            topic_name = str(node.name).strip()[:24] or "未命名知识点"
            topic = topics[topic_name]
            if item.grading_mode == "objective":
                snapshot = item.question_snapshot if isinstance(item.question_snapshot, dict) else {}
                expected = str(snapshot.get("answer") or quiz_item.answer or "").strip()
                if not expected:
                    raise WorkflowApplicationError(
                        "ASSESSMENT_VERSION_UNAVAILABLE",
                        "当前冻结评估题目缺少可验证答案。",
                        status_code=422,
                    )
                if WorkflowApplicationService._assessment_answer_values_match(expected, learner_answer):
                    objective_matched += 1
                    topic["objective_matched"] = int(topic["objective_matched"]) + 1
                else:
                    objective_review += 1
                    topic["objective_review"] = int(topic["objective_review"]) + 1
            else:
                subjective_submitted += 1
                topic["subjective_submitted"] = int(topic["subjective_submitted"]) + 1
        if not answers:
            raise WorkflowApplicationError(
                "ASSESSMENT_SUBMISSION_MISMATCH",
                "当前冻结评估没有可用于能力画像的题目。",
                status_code=422,
            )
        # Only topics needing subjective review or a corrective action go into
        # the prompt. The aggregate still reflects the whole frozen version,
        # while avoiding a second copy of a 36-question page in the query.
        topic_rows = [
            [
                name,
                int(stats["objective_matched"]),
                int(stats["objective_review"]),
                int(stats["subjective_submitted"]),
            ]
            for name, stats in sorted(topics.items())
            if stats["objective_review"] or stats["subjective_submitted"]
        ]
        return answers, {
            "source": "server_verified_published_submission",
            "objective": [objective_matched, objective_review],
            "subjective_submitted": subjective_submitted,
            "topic_schema": "[knowledge_point,objective_matched,objective_review,subjective_submitted]",
            "topics": topic_rows,
        }

    @staticmethod
    def _assessment_answer_excerpt(value: str | list[str], *, limit: int = 4) -> str | list[str]:
        if isinstance(value, str):
            return value[:limit]
        return [item[:limit] for item in value[:8]]

    @staticmethod
    async def _validate_assessment_quiz_artifact(
        session: AsyncSession,
        *,
        user_id: str,
        course_id: Any,
        quiz_artifact_id: Any,
        mode: ExecutionMode,
    ) -> GeneratedResource | None:
        """Require a real assessment to cite an active, owned quiz Artifact.

        The generated-resource row is the existing durable artifact truth. It
        prevents a browser-provided ID from being projected as a quiz attempt
        when it belongs to another learner/course or was never quality-ready.
        Fixture roots deliberately remain isolated for PresenterMode.
        """
        if mode == ExecutionMode.FIXTURE:
            return None

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
        return artifact

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
    async def _provider_selection(
        session: AsyncSession,
        request: WorkflowRunStartRequest,
    ) -> tuple[str | None, str | None]:
        if request.mode == ExecutionMode.FIXTURE:
            return "fixture", request.model or "fixture-v1"
        settings = get_settings()
        if not settings.AGENT_RUN_REAL_ENABLED:
            raise WorkflowApplicationError(
                "REAL_MODE_DISABLED",
                "real workflow execution is disabled by server policy",
                status_code=503,
            )
        if request.provider == "fixture":
            raise WorkflowApplicationError("INVALID_PROVIDER", "real mode cannot select fixture", status_code=422)
        provider = request.provider
        model = request.model
        if provider is None and model is None:
            try:
                selection = await ProviderCredentialRepository(session).get_model_selection(UUID(str(request.user_id)))
            except ValueError as exc:
                raise WorkflowApplicationError("INVALID_INPUT", "workflow user identifier is invalid", status_code=422) from exc
            if selection is not None:
                provider = selection.provider
                model = selection.model
        try:
            source = resolve_model_source(settings, provider=provider, model=model)
        except ModelSourceError as exc:
            raise WorkflowApplicationError(
                "MODEL_SOURCE_UNSUPPORTED",
                "requested provider or model is not enabled by server policy",
                status_code=422,
            ) from exc
        return source.provider, source.model

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
