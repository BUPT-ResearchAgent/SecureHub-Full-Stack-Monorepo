# Status: real

"""Fault-injection tests for recovery boundaries that must survive a process loss."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models.workflow_runtime import WorkflowEvent, WorkflowRun
from app.runtime.artifacts import ArtifactRecovery, ArtifactSaga
from app.runtime.engine import RuntimeEngine
from app.runtime.execution.lease import Lease
from app.runtime.execution.recovery import RecoveryService
from app.runtime.execution.worker import RuntimeWorker
from app.runtime.harness.contracts import SkillDefinition
from app.runtime.persistence import (
    CheckpointStore,
    EventOutboxPublisher,
    EventStore,
    LeaseFencedError,
    ProviderCallStore,
    RunStore,
)
from app.runtime.persistence.common import lease_is_active, utcnow
from app.runtime.redis_notify import RedisRuntimeNotifier
from app.runtime.supervisor import RuntimeSupervisor
from app.runtime.workflow_definition import NodeDefinition, WorkflowDefinition
from app.runtime.workflow_registry import WorkflowRegistry
from app.schemas.agent_control import WorkflowRunStartRequest
from app.services.workflow_application_service import WorkflowApplicationError, WorkflowApplicationService
from app.streaming.sse_gateway import WorkflowSSEGateway


class _ControlInput(BaseModel):
    value: str


class _ControlOutput(BaseModel):
    value: str


class _RecoveredOutput(BaseModel):
    content: str
    evidence_chunk_ids: list[str] = []
    quality_score: float | None = None


_CONTROL_DEFINITION = WorkflowDefinition(
    name="durable_control_v1",
    version=1,
    input_model=_ControlInput,
    output_model=_ControlOutput,
    nodes=(NodeDefinition(node_id="noop", kind="action", action_name="Noop"),),
)

_RECOVERY_DEFINITION = WorkflowDefinition(
    name="durable_provider_recovery_v1",
    version=1,
    input_model=_ControlInput,
    output_model=_RecoveredOutput,
    nodes=(NodeDefinition(node_id="producer", kind="skill", agent_name="test_agent", skill_name="TestSkill"),),
)


class _NoopRecorder:
    def __init__(self) -> None:
        self.succeeded: list[dict[str, Any]] = []

    async def succeed(self, agent_run_id: UUID, **kwargs: Any) -> None:
        self.succeeded.append({"agent_run_id": agent_run_id, **kwargs})


class _MemoryArtifactStorage:
    provider_name = "memory"
    bucket = "tests"

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put_bytes(
        self,
        *,
        object_key: str,
        content: bytes,
        mime_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> None:
        self.objects[object_key] = content

    async def get_bytes(self, object_key: str) -> bytes | None:
        return self.objects.get(object_key)

    async def exists(self, object_key: str) -> bool:
        return object_key in self.objects

    async def delete(self, object_key: str) -> None:
        self.objects.pop(object_key, None)


class _SimulatedPublisherCrash(BaseException):
    pass


async def _claimed_run(
    session,
    *,
    workflow_name: str = _CONTROL_DEFINITION.name,
    input_payload: dict[str, Any] | None = None,
) -> tuple[RunStore, Any]:
    store = RunStore(session)
    run = await store.create_run(
        {
            "workflow_name": workflow_name,
            "workflow_version": "1",
            "workflow_definition_digest": "d" * 64,
            "catalog_version": "catalog-v1",
            "provider_policy_version": "provider-v1",
            "checkpoint_schema_version": "checkpoint-v1",
            "runtime_build_sha": "test",
            "mode": "fixture",
            "input_payload": input_payload or {"value": "durable control"},
        }
    )
    await session.commit()
    claimed = await store.claim_next("worker-a", lease_seconds=60)
    assert claimed is not None
    await session.commit()
    return store, claimed


def _engine(
    session,
    definition: WorkflowDefinition,
    store: RunStore,
    events: EventStore,
    *,
    recorder: _NoopRecorder | None = None,
    provider_calls: ProviderCallStore | None = None,
) -> RuntimeEngine:
    registry = WorkflowRegistry()
    registry.register(definition)
    return RuntimeEngine(
        session=session,
        workflow_registry=registry,
        skill_catalog={},
        run_store=store,
        event_store=events,
        skill_executor=object(),
        run_recorder=recorder or _NoopRecorder(),
        checkpoint_store=CheckpointStore(session),
        provider_call_store=provider_calls,
    )


@pytest.mark.anyio
async def test_expired_pausing_run_is_checkpointed_by_replacement_worker(sqlite_session) -> None:
    store, first = await _claimed_run(sqlite_session)
    first_epoch = first.lease_epoch
    events = EventStore(sqlite_session)
    pausing = await store.transition_run(
        first.id,
        expected_state_version=first.state_version,
        lease_epoch=None,
        status="pausing",
        event_type="progress",
        event_payload={"status": "pausing"},
    )
    await sqlite_session.execute(
        update(WorkflowRun)
        .where(WorkflowRun.id == pausing.id)
        .values(lease_expires_at=utcnow() - timedelta(seconds=1))
    )
    await sqlite_session.commit()

    replacement = await store.claim_next("worker-b", lease_seconds=60)
    assert replacement is not None
    assert replacement.lease_epoch == first_epoch + 1
    await sqlite_session.commit()

    result = await _engine(sqlite_session, _CONTROL_DEFINITION, store, events).execute(
        replacement.id,
        lease_owner="worker-b",
    )
    assert result.status == "paused"
    checkpoints = await CheckpointStore(sqlite_session).list_for_run(replacement.id)
    assert len(checkpoints) == 1
    assert checkpoints[0].lease_epoch == replacement.lease_epoch
    assert [event.sequence for event in await events.replay_events(replacement.id)] == [1, 2]
    assert (await store.get_run(replacement.id)).status == "paused"


@pytest.mark.anyio
async def test_cancel_intent_is_idempotent_and_replacement_worker_converges(sqlite_session) -> None:
    store, first = await _claimed_run(sqlite_session)
    events = EventStore(sqlite_session)
    running = await store.transition_run(
        first.id,
        expected_state_version=first.state_version,
        lease_epoch=first.lease_epoch,
        status="running",
        event_type="progress",
        event_payload={"status": "running"},
    )
    await sqlite_session.commit()
    cancelling = await store.request_cancel(running.id)
    repeated = await store.request_cancel(running.id)
    assert cancelling.status == repeated.status == "cancelling"
    assert cancelling.state_version == repeated.state_version
    assert [event.sequence for event in await events.replay_events(running.id)] == [1, 2]

    await sqlite_session.execute(
        update(WorkflowRun)
        .where(WorkflowRun.id == running.id)
        .values(lease_expires_at=utcnow() - timedelta(seconds=1))
    )
    await sqlite_session.commit()
    replacement = await store.claim_next("worker-b", lease_seconds=60)
    assert replacement is not None
    await sqlite_session.commit()

    result = await _engine(sqlite_session, _CONTROL_DEFINITION, store, events).execute(
        replacement.id,
        lease_owner="worker-b",
    )
    assert result.status == "cancelled"
    replay = await events.replay_events(replacement.id)
    assert [event.sequence for event in replay] == [1, 2, 3]
    assert replay[-1].event_type == "done"
    assert replay[-1].payload["status"] == "cancelled"


@pytest.mark.anyio
async def test_unknown_provider_is_fenced_then_requires_explicit_approval(sqlite_session) -> None:
    store, first = await _claimed_run(sqlite_session)
    running = await store.transition_run(
        first.id,
        expected_state_version=first.state_version,
        lease_epoch=first.lease_epoch,
        status="running",
    )
    calls = ProviderCallStore(sqlite_session, commit_started_calls=False)
    old_epoch = running.lease_epoch
    call = await calls.start(
        workflow_run_id=running.id,
        attempt=1,
        stream_attempt=1,
        provider="deepseek",
        model="deepseek-v4-pro",
        provider_policy_version="provider-v1",
        request_digest="u" * 64,
        lease_epoch=old_epoch,
    )
    await sqlite_session.execute(
        update(WorkflowRun)
        .where(WorkflowRun.id == running.id)
        .values(lease_expires_at=utcnow() - timedelta(seconds=1))
    )
    await sqlite_session.commit()
    replacement = await store.claim_next("worker-b", lease_seconds=60)
    assert replacement is not None
    await sqlite_session.commit()

    with pytest.raises(LeaseFencedError):
        await calls.complete(
            call.id,
            outcome="success",
            response_ref={"candidate_output": {"content": "stale"}},
            lease_epoch=old_epoch,
        )

    result = await RecoveryService(store, CheckpointStore(sqlite_session), calls).prepare_resume(
        replacement,
        Lease.from_run(replacement),
    )
    await sqlite_session.commit()
    assert result.action == "waiting_approval"
    assert result.unknown_provider_call_ids == (str(call.id),)
    assert (await calls.get(call.id)).status == "unknown"
    assert (await store.get_run(replacement.id)).status == "waiting_approval"


@pytest.mark.anyio
async def test_completed_provider_candidate_is_reused_after_worker_crash(sqlite_session) -> None:
    store, first = await _claimed_run(
        sqlite_session,
        workflow_name=_RECOVERY_DEFINITION.name,
    )
    events = EventStore(sqlite_session)
    running = await store.transition_run(
        first.id,
        expected_state_version=first.state_version,
        lease_epoch=first.lease_epoch,
        status="running",
    )
    step = await store.create_step_attempt(
        workflow_run_id=running.id,
        node_id="producer",
        attempt=1,
        agent_name="test_agent",
        skill_name="TestSkill",
        agent_run_id=uuid4(),
        lease_epoch=running.lease_epoch,
    )
    step = await store.transition_step_attempt(
        step.id,
        expected_state_version=step.state_version,
        lease_epoch=running.lease_epoch,
        status="running",
    )
    calls = ProviderCallStore(sqlite_session, commit_started_calls=False)
    call = await calls.start(
        workflow_run_id=running.id,
        step_attempt_id=step.id,
        agent_run_id=step.agent_run_id,
        attempt=1,
        stream_attempt=1,
        provider="deepseek",
        model="deepseek-v4-pro",
        provider_policy_version="provider-v1",
        request_digest="c" * 64,
        lease_epoch=running.lease_epoch,
    )
    candidate = {"content": "strict candidate", "evidence_chunk_ids": [], "quality_score": 0.82}
    await calls.complete(
        call.id,
        outcome="success",
        response_ref={"candidate_output": candidate, "evidence_snapshot_ids": []},
        response_digest="r" * 64,
        lease_epoch=running.lease_epoch,
    )
    await sqlite_session.execute(
        update(WorkflowRun)
        .where(WorkflowRun.id == running.id)
        .values(lease_expires_at=utcnow() - timedelta(seconds=1))
    )
    await sqlite_session.commit()
    replacement = await store.claim_next("worker-b", lease_seconds=60)
    assert replacement is not None
    await sqlite_session.commit()

    recorder = _NoopRecorder()
    skill = SkillDefinition(
        name="TestSkill",
        agent_name="test_agent",
        version=1,
        input_model=_ControlInput,
        output_model=_RecoveredOutput,
        prompt_template="test only",
        evidence_floor=0,
    )
    engine = _engine(
        sqlite_session,
        _RECOVERY_DEFINITION,
        store,
        events,
        recorder=recorder,
        provider_calls=calls,
    )
    engine.skill_catalog = {("test_agent", "TestSkill"): skill}
    state: dict[str, dict[str, Any]] = {}
    attempts: dict[str, int] = {}
    await engine._recover_completed_provider_results(
        replacement,
        _RECOVERY_DEFINITION,
        {"value": "recover"},
        state,
        attempts,
    )

    recovered_step = await store.get_step_attempt(step.id)
    assert recovered_step is not None and recovered_step.status == "succeeded"
    assert recovered_step.lease_epoch == replacement.lease_epoch
    assert recovered_step.output_ref["candidate_output"] == candidate
    assert state["producer"]["provider_call_id"] == str(call.id)
    assert attempts == {"producer": 1}
    assert len(recorder.succeeded) == 1
    assert (await calls.list_started_for_run(replacement.id)) == []
    assert [event.payload.get("recovered_provider_result") for event in await events.replay_events(replacement.id)] == [True]


@pytest.mark.anyio
async def test_outbox_republishes_after_process_crash_between_send_and_mark(sqlite_session) -> None:
    _store, claimed = await _claimed_run(sqlite_session)
    events = EventStore(sqlite_session)
    event = await events.append_event(
        claimed.id,
        "progress",
        {"status": "running"},
        lease_epoch=claimed.lease_epoch,
    )
    await sqlite_session.commit()
    delivered: list[int] = []

    async def crash_after_send(envelope) -> None:
        delivered.append(envelope.sequence)
        raise _SimulatedPublisherCrash()

    crashing = EventOutboxPublisher(sqlite_session, crash_after_send, owner="publisher-a")
    with pytest.raises(_SimulatedPublisherCrash):
        await crashing.publish_once()
    await sqlite_session.rollback()
    await sqlite_session.execute(
        update(WorkflowEvent)
        .where(WorkflowEvent.id == event.id)
        .values(publish_lease_expires_at=utcnow() - timedelta(seconds=1))
    )
    await sqlite_session.commit()

    async def publish_after_recovery(envelope) -> None:
        delivered.append(envelope.sequence)

    recovered = EventOutboxPublisher(sqlite_session, publish_after_recovery, owner="publisher-b")
    assert await recovered.publish_once() == 1
    row = await sqlite_session.get(WorkflowEvent, event.id)
    assert delivered == [1, 1]
    assert row is not None and row.published_at is not None and row.publish_attempts == 2


@pytest.mark.anyio
async def test_artifact_recovery_activates_orphans_without_creating_sse_holes(sqlite_session) -> None:
    _store, claimed = await _claimed_run(sqlite_session)
    storage = _MemoryArtifactStorage()
    saga = ArtifactSaga(sqlite_session, storage)
    recoverable = await saga.stage(
        workflow_run_id=claimed.id,
        step_attempt_id=None,
        agent_run_id=None,
        resource_type="course_doc",
        title="Recoverable",
        content=b"recover me",
        lease_epoch=claimed.lease_epoch,
    )
    interrupted = await saga.stage(
        workflow_run_id=claimed.id,
        step_attempt_id=None,
        agent_run_id=None,
        resource_type="course_doc",
        title="Missing object",
        content=b"orphan me",
        lease_epoch=claimed.lease_epoch,
    )
    storage.objects.pop(interrupted.staging_key)
    await sqlite_session.commit()

    recovered = await ArtifactRecovery(sqlite_session, storage).recover_staging()
    await sqlite_session.commit()
    assert recovered == {"scanned": 2, "activated": 1, "orphaned": 1}
    visible = await EventStore(sqlite_session).replay_events(claimed.id)
    assert [event.sequence for event in visible] == [1, 2]
    assert [event.event_type for event in visible] == ["artifact", "trace"]
    assert visible[1].payload["artifact_recovery"] == "orphaned"
    assert recoverable.storage_object_id != interrupted.storage_object_id


@pytest.mark.anyio
async def test_sse_replay_waits_for_hidden_artifact_prefix_then_recovers_gap(sqlite_session) -> None:
    _store, claimed = await _claimed_run(sqlite_session)
    events = EventStore(sqlite_session)
    first = await events.append_event(claimed.id, "progress", {"status": "running"}, lease_epoch=claimed.lease_epoch)
    hidden = await events.append_event(
        claimed.id,
        "artifact",
        {"resource_id": str(uuid4()), "resource_type": "course_doc"},
        lease_epoch=claimed.lease_epoch,
        publish_ready=False,
    )
    third = await events.append_event(claimed.id, "trace", {"phase": "after_artifact"}, lease_epoch=claimed.lease_epoch)
    await sqlite_session.commit()

    assert [event.sequence for event in await events.replay_events(claimed.id)] == [first.sequence]
    assert await events.mark_publish_ready(hidden.id)
    await sqlite_session.commit()
    assert [event.sequence for event in await events.replay_events(claimed.id)] == [
        first.sequence,
        hidden.sequence,
        third.sequence,
    ]


class _GatewayService:
    def __init__(self, run_id: UUID, *, empty_replays_before_terminal: int) -> None:
        from app.runtime.contracts import EventEnvelope

        self.run_id = run_id
        self.empty_replays_before_terminal = empty_replays_before_terminal
        self.replay_calls = 0
        self.events = (
            EventEnvelope(workflow_run_id=run_id, sequence=1, event_type="progress", payload={"status": "running"}),
            EventEnvelope(workflow_run_id=run_id, sequence=2, event_type="trace", payload={"phase": "postgres_replay"}),
            EventEnvelope(workflow_run_id=run_id, sequence=3, event_type="done", payload={"status": "succeeded"}),
        )

    async def replay(self, _run_id, *, after_sequence: int, **_kwargs):
        self.replay_calls += 1
        if after_sequence == 0:
            return [self.events[0]]
        if self.empty_replays_before_terminal > 0:
            self.empty_replays_before_terminal -= 1
            return []
        return [event for event in self.events if event.sequence > after_sequence]

    async def get(self, _run_id, **_kwargs):
        return SimpleNamespace(status="running")


class _DuplicateHintNotifier:
    async def listen_events(self, _run_id, callback, *, stop_requested) -> None:
        callback("duplicated-hint")
        callback("duplicated-hint")
        while not stop_requested():
            await asyncio.sleep(0.001)


@pytest.mark.anyio
async def test_sse_gateway_replays_postgres_after_lost_or_duplicate_redis_hints() -> None:
    run_id = uuid4()
    service = _GatewayService(run_id, empty_replays_before_terminal=1)
    gateway = WorkflowSSEGateway(
        service,
        notifier=_DuplicateHintNotifier(),
        poll_interval_seconds=0.001,
    )
    streamed = [event async for event in gateway.stream(run_id)]
    assert [event.sequence for event in streamed] == [1, 2, 3]
    assert service.replay_calls >= 3

    no_hint_service = _GatewayService(uuid4(), empty_replays_before_terminal=1)
    no_hint_gateway = WorkflowSSEGateway(no_hint_service, poll_interval_seconds=0.001)
    polled = [event async for event in no_hint_gateway.stream(no_hint_service.run_id)]
    assert [event.sequence for event in polled] == [1, 2, 3]


class _FakePubSub:
    def __init__(self) -> None:
        self.messages: list[dict[str, bytes]] = [{"data": b"queued-run"}]
        self.subscribed: list[str] = []
        self.unsubscribed: list[str] = []
        self.closed = False

    async def subscribe(self, channel: str) -> None:
        self.subscribed.append(channel)

    async def get_message(self, **_kwargs):
        return self.messages.pop(0) if self.messages else None

    async def unsubscribe(self, channel: str) -> None:
        self.unsubscribed.append(channel)

    async def aclose(self) -> None:
        self.closed = True


class _FakeRedisClient:
    def __init__(self, pubsub: _FakePubSub) -> None:
        self._pubsub = pubsub

    def pubsub(self, **_kwargs) -> _FakePubSub:
        return self._pubsub


@pytest.mark.anyio
async def test_redis_listener_is_only_a_wakeup_hint() -> None:
    notifier = RedisRuntimeNotifier("redis://not-used")
    pubsub = _FakePubSub()

    async def fake_client() -> _FakeRedisClient:
        return _FakeRedisClient(pubsub)

    notifier._get_client = fake_client  # type: ignore[method-assign]
    stopped = asyncio.Event()
    received: list[str] = []

    async def receive(payload: str) -> None:
        received.append(payload)
        stopped.set()

    await notifier.listen_runs(receive, stop_requested=stopped.is_set, poll_timeout_seconds=0.001)
    assert received == ["queued-run"]
    assert pubsub.subscribed == [RedisRuntimeNotifier.RUN_CHANNEL]
    assert pubsub.unsubscribed == [RedisRuntimeNotifier.RUN_CHANNEL]
    assert pubsub.closed


@pytest.mark.anyio
async def test_worker_heartbeat_renews_lease_before_a_second_worker_can_claim(tmp_path) -> None:
    database = tmp_path / "runtime-heartbeat.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database}")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            store = RunStore(session)
            run = await store.create_run(
                workflow_name=_CONTROL_DEFINITION.name,
                workflow_version="1",
                workflow_definition_digest="h" * 64,
                catalog_version="catalog-v1",
                provider_policy_version="provider-v1",
                checkpoint_schema_version="checkpoint-v1",
                runtime_build_sha="test",
                mode="fixture",
                input_payload={"value": "heartbeat"},
            )
            await session.commit()
        started = asyncio.Event()
        release = asyncio.Event()

        async def execute_claim(_run, _lease, _session) -> None:
            started.set()
            await release.wait()

        worker = RuntimeWorker(sessions, execute_claim, owner="worker-a", lease_seconds=0.15)
        task = asyncio.create_task(worker.run_once())
        try:
            await asyncio.wait_for(started.wait(), timeout=2)
            await asyncio.sleep(0.19)
            async with sessions() as observer:
                current = await RunStore(observer).get_run(run.id)
                assert current is not None and current.lease_owner == "worker-a"
                assert current.lease_epoch == 1
                assert lease_is_active(current.lease_expires_at)
                assert await RunStore(observer).claim_next("worker-b", lease_seconds=1) is None
                await observer.commit()
        finally:
            release.set()
            outcome = await asyncio.gather(task, return_exceptions=True)
        assert outcome == [True]
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_resume_and_explicit_retry_release_obsolete_leases_before_requeue(tmp_path) -> None:
    database = tmp_path / "runtime-requeue.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database}")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        registry = WorkflowRegistry()
        registry.register(_CONTROL_DEFINITION)
        service = WorkflowApplicationService(sessions, workflow_registry=registry)

        async with sessions() as session:
            store = RunStore(session)
            paused_root = await store.create_run(
                workflow_name=_CONTROL_DEFINITION.name,
                workflow_version="1",
                workflow_definition_digest="p" * 64,
                catalog_version="catalog-v1",
                provider_policy_version="provider-v1",
                checkpoint_schema_version="checkpoint-v1",
                runtime_build_sha="test",
                mode="fixture",
                input_payload={"value": "resume"},
            )
            await session.commit()
            paused_claim = await store.claim_next("worker-a", lease_seconds=60)
            assert paused_claim is not None
            paused = await store.transition_run(
                paused_claim.id,
                expected_state_version=paused_claim.state_version,
                lease_epoch=None,
                status="paused",
            )
            await session.commit()

        assert (await service.resume(paused.id)).status == "queued"
        async with sessions() as session:
            resumed = await RunStore(session).get_run(paused.id)
            assert resumed is not None and resumed.lease_owner is None and resumed.lease_expires_at is None
            assert await RunStore(session).claim_next("worker-b", lease_seconds=60) is not None
            await session.commit()

        async with sessions() as session:
            store = RunStore(session)
            retry_root = await store.create_run(
                workflow_name=_CONTROL_DEFINITION.name,
                workflow_version="1",
                workflow_definition_digest="r" * 64,
                catalog_version="catalog-v1",
                provider_policy_version="provider-v1",
                checkpoint_schema_version="checkpoint-v1",
                runtime_build_sha="test",
                mode="fixture",
                input_payload={"value": "retry"},
            )
            await session.commit()
            retry_claim = await store.claim_next("worker-a", lease_seconds=60)
            assert retry_claim is not None
            running = await store.transition_run(
                retry_claim.id,
                expected_state_version=retry_claim.state_version,
                lease_epoch=retry_claim.lease_epoch,
                status="running",
            )
            calls = ProviderCallStore(session, commit_started_calls=False)
            call = await calls.start(
                workflow_run_id=running.id,
                attempt=1,
                stream_attempt=1,
                provider="deepseek",
                model="deepseek-v4-pro",
                provider_policy_version="provider-v1",
                request_digest="x" * 64,
                lease_epoch=running.lease_epoch,
            )
            await calls.mark_unknown(call.id, lease_epoch=running.lease_epoch)
            waiting = await store.transition_run(
                running.id,
                expected_state_version=running.state_version,
                lease_epoch=None,
                status="waiting_approval",
            )
            await session.commit()

        assert (await service.retry(waiting.id)).status == "queued"
        async with sessions() as session:
            retried = await RunStore(session).get_run(waiting.id)
            assert retried is not None and retried.lease_owner is None and retried.lease_expires_at is None
            assert await RunStore(session).claim_next("worker-b", lease_seconds=60) is not None
            await session.commit()
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_keyed_start_and_cancel_are_idempotent(tmp_path) -> None:
    database = tmp_path / "runtime-idempotency.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database}")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        registry = WorkflowRegistry()
        registry.register(_CONTROL_DEFINITION)
        service = WorkflowApplicationService(sessions, workflow_registry=registry)
        user_id = str(uuid4())
        request = WorkflowRunStartRequest(
            workflow=_CONTROL_DEFINITION.name,
            user_id=user_id,
            input={"value": "same request"},
            mode="fixture",
        )

        with pytest.raises(WorkflowApplicationError, match="Idempotency-Key") as missing:
            await service.start(request, actor_user_id=user_id)
        assert missing.value.code == "IDEMPOTENCY_KEY_REQUIRED"

        first = await service.start(request, idempotency_key="same-root", actor_user_id=user_id)
        second = await service.start(request, idempotency_key="same-root", actor_user_id=user_id)
        assert first.run_id == second.run_id

        changed = request.model_copy(update={"input": {"value": "different request"}})
        with pytest.raises(WorkflowApplicationError) as reuse:
            await service.start(changed, idempotency_key="same-root", actor_user_id=user_id)
        assert reuse.value.code == "IDEMPOTENCY_KEY_REUSED"

        first_cancel = await service.cancel(first.run_id, actor_user_id=user_id)
        repeated_cancel = await service.cancel(first.run_id, actor_user_id=user_id)
        assert first_cancel.status == repeated_cancel.status == "cancelling"
        async with sessions() as session:
            replay = await EventStore(session).replay_events(first.run_id)
            assert [event.sequence for event in replay] == [1, 2]
            assert replay[-1].payload["cancel_requested"] is True
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_supervisor_blocks_incompatible_checkpoint_before_resuming_effects(
    sqlite_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = RunStore(sqlite_session)
    definition = _CONTROL_DEFINITION
    run = await store.create_run(
        workflow_name=definition.name,
        workflow_version=str(definition.version),
        workflow_definition_digest=definition.definition_digest,
        catalog_version=definition.catalog_version,
        provider_policy_version=definition.provider_policy_version,
        checkpoint_schema_version=definition.checkpoint_schema_version,
        runtime_build_sha="semantic-test",
        mode="fixture",
        input_payload={"value": "semantic recovery"},
    )
    await sqlite_session.commit()
    first = await store.claim_next("worker-a", lease_seconds=60)
    assert first is not None
    running = await store.transition_run(
        first.id,
        expected_state_version=first.state_version,
        lease_epoch=first.lease_epoch,
        status="running",
    )
    await CheckpointStore(sqlite_session).save(
        workflow_run_id=running.id,
        lease_epoch=running.lease_epoch,
        checkpoint_schema_version="checkpoint-v0",
        state_json={"completed": []},
    )
    await sqlite_session.execute(
        update(WorkflowRun)
        .where(WorkflowRun.id == running.id)
        .values(lease_expires_at=utcnow() - timedelta(seconds=1))
    )
    await sqlite_session.commit()
    replacement = await store.claim_next("worker-b", lease_seconds=60)
    assert replacement is not None
    await sqlite_session.commit()

    registry = WorkflowRegistry()
    registry.register(definition)

    class _Engine:
        workflow_registry = registry
        runtime_build_sha = "semantic-test"
        executed = False

        async def execute(self, *_args: Any, **_kwargs: Any) -> None:
            self.executed = True

    fake_engine = _Engine()
    monkeypatch.setattr("app.runtime.supervisor.build_runtime_engine", lambda _session: fake_engine)
    supervisor = object.__new__(RuntimeSupervisor)
    await supervisor._execute_claim(replacement, Lease.from_run(replacement), sqlite_session)

    assert fake_engine.executed is False
    blocked = await store.get_run(replacement.id)
    assert blocked is not None and blocked.status == "blocked"
    replay = await EventStore(sqlite_session).replay_events(replacement.id)
    assert replay[-1].event_type == "error"
    assert replay[-1].payload["code"] == "SEMANTIC_VERSION_INCOMPATIBLE"
