# Status: real

"""SQL-only persistence adapter for frozen benchmark datasets and runs."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from app.db.models.benchmark.benchmark import (
    BenchmarkCaseResult,
    BenchmarkDatasetVersion,
    BenchmarkRun,
)
from app.db.models.education.education_domain import GovernanceAuditEvent
from app.repositories.base import BaseRepository


class BenchmarkRepository(BaseRepository):
    async def get_dataset(self, dataset_id: UUID) -> BenchmarkDatasetVersion | None:
        return await self.session.get(BenchmarkDatasetVersion, dataset_id)

    async def get_dataset_by_kind_version(
        self, *, kind: str, semantic_version: str
    ) -> BenchmarkDatasetVersion | None:
        return await self.session.scalar(
            select(BenchmarkDatasetVersion).where(
                BenchmarkDatasetVersion.kind == kind,
                BenchmarkDatasetVersion.semantic_version == semantic_version,
            )
        )

    async def list_datasets(self) -> Sequence[BenchmarkDatasetVersion]:
        result = await self.session.execute(
            select(BenchmarkDatasetVersion).order_by(
                BenchmarkDatasetVersion.kind, BenchmarkDatasetVersion.semantic_version.desc()
            )
        )
        return result.scalars().all()

    async def get_run(self, run_id: UUID) -> BenchmarkRun | None:
        return await self.session.get(BenchmarkRun, run_id)

    async def list_case_results(self, run_id: UUID) -> Sequence[BenchmarkCaseResult]:
        result = await self.session.execute(
            select(BenchmarkCaseResult)
            .where(BenchmarkCaseResult.run_id == run_id)
            .order_by(BenchmarkCaseResult.case_key)
        )
        return result.scalars().all()

    async def create_dataset(self, **values: Any) -> BenchmarkDatasetVersion:
        row = BenchmarkDatasetVersion(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_run(self, **values: Any) -> BenchmarkRun:
        row = BenchmarkRun(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_case_result(self, **values: Any) -> BenchmarkCaseResult:
        row = BenchmarkCaseResult(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def write_audit(
        self,
        *,
        actor_user_id: UUID,
        action: str,
        object_type: str,
        object_id: UUID,
        reason: str | None,
        result_status: str,
        metadata: dict[str, Any],
    ) -> GovernanceAuditEvent:
        row = GovernanceAuditEvent(
            id=uuid4(),
            actor_user_id=actor_user_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            reason=reason,
            result_status=result_status,
            request_id=None,
            metadata_=metadata,
            created_at=datetime.now(UTC),
        )
        self.session.add(row)
        await self.session.flush()
        return row
