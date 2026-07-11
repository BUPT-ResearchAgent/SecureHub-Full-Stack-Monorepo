# Status: real

"""Factory wiring the one RuntimeEngine with PostgreSQL-backed ports."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.actions import WorkflowActionService
from app.runtime.engine import RuntimeEngine
from app.runtime.harness.executor import SkillExecutor
from app.runtime.persistence.checkpoint_store import CheckpointStore
from app.runtime.persistence.event_store import EventStore
from app.runtime.persistence.evidence_snapshot_store import EvidenceSnapshotStore
from app.runtime.persistence.provider_call_store import ProviderCallStore
from app.runtime.persistence.run_store import RunStore
from app.runtime.ports.run_recorder import AgentRunRecorder
from app.runtime.skill_catalog import build_production_skill_catalog
from app.services.workflow_application_service import build_default_workflow_registry


def build_runtime_engine(session: AsyncSession, *, runtime_build_sha: str = "dev") -> RuntimeEngine:
    events = EventStore(session)
    provider_calls = ProviderCallStore(session)
    return RuntimeEngine(
        session=session,
        workflow_registry=build_default_workflow_registry(),
        skill_catalog=build_production_skill_catalog(),
        run_store=RunStore(session, event_store=events),
        event_store=events,
        skill_executor=SkillExecutor(
            evidence_snapshot_store=EvidenceSnapshotStore(session),
            provider_call_store=provider_calls,
        ),
        run_recorder=AgentRunRecorder(session),
        action_handler=WorkflowActionService(session),
        checkpoint_store=CheckpointStore(session),
        provider_call_store=provider_calls,
        runtime_build_sha=runtime_build_sha,
    )


__all__ = ["build_runtime_engine"]
