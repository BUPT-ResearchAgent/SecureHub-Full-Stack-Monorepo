# Status: real

"""Focused durable Runtime fault-injection coverage.

These tests use SQLite only for fast CI. PostgreSQL is still the production
truth; the same conditional updates exercise fencing and outbox semantics.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import update

from app.db.models.workflow_runtime import WorkflowEvent, WorkflowRun
from app.runtime.artifacts import ArtifactCleanup, ArtifactRecovery, ArtifactSaga
from app.runtime.contracts import RuntimeSemanticVersion
from app.runtime.execution.lease import Lease
from app.runtime.execution.recovery import RecoveryService
from app.runtime.persistence import (
    CheckpointStore,
    EventOutboxPublisher,
    EventStore,
    LeaseFencedError,
    ProviderCallStore,
    RunStore,
)
from app.runtime.persistence.common import utcnow
from app.runtime.versioning import CheckpointMigrationRegistry, CompatibilityPolicy


class _MemoryArtifactStorage:
    provider_name = "memory"
    bucket = "test"

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


async def _claimed_run(sqlite_session):
    store = RunStore(sqlite_session)
    run = await store.create_run(
        {
            "workflow_name": "resource_generate_v1",
            "workflow_version": "1",
            "workflow_definition_digest": "a" * 64,
            "catalog_version": "catalog-v1",
            "provider_policy_version": "provider-v1",
            "checkpoint_schema_version": "checkpoint-v1",
            "runtime_build_sha": "test",
            "mode": "real",
            "input_payload": {"topic": "secure coding"},
        }
    )
    await sqlite_session.commit()
    claimed = await store.claim_next("worker-a", lease_seconds=60)
    assert claimed is not None
    await sqlite_session.commit()
    return store, claimed


@pytest.mark.anyio
async def test_event_sequence_and_outbox_crash_recovery(sqlite_session) -> None:
    store, claimed = await _claimed_run(sqlite_session)
    running = await store.transition_run(
        claimed.id,
        expected_state_version=claimed.state_version,
        lease_epoch=claimed.lease_epoch,
        status="running",
        event_type="progress",
        event_payload={"status": "running", "node_id": "generate"},
    )
    first = (await EventStore(sqlite_session).replay_events(claimed.id))[0]
    second = await EventStore(sqlite_session).append_event(
        claimed.id,
        "trace",
        {"phase": "provider_started"},
        lease_epoch=running.lease_epoch,
    )
    await sqlite_session.commit()

    replay = await EventStore(sqlite_session).replay_events(claimed.id)
    assert [event.sequence for event in replay] == [1, 2]
    assert second.sequence == 2

    outbox = EventStore(sqlite_session)
    first_claim = await outbox.claim_publishable("publisher-a", batch_size=10, lease_seconds=60)
    assert [event.sequence for event in first_claim] == [1]
    await sqlite_session.commit()  # Simulate crash after external publish, before mark_published.

    await sqlite_session.execute(
        update(WorkflowEvent)
        .where(WorkflowEvent.id == first_claim[0].id)
        .values(publish_lease_expires_at=utcnow() - timedelta(seconds=1))
    )
    await sqlite_session.commit()
    replay_claim = await outbox.claim_publishable("publisher-b", batch_size=10, lease_seconds=60)
    assert [event.sequence for event in replay_claim] == [1]
    assert replay_claim[0].publish_attempts == 2
    assert await outbox.mark_published(replay_claim[0].id, owner="publisher-b")
    await sqlite_session.commit()

    next_claim = await outbox.claim_publishable("publisher-b", batch_size=10, lease_seconds=60)
    assert [event.sequence for event in next_claim] == [2]


@pytest.mark.anyio
async def test_stale_worker_is_fenced_from_root_and_step(sqlite_session) -> None:
    store, first = await _claimed_run(sqlite_session)
    first_epoch = first.lease_epoch
    first_state_version = first.state_version
    step = await store.create_step_attempt(
        {
            "workflow_run_id": first.id,
            "node_id": "generate",
            "attempt": 1,
            "lease_epoch": first_epoch,
        }
    )
    await sqlite_session.commit()
    await sqlite_session.execute(
        update(WorkflowRun)
        .where(WorkflowRun.id == first.id)
        .values(lease_expires_at=utcnow() - timedelta(seconds=1))
    )
    await sqlite_session.commit()
    replacement = await store.claim_next("worker-b", lease_seconds=60)
    assert replacement is not None
    assert replacement.lease_epoch == first_epoch + 1
    await sqlite_session.commit()

    with pytest.raises(LeaseFencedError):
        await store.transition_run(
            first.id,
            expected_state_version=first_state_version,
            lease_epoch=first_epoch,
            status="running",
        )
    with pytest.raises(LeaseFencedError):
        await store.transition_step_attempt(
            step.id,
            expected_state_version=step.state_version,
            lease_epoch=first_epoch,
            status="running",
        )


@pytest.mark.anyio
async def test_provider_unknown_outcome_is_durable_and_not_replayed(sqlite_session) -> None:
    _store, claimed = await _claimed_run(sqlite_session)
    calls = ProviderCallStore(sqlite_session, commit_started_calls=False)
    call = await calls.start(
        workflow_run_id=claimed.id,
        attempt=1,
        stream_attempt=1,
        provider="deepseek",
        model="deepseek-v4-pro",
        provider_policy_version="provider-v1",
        request_digest="b" * 64,
    )
    await sqlite_session.commit()

    unknown = await calls.mark_unknown(call.id, error_message="worker process ended during request")
    await sqlite_session.commit()
    assert unknown.status == "unknown"
    assert unknown.outcome is None
    assert await calls.completed_success(call.id) is None
    assert (await calls.list_started_for_run(claimed.id)) == []


@pytest.mark.anyio
async def test_artifact_saga_delays_event_until_active_and_recovers_orphan(sqlite_session) -> None:
    _store, claimed = await _claimed_run(sqlite_session)
    storage = _MemoryArtifactStorage()
    saga = ArtifactSaga(sqlite_session, storage)
    staged = await saga.stage(
        workflow_run_id=claimed.id,
        step_attempt_id=None,
        agent_run_id=None,
        resource_type="course_doc",
        title="Secure coding notes",
        content=b"artifact body",
        resource_content={"kind": "course_doc"},
        lease_epoch=claimed.lease_epoch,
    )
    await sqlite_session.commit()
    assert await EventStore(sqlite_session).replay_events(claimed.id) == []

    activated = await saga.activate(staged.storage_object_id)
    await sqlite_session.commit()
    assert activated.resource_id == staged.resource_id
    visible = await EventStore(sqlite_session).replay_events(claimed.id)
    assert [(event.event_type, event.sequence) for event in visible] == [("artifact", 1)]

    interrupted = await saga.stage(
        workflow_run_id=claimed.id,
        step_attempt_id=None,
        agent_run_id=None,
        resource_type="course_doc",
        title="Interrupted artifact",
        content=b"will disappear",
        lease_epoch=claimed.lease_epoch,
    )
    storage.objects.pop(interrupted.staging_key)
    await sqlite_session.commit()
    recovered = await ArtifactRecovery(sqlite_session, storage).recover_staging()
    assert recovered["orphaned"] == 1
    await sqlite_session.commit()
    cleanup = await ArtifactCleanup(sqlite_session, storage).cleanup_orphaned(
        older_than_seconds=0
    )
    assert cleanup["deleted"] == 1


@pytest.mark.anyio
async def test_unknown_provider_recovery_waits_for_explicit_approval(sqlite_session) -> None:
    store, claimed = await _claimed_run(sqlite_session)
    calls = ProviderCallStore(sqlite_session, commit_started_calls=False)
    call = await calls.start(
        workflow_run_id=claimed.id,
        attempt=1,
        stream_attempt=1,
        provider="deepseek",
        model="deepseek-v4-pro",
        provider_policy_version="provider-v1",
        request_digest="c" * 64,
    )
    await sqlite_session.commit()
    recovery = RecoveryService(store, CheckpointStore(sqlite_session), calls)
    result = await recovery.prepare_resume(claimed, Lease.from_run(claimed))
    await sqlite_session.commit()
    assert result.action == "waiting_approval"
    assert result.unknown_provider_call_ids == (str(call.id),)
    assert (await store.get_run(claimed.id)).status == "waiting_approval"


@pytest.mark.anyio
async def test_semantic_version_policy_allows_only_explicit_checkpoint_migration(sqlite_session) -> None:
    _store, claimed = await _claimed_run(sqlite_session)
    checkpoints = CheckpointStore(sqlite_session)
    checkpoint = await checkpoints.save(
        workflow_run_id=claimed.id,
        lease_epoch=claimed.lease_epoch,
        state_json={"completed_nodes": ["producer"]},
    )
    target = RuntimeSemanticVersion(
        workflow_definition_digest=claimed.workflow_definition_digest,
        catalog_version=claimed.catalog_version,
        provider_policy_version=claimed.provider_policy_version,
        checkpoint_schema_version=claimed.checkpoint_schema_version,
        runtime_build_sha=claimed.runtime_build_sha,
    )
    migrations = CheckpointMigrationRegistry()
    policy = CompatibilityPolicy(migrations)
    assert policy.assess(claimed, checkpoint, target).status == "compatible"
    migrations.register("checkpoint-v1", "checkpoint-v2", lambda state: state)
    migrated_target = target.model_copy(update={"checkpoint_schema_version": "checkpoint-v2"})
    assert policy.assess(claimed, checkpoint, migrated_target).status == "migratable"
    incompatible_target = target.model_copy(update={"catalog_version": "catalog-v2"})
    assert policy.assess(claimed, checkpoint, incompatible_target).status == "incompatible"


@pytest.mark.anyio
async def test_outbox_publisher_delivers_in_sequence(sqlite_session) -> None:
    _store, claimed = await _claimed_run(sqlite_session)
    events = EventStore(sqlite_session)
    await events.append_event(claimed.id, "progress", {"status": "running"}, lease_epoch=claimed.lease_epoch)
    await events.append_event(claimed.id, "trace", {"phase": "next"}, lease_epoch=claimed.lease_epoch)
    await sqlite_session.commit()
    published: list[int] = []

    async def publish(envelope) -> None:
        published.append(envelope.sequence)

    publisher = EventOutboxPublisher(sqlite_session, publish, owner="publisher")
    assert await publisher.publish_once(batch_size=10) == 1
    assert await publisher.publish_once(batch_size=10) == 1
    assert published == [1, 2]
