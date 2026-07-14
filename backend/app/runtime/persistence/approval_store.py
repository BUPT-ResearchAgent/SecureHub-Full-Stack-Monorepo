# Status: real

"""Durable HITL approvals and control-plane audit facts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.workflow_runtime import WorkflowApproval, WorkflowAuditLog
from app.runtime.persistence.common import as_uuid, mapping


class ApprovalNotFoundError(KeyError):
    pass


class ApprovalStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def request(
        self,
        *,
        workflow_run_id: UUID | str,
        kind: str,
        node_id: str | None = None,
        request: dict[str, Any] | None = None,
        requested_by: str | None = None,
    ) -> WorkflowApproval:
        run_id = as_uuid(workflow_run_id, field="workflow_run_id")
        existing = await self.session.scalar(
            select(WorkflowApproval)
            .where(
                WorkflowApproval.workflow_run_id == run_id,
                WorkflowApproval.kind == str(kind),
                WorkflowApproval.node_id == node_id,
                WorkflowApproval.status == "pending",
            )
            .order_by(WorkflowApproval.created_at.desc())
            .limit(1)
        )
        if existing is not None:
            return existing
        row = WorkflowApproval(
            workflow_run_id=run_id,
            node_id=node_id,
            kind=str(kind),
            status="pending",
            request=mapping(request or {}, field="approval_request"),
            requested_by=requested_by,
        )
        self.session.add(row)
        await self.session.flush()
        await self.audit(run_id, action="approval_requested", node_id=node_id, details={"kind": str(kind)})
        return row

    async def decide(
        self,
        approval_id: UUID | str,
        *,
        approved: bool,
        actor_id: UUID | str | None,
        decision: dict[str, Any] | None = None,
    ) -> WorkflowApproval:
        identifier = as_uuid(approval_id, field="approval_id")
        row = await self.session.get(WorkflowApproval, identifier)
        if row is None:
            raise ApprovalNotFoundError(str(identifier))
        if row.status != "pending":
            return row
        now = datetime.now(timezone.utc)
        target = "approved" if approved else "rejected"
        result = await self.session.execute(
            update(WorkflowApproval)
            .where(WorkflowApproval.id == identifier, WorkflowApproval.status == "pending")
            .values(
                status=target,
                decision=mapping(decision or {}, field="approval_decision"),
                decided_by=str(actor_id) if actor_id is not None else None,
                decided_at=now,
                updated_at=now,
            )
            .returning(WorkflowApproval)
        )
        resolved = result.scalar_one_or_none() or row
        await self.audit(
            resolved.workflow_run_id,
            action="approval_approved" if approved else "approval_rejected",
            actor_id=actor_id,
            node_id=resolved.node_id,
            details={"approval_id": str(resolved.id), "kind": resolved.kind},
        )
        await self.session.flush()
        return resolved

    async def get(self, approval_id: UUID | str) -> WorkflowApproval:
        identifier = as_uuid(approval_id, field="approval_id")
        row = await self.session.get(WorkflowApproval, identifier)
        if row is None:
            raise ApprovalNotFoundError(str(identifier))
        return row

    async def has_approved(
        self,
        *,
        workflow_run_id: UUID | str,
        kind: str,
        node_id: str | None = None,
    ) -> bool:
        row = await self.session.scalar(
            select(WorkflowApproval.id).where(
                WorkflowApproval.workflow_run_id == as_uuid(workflow_run_id, field="workflow_run_id"),
                WorkflowApproval.kind == str(kind),
                WorkflowApproval.node_id == node_id,
                WorkflowApproval.status == "approved",
            )
        )
        return row is not None

    async def list_for_run(self, workflow_run_id: UUID | str) -> list[WorkflowApproval]:
        rows = await self.session.execute(
            select(WorkflowApproval)
            .where(WorkflowApproval.workflow_run_id == as_uuid(workflow_run_id, field="workflow_run_id"))
            .order_by(WorkflowApproval.created_at.asc())
        )
        return list(rows.scalars().all())

    async def audit(
        self,
        workflow_run_id: UUID | str,
        *,
        action: str,
        actor_id: UUID | str | None = None,
        node_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> WorkflowAuditLog:
        row = WorkflowAuditLog(
            workflow_run_id=as_uuid(workflow_run_id, field="workflow_run_id"),
            action=str(action),
            actor_id=str(actor_id) if actor_id is not None else None,
            node_id=node_id,
            details=mapping(details or {}, field="audit_details"),
        )
        self.session.add(row)
        await self.session.flush()
        return row


__all__ = ["ApprovalNotFoundError", "ApprovalStore"]
