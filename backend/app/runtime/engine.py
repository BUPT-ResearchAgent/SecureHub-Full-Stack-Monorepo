# Status: real

"""The unique production execution authority for SecureHub workflows."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.workflow_runtime import WorkflowStepAttempt
from app.runtime.contracts import ErrorCode, ExecutionMode, ProviderSelection, RunStatus, StepStatus
from app.runtime.harness.contracts import CandidateOutput, SkillDefinition
from app.runtime.harness.execution_context import ExecutionCancelled, ExecutionContext
from app.runtime.harness.executor import SkillExecutionError, SkillExecutor
from app.runtime.ports.run_recorder import AgentRunRecorder, RunRecordingError
from app.runtime.state_machine import InvalidStateTransition, SecureHubStateMachine
from app.runtime.workflow_definition import NodeDefinition, WorkflowDefinition
from app.runtime.workflow_registry import WorkflowRegistry


ActionHandler = Callable[[str, dict[str, Any], dict[str, Any], ExecutionContext], Awaitable[dict[str, Any]]]


class RuntimeEngineError(RuntimeError):
    def __init__(self, code: ErrorCode | str, message: str, *, blocked: bool = False) -> None:
        self.code = str(code)
        self.blocked = blocked
        super().__init__(message)


@dataclass(frozen=True)
class ExecutionResult:
    workflow_run_id: UUID
    status: str
    output: dict[str, Any] | None = None


class RuntimeEngine:
    """Runs a claimed durable root; it never owns an HTTP request lifecycle."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        workflow_registry: WorkflowRegistry,
        skill_catalog: dict[tuple[str, str], SkillDefinition],
        run_store: Any,
        event_store: Any,
        skill_executor: SkillExecutor,
        run_recorder: AgentRunRecorder | None = None,
        action_handler: ActionHandler | None = None,
        checkpoint_store: Any | None = None,
        provider_call_store: Any | None = None,
        runtime_build_sha: str = "dev",
    ) -> None:
        self.session = session
        self.workflow_registry = workflow_registry
        self.skill_catalog = skill_catalog
        self.run_store = run_store
        self.event_store = event_store
        self.skill_executor = skill_executor
        self.run_recorder = run_recorder or AgentRunRecorder(session)
        self.action_handler = action_handler or self._missing_action
        self.checkpoint_store = checkpoint_store
        self.provider_call_store = provider_call_store
        self.runtime_build_sha = runtime_build_sha

    async def execute(self, workflow_run_id: UUID | str, *, lease_owner: str | None = None) -> ExecutionResult:
        run = await self.run_store.get_run(workflow_run_id)
        assert run is not None
        if SecureHubStateMachine.is_terminal_run(run.status):
            return ExecutionResult(run.id, run.status, dict(run.output_ref or {}) or None)
        if run.lease_epoch < 1:
            raise RuntimeEngineError(ErrorCode.LEASE_FENCED, "RuntimeEngine requires a claimed lease")
        if lease_owner is not None and run.lease_owner != lease_owner:
            raise RuntimeEngineError(ErrorCode.LEASE_FENCED, "claimed lease owner does not match RuntimeEngine owner")

        try:
            definition = self.workflow_registry.get(run.workflow_name, self._workflow_version(run.workflow_version))
        except Exception as exc:
            return await self._fail_root(run, ErrorCode.INVALID_WORKFLOW, "registered workflow definition is unavailable")

        try:
            root_input = definition.input_model.model_validate(dict(run.input_payload or {})).model_dump(mode="json")
        except ValidationError:
            return await self._fail_root(run, ErrorCode.INVALID_INPUT, "workflow input failed definition validation")

        if run.cancel_requested_at is not None or run.status == RunStatus.CANCELLING:
            return await self._cancel_root(run)

        state, attempts = await self._recover_state(run.id)
        try:
            await self._recover_completed_provider_results(
                run,
                definition,
                root_input,
                state,
                attempts,
            )
        except RuntimeEngineError as exc:
            return await self._fail_root(run, exc.code, str(exc), blocked=exc.blocked)
        # Pause is cooperative: a request may arrive while another process is
        # inside a provider stream, but RuntimeEngine converges it to paused at
        # the next durable boundary before starting any further node.
        if run.status == RunStatus.PAUSING:
            return await self._pause_root(run, definition, state)

        if run.status != RunStatus.RUNNING:
            try:
                SecureHubStateMachine.assert_run_transition(run.status, RunStatus.RUNNING)
                run = await self.run_store.transition_run(
                    run.id,
                    expected_state_version=run.state_version,
                    lease_epoch=run.lease_epoch,
                    status=RunStatus.RUNNING,
                    event_type="progress",
                    event_payload=self._root_payload(run, {"root_status": "running", "status": "running", "percentage": 1}),
                )
                await self.session.commit()
            except Exception as exc:
                await self.session.rollback()
                raise RuntimeEngineError(ErrorCode.LEASE_FENCED, "unable to start claimed root") from exc

        initial = definition.initial_nodes()
        if len(initial) != 1:
            return await self._fail_root(run, ErrorCode.INVALID_WORKFLOW, "workflow requires one deterministic initial node")
        current: NodeDefinition | None = initial[0]
        # Rebuild the bounded rework counter from durable step attempts after
        # a worker crash. A recovered root must not silently gain extra model
        # retries because its process-local counter was reset.
        rework_count = max(0, max(attempts.values(), default=1) - 1)

        while current is not None:
            run = await self.run_store.get_run(run.id)
            assert run is not None
            if run.cancel_requested_at is not None or run.status == RunStatus.CANCELLING:
                return await self._cancel_root(run)
            if SecureHubStateMachine.is_terminal_run(run.status):
                return ExecutionResult(run.id, run.status, dict(run.output_ref or {}) or None)
            if run.status == RunStatus.PAUSING:
                return await self._pause_root(run, definition, state)

            if current.node_id in state:
                candidate_state = state[current.node_id]
            else:
                try:
                    candidate_state = await self._execute_node(
                        run=run,
                        definition=definition,
                        node=current,
                        root_input=root_input,
                        state=state,
                        attempt=attempts.get(current.node_id, 0) + 1,
                    )
                except ExecutionCancelled:
                    return await self._cancel_root(await self.run_store.get_run(run.id))
                except RuntimeEngineError as exc:
                    if exc.code == ErrorCode.PROVIDER_UNKNOWN_OUTCOME:
                        return await self._wait_for_approval(run, exc)
                    return await self._fail_root(run, exc.code, str(exc), blocked=exc.blocked)
                except Exception as exc:  # noqa: BLE001 - terminal convergence boundary
                    return await self._fail_root(run, ErrorCode.INTERNAL, "runtime node execution failed")
                state[current.node_id] = candidate_state
                attempts[current.node_id] = attempts.get(current.node_id, 0) + 1
                await self._write_checkpoint(run, definition, state)

            condition: str | None = None
            if current.skill_name == "QualityCheck":
                output = candidate_state.get("output", {})
                if bool(output.get("accept")):
                    condition = "accept"
                else:
                    condition = "defect"
                    if rework_count >= definition.max_rework_attempts:
                        return await self._fail_root(
                            run,
                            ErrorCode.QUALITY_REJECTED,
                            "QualityCheck rejected candidate after bounded rework",
                            blocked=True,
                        )
                    successors = definition.successors(current.node_id, condition="defect")
                    if not successors:
                        return await self._fail_root(
                            run,
                            ErrorCode.QUALITY_REJECTED,
                            "QualityCheck rejected candidate without a deterministic rework route",
                            blocked=True,
                        )
                    rework_count += 1
                    SecureHubStateMachine.assert_run_transition(run.status, RunStatus.REWORKING)
                    run = await self.run_store.transition_run(
                        run.id,
                        expected_state_version=run.state_version,
                        lease_epoch=run.lease_epoch,
                        status=RunStatus.REWORKING,
                        event_type="progress",
                        event_payload=self._root_payload(
                            run,
                            {"root_status": "reworking", "status": "reworking", "rework_attempt": rework_count},
                        ),
                    )
                    await self.session.commit()
                    SecureHubStateMachine.assert_run_transition(run.status, RunStatus.RUNNING)
                    run = await self.run_store.transition_run(
                        run.id,
                        expected_state_version=run.state_version,
                        lease_epoch=run.lease_epoch,
                        status=RunStatus.RUNNING,
                        event_type="progress",
                        event_payload=self._root_payload(run, {"root_status": "running", "status": "running", "rework_attempt": rework_count}),
                    )
                    await self.session.commit()
                    # The defect edge intentionally invalidates the prior
                    # candidate. Leaving it in ``state`` would cause the
                    # loop below to skip the producer and re-check the same
                    # rejected output instead of creating a new attempt.
                    rework_target = successors[0]
                    state.pop(current.node_id, None)
                    state.pop(rework_target.node_id, None)
                    current = rework_target
                    continue

            successors = definition.successors(current.node_id, condition=condition)
            if len(successors) > 1:
                return await self._fail_root(run, ErrorCode.INVALID_WORKFLOW, "parallel execution is not enabled for this root")
            current = successors[0] if successors else None

        run = await self.run_store.get_run(run.id)
        assert run is not None
        final_output = self._final_output(definition, state)
        try:
            SecureHubStateMachine.assert_run_transition(run.status, RunStatus.SUCCEEDED)
            run = await self.run_store.transition_run(
                run.id,
                expected_state_version=run.state_version,
                lease_epoch=run.lease_epoch,
                status=RunStatus.SUCCEEDED,
                changes={"output_ref": final_output},
                event_type="done",
                event_payload=self._root_payload(
                    run,
                    {
                        "status": "succeeded",
                        "final_output_ref": final_output.get("ref"),
                        "quality_score": final_output.get("quality_score"),
                    },
                ),
            )
            await self.session.commit()
            return ExecutionResult(run.id, run.status, final_output)
        except Exception as exc:
            await self.session.rollback()
            raise RuntimeEngineError(ErrorCode.LEASE_FENCED, "unable to converge root terminal state") from exc

    async def _execute_node(
        self,
        *,
        run: Any,
        definition: WorkflowDefinition,
        node: NodeDefinition,
        root_input: dict[str, Any],
        state: dict[str, dict[str, Any]],
        attempt: int,
    ) -> dict[str, Any]:
        if node.kind == "action":
            return await self._execute_action(run, definition, node, root_input, state, attempt)
        skill = self._resolve_skill(definition, node, root_input)
        mapped_input = node.input_mapper(root_input, state) if node.input_mapper else dict(root_input)
        step = await self.run_store.create_step_attempt(
            workflow_run_id=run.id,
            node_id=node.node_id,
            attempt=attempt,
            agent_name=skill.agent_name,
            skill_name=skill.name,
            skill_version=str(skill.version),
            skill_definition_digest=skill.definition_digest,
            prompt_version=skill.prompt_version,
            prompt_digest=hashlib.sha256(skill.prompt_template.encode("utf-8")).hexdigest(),
            input_ref={"input_digest": self._digest(mapped_input)},
            status=StepStatus.PENDING,
            lease_epoch=run.lease_epoch,
        )
        context = self._execution_context(run, step, node)
        agent_run_id: UUID
        started = time.perf_counter()
        try:
            agent_run_id = await self.run_recorder.start(
                workflow_run_id=run.id,
                step_attempt_id=step.id,
                workflow_name=definition.name,
                user_id=run.user_id,
                agent_name=skill.agent_name,
                skill_name=skill.name,
                attempt=attempt,
                provider=context.provider_selection.requested_provider,
                model=context.provider_selection.requested_model,
                input_summary={"workflow_run_id": str(run.id), "step_attempt_id": str(step.id), "input_digest": self._digest(mapped_input)},
                require_resolution=run.mode == ExecutionMode.REAL,
            )
            step = await self.run_store.transition_step_attempt(
                step.id,
                expected_state_version=step.state_version,
                lease_epoch=run.lease_epoch,
                status=StepStatus.RUNNING,
                changes={"agent_run_id": agent_run_id},
                event_type="trace",
                event_payload=self._node_payload(
                    run,
                    node,
                    step,
                    {"status": "running", "agent_run_id": str(agent_run_id)},
                ),
                agent_run_id=agent_run_id,
            )
            # This commit is the precondition for RAG and Provider I/O.
            await self.session.commit()
        except Exception as exc:
            await self.session.rollback()
            raise RuntimeEngineError(ErrorCode.AGENT_RUN_PERSIST_FAILED, "running agent_run could not be persisted") from exc

        context = self._execution_context(run, step, node, agent_run_id=agent_run_id)
        try:
            candidate = await self.skill_executor.execute(skill, mapped_input, context)
            output = candidate.output_payload()
            evidence_ids = self._uuid_evidence_ids(candidate)
            await self.run_recorder.succeed(
                agent_run_id,
                output_summary=self._compact_output(output),
                evidence_chunk_ids=evidence_ids,
                quality_score=self._quality_score(output),
                duration_ms=int((time.perf_counter() - started) * 1000),
                token_usage=candidate.usage,
            )
            step = await self.run_store.transition_step_attempt(
                step.id,
                expected_state_version=step.state_version,
                lease_epoch=run.lease_epoch,
                status=StepStatus.SUCCEEDED,
                changes={
                    "output_ref": {
                        "candidate_output": output,
                        "output_digest": self._digest(output),
                        "provider_call_id": candidate.provider_call_id,
                        "evidence_snapshot_ids": [str(item.evidence_snapshot_id) for item in candidate.evidence],
                    },
                    "quality_score": self._quality_score(output),
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                },
                event_type="trace",
                event_payload=self._node_payload(
                    run,
                    node,
                    step,
                    {
                        "status": "succeeded",
                        "agent_run_id": str(agent_run_id),
                        "quality_score": self._quality_score(output),
                    },
                ),
                agent_run_id=agent_run_id,
            )
            await self.session.commit()
            return {
                "output": output,
                "agent_run_id": str(agent_run_id),
                "step_attempt_id": str(step.id),
                "evidence_snapshot_ids": [str(item.evidence_snapshot_id) for item in candidate.evidence],
            "quality_score": self._quality_score(output),
            "usage": candidate.usage,
            "provider_call_id": candidate.provider_call_id,
            }
        except ExecutionCancelled:
            await self._mark_step_cancelled(run, step, agent_run_id, started)
            raise
        except SkillExecutionError as exc:
            await self._mark_step_failed(run, step, agent_run_id, started, exc.code, str(exc), blocked=False)
            raise RuntimeEngineError(exc.code, str(exc)) from exc
        except RunRecordingError as exc:
            await self._mark_step_failed(run, step, agent_run_id, started, ErrorCode.AGENT_RUN_PERSIST_FAILED, str(exc), blocked=False)
            raise RuntimeEngineError(ErrorCode.AGENT_RUN_PERSIST_FAILED, str(exc)) from exc
        except Exception as exc:
            await self._mark_step_failed(run, step, agent_run_id, started, ErrorCode.INTERNAL, "skill execution failed", blocked=False)
            raise RuntimeEngineError(ErrorCode.INTERNAL, "skill execution failed") from exc

    async def _execute_action(
        self,
        run: Any,
        definition: WorkflowDefinition,
        node: NodeDefinition,
        root_input: dict[str, Any],
        state: dict[str, dict[str, Any]],
        attempt: int,
    ) -> dict[str, Any]:
        step = await self.run_store.create_step_attempt(
            workflow_run_id=run.id,
            node_id=node.node_id,
            attempt=attempt,
            status=StepStatus.PENDING,
            lease_epoch=run.lease_epoch,
        )
        step = await self.run_store.transition_step_attempt(
            step.id,
            expected_state_version=step.state_version,
            lease_epoch=run.lease_epoch,
            status=StepStatus.RUNNING,
            event_type="progress",
            event_payload=self._node_payload(run, node, step, {"node_status": "running", "percentage": 85}),
        )
        await self.session.commit()
        context = self._execution_context(run, step, node)
        try:
            output = await self.action_handler(node.action_name or "", root_input, state, context)
            step = await self.run_store.transition_step_attempt(
                step.id,
                expected_state_version=step.state_version,
                lease_epoch=run.lease_epoch,
                status=StepStatus.SUCCEEDED,
                changes={"output_ref": output},
                event_type="progress",
                event_payload=self._node_payload(run, node, step, {"node_status": "succeeded", "percentage": 95}),
                # Artifact visibility is controlled by ArtifactSaga's own
                # hidden `artifact` outbox row. Action lifecycle progress is
                # always public; hiding ordinary persistence actions creates
                # an unfillable public SSE sequence gap before `done`.
                publish_ready=True,
            )
            await self.session.commit()
            return {"output": output, "step_attempt_id": str(step.id)}
        except Exception as exc:
            # Do not expose a storage/provider response body, but retain the
            # exception category so an operator can distinguish a persistence
            # conflict from an external artifact boundary failure.
            message = f"workflow action failed ({exc.__class__.__name__})"
            await self._mark_step_failed(
                run,
                step,
                None,
                time.perf_counter(),
                ErrorCode.ARTIFACT_PERSIST_FAILED,
                message,
                blocked=True,
            )
            raise RuntimeEngineError(ErrorCode.ARTIFACT_PERSIST_FAILED, message, blocked=True) from exc

    async def _mark_step_failed(
        self,
        run: Any,
        step: Any,
        agent_run_id: UUID | None,
        started: float,
        code: ErrorCode | str,
        message: str,
        *,
        blocked: bool,
    ) -> None:
        try:
            if agent_run_id is not None:
                await self.run_recorder.fail(
                    agent_run_id,
                    error_code=str(code),
                    error_summary={"code": str(code), "message": message[:400]},
                    duration_ms=int((time.perf_counter() - started) * 1000),
                )
            await self.run_store.transition_step_attempt(
                step.id,
                expected_state_version=step.state_version,
                lease_epoch=run.lease_epoch,
                status=StepStatus.BLOCKED if blocked else StepStatus.FAILED,
                changes={"error_code": str(code), "error": {"code": str(code), "message": message[:400]}},
                event_type="trace",
                event_payload={
                    "node_id": step.node_id,
                    "agent_name": step.agent_name,
                    "skill_name": step.skill_name,
                    "step_attempt_id": str(step.id),
                    "mode": run.mode,
                    "status": "blocked" if blocked else "failed",
                    "code": str(code),
                },
                agent_run_id=agent_run_id,
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()

    async def _mark_step_cancelled(self, run: Any, step: Any, agent_run_id: UUID, started: float) -> None:
        try:
            await self.run_recorder.fail(
                agent_run_id,
                error_code=ErrorCode.RUN_CANCELLED.value,
                error_summary={"code": ErrorCode.RUN_CANCELLED.value},
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            await self.run_store.transition_step_attempt(
                step.id,
                expected_state_version=step.state_version,
                lease_epoch=run.lease_epoch,
                status=StepStatus.CANCELLED,
                event_type="trace",
                event_payload={"node_id": step.node_id, "status": "cancelled", "agent_run_id": str(agent_run_id)},
                agent_run_id=agent_run_id,
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()

    async def _fail_root(
        self,
        run: Any | None,
        code: ErrorCode | str,
        message: str,
        *,
        blocked: bool = False,
    ) -> ExecutionResult:
        if run is None:
            raise RuntimeEngineError(code, message, blocked=blocked)
        target = RunStatus.BLOCKED if blocked else RunStatus.FAILED
        try:
            if run.status != target:
                SecureHubStateMachine.assert_run_transition(run.status, target)
            run = await self.run_store.transition_run(
                run.id,
                expected_state_version=run.state_version,
                lease_epoch=run.lease_epoch,
                status=target,
                changes={"error": {"code": str(code), "message": message[:400]}},
                event_type="error",
                event_payload=self._root_payload(run, {"code": str(code), "message": message[:400], "recoverable": False, "terminal": True, "status": target.value}),
            )
            await self.session.commit()
            return ExecutionResult(run.id, run.status, None)
        except Exception:
            await self.session.rollback()
            raise RuntimeEngineError(code, message, blocked=blocked)

    async def _wait_for_approval(self, run: Any, error: RuntimeEngineError) -> ExecutionResult:
        try:
            if run.status != RunStatus.WAITING_APPROVAL:
                SecureHubStateMachine.assert_run_transition(run.status, RunStatus.WAITING_APPROVAL)
                run = await self.run_store.transition_run(
                    run.id,
                    expected_state_version=run.state_version,
                    lease_epoch=run.lease_epoch,
                    status=RunStatus.WAITING_APPROVAL,
                    changes={"error": {"code": error.code, "message": str(error)[:400]}},
                    event_type="progress",
                    event_payload=self._root_payload(run, {"root_status": "waiting_approval", "status": "waiting_approval", "code": error.code}),
                )
                await self.session.commit()
            return ExecutionResult(run.id, run.status, None)
        except Exception:
            await self.session.rollback()
            raise

    async def _cancel_root(self, run: Any | None) -> ExecutionResult:
        if run is None:
            raise RuntimeEngineError(ErrorCode.RUN_NOT_FOUND, "workflow run was not found")
        try:
            if run.status != RunStatus.CANCELLED:
                SecureHubStateMachine.assert_run_transition(run.status, RunStatus.CANCELLED)
                run = await self.run_store.transition_run(
                    run.id,
                    expected_state_version=run.state_version,
                    lease_epoch=run.lease_epoch,
                    status=RunStatus.CANCELLED,
                    event_type="done",
                    event_payload=self._root_payload(run, {"status": "cancelled", "final_output_ref": None}),
                )
                await self.session.commit()
            return ExecutionResult(run.id, run.status, None)
        except Exception:
            await self.session.rollback()
            raise

    async def _pause_root(
        self,
        run: Any,
        definition: WorkflowDefinition,
        state: dict[str, dict[str, Any]],
    ) -> ExecutionResult:
        """Persist a checkpoint then converge a cooperative pause exactly once."""
        try:
            await self._write_checkpoint(run, definition, state)
            refreshed = await self.run_store.get_run(run.id)
            assert refreshed is not None
            if refreshed.status == RunStatus.PAUSED:
                return ExecutionResult(refreshed.id, refreshed.status, None)
            if refreshed.status != RunStatus.PAUSING:
                raise RuntimeEngineError(ErrorCode.LEASE_FENCED, "pause state changed before checkpoint convergence")
            SecureHubStateMachine.assert_run_transition(refreshed.status, RunStatus.PAUSED)
            paused = await self.run_store.transition_run(
                refreshed.id,
                expected_state_version=refreshed.state_version,
                lease_epoch=refreshed.lease_epoch,
                status=RunStatus.PAUSED,
                event_type="progress",
                event_payload=self._root_payload(
                    refreshed,
                    {"root_status": "paused", "status": "paused", "checkpointed": True},
                ),
            )
            await self.session.commit()
            return ExecutionResult(paused.id, paused.status, None)
        except RuntimeEngineError:
            raise
        except Exception as exc:
            await self.session.rollback()
            raise RuntimeEngineError(ErrorCode.LEASE_FENCED, "unable to converge paused root") from exc

    async def _recover_state(self, workflow_run_id: UUID) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
        rows = list(
            (
                await self.session.execute(
                    select(WorkflowStepAttempt)
                    .where(WorkflowStepAttempt.workflow_run_id == workflow_run_id)
                    .order_by(WorkflowStepAttempt.node_id, WorkflowStepAttempt.attempt.desc())
                )
            ).scalars().all()
        )
        state: dict[str, dict[str, Any]] = {}
        attempts: dict[str, int] = {}
        for row in rows:
            attempts[row.node_id] = max(attempts.get(row.node_id, 0), row.attempt)
            if row.node_id in state or row.status != StepStatus.SUCCEEDED:
                continue
            output = dict(row.output_ref or {})
            candidate = output.get("candidate_output")
            state[row.node_id] = {
                "output": candidate if isinstance(candidate, dict) else output,
                "step_attempt_id": str(row.id),
                "agent_run_id": str(row.agent_run_id) if row.agent_run_id else None,
                "provider_call_id": output.get("provider_call_id"),
                "evidence_snapshot_ids": list(output.get("evidence_snapshot_ids") or []),
                "quality_score": row.quality_score,
            }
        return state, attempts

    async def _recover_completed_provider_results(
        self,
        run: Any,
        definition: WorkflowDefinition,
        root_input: dict[str, Any],
        state: dict[str, dict[str, Any]],
        attempts: dict[str, int],
    ) -> None:
        """Finish a step from a persisted strict candidate without re-calling a provider.

        A process can die after the journaled provider completion but before
        ``workflow_step_attempts`` becomes succeeded.  The candidate stored in
        the completed journal is already schema-validated. Reusing it is the
        only recovery behaviour that does not claim an external exactly-once
        guarantee or issue a duplicate call.
        """
        if self.provider_call_store is None:
            return
        calls = await self.provider_call_store.list_completed_success_for_run(run.id)
        if not calls:
            return
        nodes = {node.node_id: node for node in definition.nodes}
        changed = False
        for call in calls:
            if call.step_attempt_id is None:
                continue
            step = await self.run_store.get_step_attempt(call.step_attempt_id, required=False)
            if step is None or step.status != StepStatus.RUNNING:
                continue
            node = nodes.get(step.node_id)
            if node is None or node.kind != "skill":
                raise RuntimeEngineError(
                    ErrorCode.INVALID_WORKFLOW,
                    "completed provider call is not associated with a skill node",
                )
            candidate_payload = dict(call.response_ref or {}).get("candidate_output")
            if not isinstance(candidate_payload, dict):
                raise RuntimeEngineError(
                    ErrorCode.AGENT_RUN_PERSIST_FAILED,
                    "completed provider result lacks a reusable strict candidate",
                )
            skill = self._resolve_skill(definition, node, root_input)
            try:
                output = skill.output_model.model_validate(candidate_payload).model_dump(mode="json")
            except ValidationError as exc:
                raise RuntimeEngineError(
                    ErrorCode.STRICT_PARSE_FAILED,
                    "completed provider candidate no longer matches its frozen schema",
                ) from exc
            step = await self.run_store.adopt_step_attempt(step.id, lease_epoch=run.lease_epoch)
            if step.agent_run_id is None:
                raise RuntimeEngineError(
                    ErrorCode.AGENT_RUN_PERSIST_FAILED,
                    "completed provider result has no running agent run",
                )
            evidence_ids = self._uuid_list(output.get("evidence_chunk_ids") or [])
            await self.run_recorder.succeed(
                step.agent_run_id,
                output_summary=self._compact_output(output),
                evidence_chunk_ids=evidence_ids,
                quality_score=self._quality_score(output),
                duration_ms=step.duration_ms,
                token_usage=dict(call.usage or {}),
            )
            step = await self.run_store.transition_step_attempt(
                step.id,
                expected_state_version=step.state_version,
                lease_epoch=run.lease_epoch,
                status=StepStatus.SUCCEEDED,
                changes={
                    "output_ref": {
                        "candidate_output": output,
                        "output_digest": self._digest(output),
                        "provider_call_id": str(call.id),
                        "evidence_snapshot_ids": list(
                            dict(call.response_ref or {}).get("evidence_snapshot_ids") or []
                        ),
                    },
                    "quality_score": self._quality_score(output),
                    "duration_ms": step.duration_ms,
                },
                event_type="trace",
                event_payload=self._node_payload(
                    run,
                    node,
                    step,
                    {
                        "status": "succeeded",
                        "agent_run_id": str(step.agent_run_id),
                        "provider_call_id": str(call.id),
                        "recovered_provider_result": True,
                        "quality_score": self._quality_score(output),
                    },
                ),
                agent_run_id=step.agent_run_id,
                provider_call_id=call.id,
            )
            state[node.node_id] = {
                "output": output,
                "agent_run_id": str(step.agent_run_id),
                "step_attempt_id": str(step.id),
                "provider_call_id": str(call.id),
                "evidence_snapshot_ids": list(
                    dict(call.response_ref or {}).get("evidence_snapshot_ids") or []
                ),
                "quality_score": self._quality_score(output),
                "usage": dict(call.usage or {}),
            }
            attempts[node.node_id] = max(attempts.get(node.node_id, 0), step.attempt)
            changed = True
        if changed:
            await self.session.commit()

    def _resolve_skill(
        self, definition: WorkflowDefinition, node: NodeDefinition, root_input: dict[str, Any]
    ) -> SkillDefinition:
        agent_name, skill_name = node.agent_name, node.skill_name
        if definition.name == "resource_generate_v1" and node.node_id == "producer":
            mapping = definition.metadata.get("producer_by_resource_type", {})
            selected = mapping.get(root_input.get("resource_type"))
            if not selected:
                raise RuntimeEngineError(ErrorCode.INVALID_INPUT, "resource type has no registered producer")
            agent_name, skill_name = selected
        if not agent_name or not skill_name:
            raise RuntimeEngineError(ErrorCode.INVALID_WORKFLOW, "skill node is missing a catalog reference")
        try:
            return self.skill_catalog[(str(agent_name), str(skill_name))]
        except KeyError as exc:
            raise RuntimeEngineError(ErrorCode.INVALID_WORKFLOW, f"unknown skill: {agent_name}.{skill_name}") from exc

    def _execution_context(self, run: Any, step: Any, node: NodeDefinition, *, agent_run_id: UUID | None = None) -> ExecutionContext:
        async def emit(event_type: str, payload: dict[str, Any]) -> None:
            event_payload = self._node_payload(run, node, step, payload)
            await self.event_store.append_event(
                run.id,
                event_type,
                event_payload,
                step_attempt_id=step.id,
                agent_run_id=agent_run_id or step.agent_run_id,
                lease_epoch=run.lease_epoch,
            )
            await self.session.commit()

        async def cancelled() -> bool:
            # PostgreSQL is checked at safe boundaries, allowing an API process
            # to cancel a stream currently owned by another Worker process.
            current = await self.run_store.get_run(run.id)
            return bool(
                current
                and (
                    current.cancel_requested_at is not None
                    or current.status == RunStatus.CANCELLING
                )
            )

        return ExecutionContext(
            workflow_run_id=run.id,
            step_attempt_id=step.id,
            agent_run_id=agent_run_id or step.agent_run_id or UUID(int=0),
            user_id=run.user_id,
            mode=ExecutionMode(run.mode),
            provider_selection=ProviderSelection(
                requested_provider=run.requested_provider,
                requested_model=run.requested_model,
                policy_version=run.provider_policy_version,
            ),
            lease_epoch=run.lease_epoch,
            course_id=(run.input_payload or {}).get("course_id"),
            persona_summary=str((run.input_payload or {}).get("persona_summary") or ""),
            stream=True,
            emit=emit,
            cancellation_requested=cancelled,
            extras={"provider_attempt": step.attempt},
        )

    async def _write_checkpoint(self, run: Any, definition: WorkflowDefinition, state: dict[str, dict[str, Any]]) -> None:
        if self.checkpoint_store is None:
            return
        try:
            await self.checkpoint_store.save(
                workflow_run_id=run.id,
                workflow_definition_digest=definition.definition_digest,
                catalog_version=definition.catalog_version,
                checkpoint_schema_version=definition.checkpoint_schema_version,
                runtime_build_sha=self.runtime_build_sha,
                state_json={key: self._checkpoint_value(value) for key, value in state.items()},
                event_cursor=max(int(run.next_event_sequence or 1) - 1, 0),
                lease_epoch=run.lease_epoch,
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise RuntimeEngineError(ErrorCode.INTERNAL, "checkpoint persistence failed")

    @staticmethod
    async def _missing_action(
        action_name: str,
        _root_input: dict[str, Any],
        _state: dict[str, Any],
        _context: ExecutionContext,
    ) -> dict[str, Any]:
        raise RuntimeEngineError(ErrorCode.ARTIFACT_PERSIST_FAILED, f"workflow action is not registered: {action_name}")

    @staticmethod
    def _workflow_version(value: str | None) -> int:
        text = str(value or "1").removeprefix("v")
        return int(text)

    @staticmethod
    def _digest(value: Any) -> str:
        import json

        return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    @staticmethod
    def _quality_score(output: dict[str, Any]) -> float | None:
        value = output.get("quality_score")
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _uuid_evidence_ids(candidate: CandidateOutput) -> list[UUID]:
        values: list[UUID] = []
        for item in candidate.evidence:
            try:
                values.append(UUID(str(item.chunk_id)))
            except (TypeError, ValueError):
                continue
        return values

    @staticmethod
    def _uuid_list(values: list[Any]) -> list[UUID]:
        resolved: list[UUID] = []
        for value in values:
            try:
                resolved.append(UUID(str(value)))
            except (TypeError, ValueError):
                continue
        return resolved

    @staticmethod
    def _compact_output(output: dict[str, Any]) -> dict[str, Any]:
        excluded = {"content", "markdown", "text", "raw_response", "reasoning", "reasoning_content"}
        return {key: value for key, value in output.items() if key not in excluded}

    @staticmethod
    def _checkpoint_value(value: dict[str, Any]) -> dict[str, Any]:
        return {key: item for key, item in value.items() if key not in {"raw_response", "reasoning", "reasoning_content"}}

    def _root_payload(self, run: Any, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "mode": run.mode,
            "requested_provider": run.requested_provider,
            "requested_model": run.requested_model,
            **payload,
        }

    @staticmethod
    def _node_payload(run: Any, node: NodeDefinition, step: Any, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "node_id": node.node_id,
            "agent_name": node.agent_name,
            "skill_name": node.skill_name,
            "step_attempt_id": str(step.id),
            "mode": run.mode,
            **payload,
        }

    @staticmethod
    def _final_output(definition: WorkflowDefinition, state: dict[str, dict[str, Any]]) -> dict[str, Any]:
        if "persist_artifact" in state:
            output = state["persist_artifact"].get("output", {})
            return {"ref": output.get("resource_id"), "quality_score": output.get("quality_score"), "artifact": output}
        last = state.get(definition.nodes[-1].node_id, {})
        return {"ref": last.get("step_attempt_id"), "output": last.get("output", {}), "quality_score": last.get("quality_score")}


__all__ = ["ExecutionResult", "RuntimeEngine", "RuntimeEngineError"]
