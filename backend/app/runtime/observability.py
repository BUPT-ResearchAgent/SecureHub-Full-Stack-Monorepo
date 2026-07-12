# Status: real

"""Queryable runtime metrics and trace-safe operational summaries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.workflow_runtime import (
    WorkflowAuditLog,
    WorkflowEvent,
    WorkflowProviderCall,
    WorkflowRun,
)


class RuntimeMetricsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def snapshot(self, *, workflow_run_id: UUID | str | None = None) -> dict[str, Any]:
        run_filter = []
        if workflow_run_id is not None:
            run_filter = [WorkflowRun.id == UUID(str(workflow_run_id))]
        status_rows = list(
            (
                await self.session.execute(
                    select(WorkflowRun.status, func.count(WorkflowRun.id)).where(*run_filter).group_by(WorkflowRun.status)
                )
            ).all()
        )
        provider_filter = []
        event_filter = []
        audit_filter = []
        if workflow_run_id is not None:
            parsed = UUID(str(workflow_run_id))
            provider_filter = [WorkflowProviderCall.workflow_run_id == parsed]
            event_filter = [WorkflowEvent.workflow_run_id == parsed]
            audit_filter = [WorkflowAuditLog.workflow_run_id == parsed]
        provider_rows = list(
            (
                await self.session.execute(
                    select(WorkflowProviderCall.status, WorkflowProviderCall.outcome, func.count(WorkflowProviderCall.id))
                    .where(*provider_filter)
                    .group_by(WorkflowProviderCall.status, WorkflowProviderCall.outcome)
                )
            ).all()
        )
        unpublished = await self.session.scalar(
            select(func.count(WorkflowEvent.id)).where(
                *event_filter,
                WorkflowEvent.published_at.is_(None),
                WorkflowEvent.publish_ready_at.is_not(None),
            )
        )
        oldest_unpublished = await self.session.scalar(
            select(func.min(WorkflowEvent.created_at)).where(
                *event_filter,
                WorkflowEvent.published_at.is_(None),
                WorkflowEvent.publish_ready_at.is_not(None),
            )
        )
        trace_events = await self.session.scalar(
            select(func.count(WorkflowEvent.id)).where(*event_filter, WorkflowEvent.event_type == "trace")
        )
        audit_events = await self.session.scalar(select(func.count(WorkflowAuditLog.id)).where(*audit_filter))
        lag_seconds = None
        if oldest_unpublished is not None:
            oldest = (
                oldest_unpublished.replace(tzinfo=timezone.utc)
                if oldest_unpublished.tzinfo is None
                else oldest_unpublished
            )
            lag_seconds = max(0.0, (datetime.now(timezone.utc) - oldest).total_seconds())
        return {
            "runs_by_status": {str(status): int(count) for status, count in status_rows},
            "provider_calls": {
                f"{status}:{outcome or 'none'}": int(count)
                for status, outcome, count in provider_rows
            },
            "unknown_provider_calls": sum(
                int(count) for status, _outcome, count in provider_rows if str(status) == "unknown"
            ),
            "outbox_unpublished": int(unpublished or 0),
            "outbox_lag_seconds": lag_seconds,
            "trace_events": int(trace_events or 0),
            "audit_events": int(audit_events or 0),
        }


__all__ = ["RuntimeMetricsService"]
