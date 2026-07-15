# Status: real

"""SQL-only persistence adapter for the T6 fairness domain."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from app.db.models.education.education_domain import GovernanceAuditEvent
from app.db.models.fairness.fairness import (
    FairnessAlert,
    FairnessAppeal,
    FairnessConsent,
    FairnessGroupAssignment,
    FairnessMetricCell,
    FairnessMetricRun,
    FairnessPolicy,
    FairnessReview,
)
from app.db.models.teaching.teacher_production import (
    Assessment,
    AssessmentAssignment,
    AssessmentGradeDecision,
    AssessmentSubmission,
    AssessmentVersion,
)
from app.repositories.base import BaseRepository


class FairnessRepository(BaseRepository):
    async def get_policy(self, policy_id: UUID) -> FairnessPolicy | None:
        return await self.session.get(FairnessPolicy, policy_id)

    async def get_policy_by_code_version(self, *, code: str, version_no: int) -> FairnessPolicy | None:
        return await self.session.scalar(
            select(FairnessPolicy).where(
                FairnessPolicy.code == code, FairnessPolicy.version_no == version_no
            )
        )

    async def get_active_policy_by_code(self, code: str) -> FairnessPolicy | None:
        return await self.session.scalar(
            select(FairnessPolicy).where(FairnessPolicy.code == code, FairnessPolicy.status == "active")
        )

    async def list_policies(self) -> Sequence[FairnessPolicy]:
        result = await self.session.execute(
            select(FairnessPolicy).order_by(FairnessPolicy.code, FairnessPolicy.version_no.desc())
        )
        return result.scalars().all()

    async def get_consent(
        self, *, user_id: UUID, policy_id: UUID, scope: str
    ) -> FairnessConsent | None:
        return await self.session.scalar(
            select(FairnessConsent).where(
                FairnessConsent.user_id == user_id,
                FairnessConsent.policy_id == policy_id,
                FairnessConsent.scope == scope,
            )
        )

    async def get_live_consent(
        self, *, user_id: UUID, policy_id: UUID, scope: str, now: datetime
    ) -> FairnessConsent | None:
        return await self.session.scalar(
            select(FairnessConsent).where(
                FairnessConsent.user_id == user_id,
                FairnessConsent.policy_id == policy_id,
                FairnessConsent.scope == scope,
                FairnessConsent.status == "granted",
                FairnessConsent.expires_at > now,
            )
        )

    async def list_live_consents(
        self, *, user_ids: Sequence[UUID], policy_id: UUID, scope: str, now: datetime
    ) -> Sequence[FairnessConsent]:
        if not user_ids:
            return []
        result = await self.session.execute(
            select(FairnessConsent).where(
                FairnessConsent.user_id.in_(user_ids),
                FairnessConsent.policy_id == policy_id,
                FairnessConsent.scope == scope,
                FairnessConsent.status == "granted",
                FairnessConsent.expires_at > now,
            )
        )
        return result.scalars().all()

    async def get_group_assignment(
        self, *, user_id: UUID, policy_id: UUID, group_key: str
    ) -> FairnessGroupAssignment | None:
        return await self.session.scalar(
            select(FairnessGroupAssignment).where(
                FairnessGroupAssignment.user_id == user_id,
                FairnessGroupAssignment.policy_id == policy_id,
                FairnessGroupAssignment.group_key == group_key,
            )
        )

    async def list_live_group_assignments(
        self, *, user_ids: Sequence[UUID], policy_id: UUID, now: datetime
    ) -> Sequence[FairnessGroupAssignment]:
        if not user_ids:
            return []
        result = await self.session.execute(
            select(FairnessGroupAssignment).where(
                FairnessGroupAssignment.user_id.in_(user_ids),
                FairnessGroupAssignment.policy_id == policy_id,
                FairnessGroupAssignment.expires_at > now,
            )
        )
        return result.scalars().all()

    async def list_published_grade_rows(
        self, *, assessment_ids: Sequence[UUID]
    ) -> Sequence[
        tuple[
            AssessmentGradeDecision,
            AssessmentSubmission,
            AssessmentAssignment,
            AssessmentVersion,
            Assessment,
        ]
    ]:
        if not assessment_ids:
            return []
        result = await self.session.execute(
            select(
                AssessmentGradeDecision,
                AssessmentSubmission,
                AssessmentAssignment,
                AssessmentVersion,
                Assessment,
            )
            .join(
                AssessmentSubmission,
                AssessmentSubmission.id == AssessmentGradeDecision.submission_id,
            )
            .join(
                AssessmentAssignment,
                AssessmentAssignment.id == AssessmentSubmission.assignment_id,
            )
            .join(
                AssessmentVersion,
                AssessmentVersion.id == AssessmentAssignment.assessment_version_id,
            )
            .join(Assessment, Assessment.id == AssessmentVersion.assessment_id)
            .where(
                Assessment.id.in_(assessment_ids),
                AssessmentGradeDecision.status == "published",
                AssessmentGradeDecision.final_score.is_not(None),
            )
            .order_by(AssessmentGradeDecision.id)
        )
        return result.all()

    async def get_grade_appeal_context(
        self, grade_decision_id: UUID
    ) -> tuple[AssessmentGradeDecision, AssessmentSubmission] | None:
        result = await self.session.execute(
            select(AssessmentGradeDecision, AssessmentSubmission)
            .join(AssessmentSubmission, AssessmentSubmission.id == AssessmentGradeDecision.submission_id)
            .where(AssessmentGradeDecision.id == grade_decision_id)
        )
        return result.one_or_none()

    async def get_metric_run(self, run_id: UUID) -> FairnessMetricRun | None:
        return await self.session.get(FairnessMetricRun, run_id)

    async def list_metric_runs(self) -> Sequence[tuple[FairnessMetricRun, FairnessPolicy]]:
        result = await self.session.execute(
            select(FairnessMetricRun, FairnessPolicy)
            .join(FairnessPolicy, FairnessPolicy.id == FairnessMetricRun.policy_id)
            .order_by(FairnessMetricRun.started_at.desc())
        )
        return result.all()

    async def list_metric_cells(self, run_id: UUID) -> Sequence[FairnessMetricCell]:
        result = await self.session.execute(
            select(FairnessMetricCell)
            .where(FairnessMetricCell.run_id == run_id)
            .order_by(FairnessMetricCell.group_key, FairnessMetricCell.group_value)
        )
        return result.scalars().all()

    async def list_alerts_for_run(self, run_id: UUID) -> Sequence[FairnessAlert]:
        result = await self.session.execute(
            select(FairnessAlert)
            .join(FairnessMetricCell, FairnessMetricCell.id == FairnessAlert.metric_cell_id)
            .where(FairnessMetricCell.run_id == run_id)
            .order_by(FairnessAlert.opened_at.desc())
        )
        return result.scalars().all()

    async def get_alert(self, alert_id: UUID) -> FairnessAlert | None:
        return await self.session.get(FairnessAlert, alert_id)

    async def get_appeal(self, appeal_id: UUID) -> FairnessAppeal | None:
        return await self.session.get(FairnessAppeal, appeal_id)

    async def list_appeals(self) -> Sequence[FairnessAppeal]:
        result = await self.session.execute(
            select(FairnessAppeal).order_by(FairnessAppeal.submitted_at.desc())
        )
        return result.scalars().all()

    async def list_appealable_grade_contexts(
        self, user_id: UUID
    ) -> Sequence[tuple[AssessmentGradeDecision, AssessmentSubmission]]:
        result = await self.session.execute(
            select(AssessmentGradeDecision, AssessmentSubmission)
            .join(AssessmentSubmission, AssessmentSubmission.id == AssessmentGradeDecision.submission_id)
            .where(
                AssessmentSubmission.student_id == user_id,
                AssessmentGradeDecision.status == "published",
                AssessmentGradeDecision.final_score.is_not(None),
            )
            .order_by(AssessmentGradeDecision.published_at.desc())
        )
        return result.all()

    async def create_policy(self, **values: Any) -> FairnessPolicy:
        row = FairnessPolicy(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_metric_run(self, **values: Any) -> FairnessMetricRun:
        row = FairnessMetricRun(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_metric_cell(self, **values: Any) -> FairnessMetricCell:
        row = FairnessMetricCell(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_alert(self, **values: Any) -> FairnessAlert:
        row = FairnessAlert(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_review(self, **values: Any) -> FairnessReview:
        row = FairnessReview(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_appeal(self, **values: Any) -> FairnessAppeal:
        row = FairnessAppeal(id=uuid4(), **values)
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
