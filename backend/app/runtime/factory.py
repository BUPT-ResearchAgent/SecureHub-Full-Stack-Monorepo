# Status: real

"""Factory wiring the one RuntimeEngine with PostgreSQL-backed ports."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
from app.services.provider_credential_resolver import ProviderCredentialResolver


def _runtime_provider_resolver(context):
    """Build a provider for this call; no mutable global key selection exists."""
    provider = context.provider_selection.requested_provider or "xfyun"
    return ProviderCredentialResolver().resolve(
        provider=provider,
        user_id=context.user_id,
        credential_id=context.provider_credential_id,
        model=context.provider_selection.requested_model,
    )


def _runtime_fallback_provider_resolver(provider: str, context):
    # A root-frozen credential only applies to the provider it was selected
    # for. ProviderPolicy fallbacks retain their server-side environment key.
    selected = context.provider_selection.requested_provider
    credential_id = context.provider_credential_id if provider == selected else None
    return ProviderCredentialResolver().resolve(
        provider=provider,
        user_id=context.user_id,
        credential_id=credential_id,
    )


def build_runtime_engine(
    session: AsyncSession,
    *,
    runtime_build_sha: str = "dev",
    parallel_sessionmaker: async_sessionmaker[AsyncSession] | None = None,
) -> RuntimeEngine:
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
            provider_resolver=_runtime_provider_resolver,
            fallback_provider_resolver=_runtime_fallback_provider_resolver,
        ),
        run_recorder=AgentRunRecorder(session),
        action_handler=WorkflowActionService(session),
        checkpoint_store=CheckpointStore(session),
        provider_call_store=provider_calls,
        runtime_build_sha=runtime_build_sha,
        parallel_sessionmaker=parallel_sessionmaker,
    )


__all__ = ["build_runtime_engine"]
