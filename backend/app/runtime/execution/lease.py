# Status: real

"""PostgreSQL lease ownership and fencing-token helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.db.models.workflow_runtime import WorkflowRun
from app.runtime.persistence.run_store import RunStore


@dataclass(frozen=True, slots=True)
class Lease:
    workflow_run_id: UUID
    owner: str
    epoch: int
    expires_at: datetime | None

    @classmethod
    def from_run(cls, run: WorkflowRun) -> "Lease":
        if not run.lease_owner or run.lease_epoch < 1:
            raise ValueError("claimed run has no active lease")
        return cls(
            workflow_run_id=run.id,
            owner=run.lease_owner,
            epoch=run.lease_epoch,
            expires_at=run.lease_expires_at,
        )


class LeaseManager:
    def __init__(self, run_store: RunStore, *, owner: str, lease_seconds: float = 30.0) -> None:
        self.run_store = run_store
        self.owner = owner
        self.lease_seconds = lease_seconds

    async def renew(self, lease: Lease) -> Lease:
        if lease.owner != self.owner:
            raise ValueError("lease owner does not match manager")
        renewed = await self.run_store.renew_lease(
            lease.workflow_run_id,
            self.owner,
            lease.epoch,
            self.lease_seconds,
        )
        return Lease.from_run(renewed)


__all__ = ["Lease", "LeaseManager"]
