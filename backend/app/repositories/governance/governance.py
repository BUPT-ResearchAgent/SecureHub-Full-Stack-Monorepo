# Status: real

"""SQL-only persistence adapter for T4 administrator governance."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.db.models.collaboration.collaboration import CourseUpdateSuggestion, Message, MessageDelivery
from app.db.models.education.education_domain import (
    CourseEnrollment,
    GovernanceAuditEvent,
    TeachingClass,
)
from app.db.models.governance.governance import (
    CourseResourceGovernance,
    KpiDefinition,
    RoleDefinition,
    UserRoleGrant,
)
from app.db.models.identity.user import User
from app.db.models.knowledge.course import Course
from app.db.models.knowledge.document import Document
from app.db.models.teaching.teacher_production import CourseAssetGovernance, CourseDocumentBinding, AssessmentGradeDecision
from app.repositories.base import BaseRepository


class GovernanceRepository(BaseRepository):
    async def get_user(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def list_users(self) -> Sequence[User]:
        result = await self.session.execute(select(User).order_by(User.display_name, User.email))
        return result.scalars().all()

    async def get_active_role_by_code(self, code: str) -> RoleDefinition | None:
        return await self.session.scalar(
            select(RoleDefinition).where(RoleDefinition.code == code, RoleDefinition.status == "active")
        )

    async def get_role(self, role_id: UUID) -> RoleDefinition | None:
        return await self.session.get(RoleDefinition, role_id)

    async def get_role_grant(self, grant_id: UUID) -> UserRoleGrant | None:
        return await self.session.get(UserRoleGrant, grant_id)

    async def get_active_grant(self, *, user_id: UUID, role_id: UUID) -> UserRoleGrant | None:
        return await self.session.scalar(
            select(UserRoleGrant).where(
                UserRoleGrant.user_id == user_id,
                UserRoleGrant.role_id == role_id,
                UserRoleGrant.status == "active",
            )
        )

    async def has_active_role(self, *, user_id: UUID, role_code: str) -> bool:
        value = await self.session.scalar(
            select(UserRoleGrant.id)
            .join(RoleDefinition, RoleDefinition.id == UserRoleGrant.role_id)
            .where(
                UserRoleGrant.user_id == user_id,
                UserRoleGrant.status == "active",
                RoleDefinition.code == role_code,
                RoleDefinition.status == "active",
            )
        )
        return value is not None

    async def list_role_codes_by_user(self) -> dict[UUID, list[str]]:
        result = await self.session.execute(
            select(UserRoleGrant.user_id, RoleDefinition.code)
            .join(RoleDefinition, RoleDefinition.id == UserRoleGrant.role_id)
            .where(UserRoleGrant.status == "active", RoleDefinition.status == "active")
            .order_by(RoleDefinition.code)
        )
        grouped: dict[UUID, list[str]] = {}
        for user_id, code in result.all():
            grouped.setdefault(user_id, []).append(code)
        return grouped

    async def count_active_role(self, code: str) -> int:
        value = await self.session.scalar(
            select(func.count(UserRoleGrant.id))
            .join(RoleDefinition, RoleDefinition.id == UserRoleGrant.role_id)
            .where(
                UserRoleGrant.status == "active",
                RoleDefinition.status == "active",
                RoleDefinition.code == code,
            )
        )
        return int(value or 0)

    async def list_active_kpi_definitions(self) -> Sequence[KpiDefinition]:
        result = await self.session.execute(
            select(KpiDefinition)
            .where(KpiDefinition.status == "active")
            .order_by(KpiDefinition.code, KpiDefinition.version_no.desc())
        )
        return result.scalars().all()

    async def get_asset_context(
        self, asset_id: UUID
    ) -> tuple[CourseAssetGovernance, CourseDocumentBinding, Document, Course] | None:
        result = await self.session.execute(
            select(CourseAssetGovernance, CourseDocumentBinding, Document, Course)
            .join(CourseDocumentBinding, CourseDocumentBinding.id == CourseAssetGovernance.binding_id)
            .join(Document, Document.id == CourseDocumentBinding.document_id)
            .join(Course, Course.id == CourseDocumentBinding.course_id)
            .where(CourseAssetGovernance.id == asset_id)
        )
        return result.one_or_none()

    async def get_resource_governance(self, asset_id: UUID) -> CourseResourceGovernance | None:
        return await self.session.scalar(
            select(CourseResourceGovernance).where(CourseResourceGovernance.asset_id == asset_id)
        )

    async def list_resource_contexts(
        self,
    ) -> Sequence[tuple[CourseAssetGovernance, CourseDocumentBinding, Document, Course, CourseResourceGovernance | None]]:
        result = await self.session.execute(
            select(CourseAssetGovernance, CourseDocumentBinding, Document, Course, CourseResourceGovernance)
            .join(CourseDocumentBinding, CourseDocumentBinding.id == CourseAssetGovernance.binding_id)
            .join(Document, Document.id == CourseDocumentBinding.document_id)
            .join(Course, Course.id == CourseDocumentBinding.course_id)
            .outerjoin(CourseResourceGovernance, CourseResourceGovernance.asset_id == CourseAssetGovernance.id)
            .order_by(Course.code, CourseAssetGovernance.updated_at.desc())
        )
        return result.all()

    async def count_kpi(self, *, query_key: str, window_start: datetime) -> int:
        if query_key == "active_teaching_classes":
            value = await self.session.scalar(
                select(func.count(TeachingClass.id)).where(TeachingClass.status == "active")
            )
        elif query_key == "enrolled_students":
            value = await self.session.scalar(
                select(func.count(CourseEnrollment.id)).where(CourseEnrollment.status == "enrolled")
            )
        elif query_key == "published_grades":
            value = await self.session.scalar(
                select(func.count(AssessmentGradeDecision.id)).where(
                    AssessmentGradeDecision.status == "published"
                )
            )
        elif query_key == "pending_course_updates":
            value = await self.session.scalar(
                select(func.count(CourseUpdateSuggestion.id)).where(
                    CourseUpdateSuggestion.status == "pending_teacher_decision"
                )
            )
        elif query_key == "sent_messages_7d":
            value = await self.session.scalar(
                select(func.count(Message.id)).where(
                    Message.status.in_(("sent", "partially_delivered")),
                    Message.sent_at.is_not(None),
                    Message.sent_at >= window_start,
                )
            )
        elif query_key == "unread_deliveries":
            value = await self.session.scalar(
                select(func.count(MessageDelivery.id)).where(MessageDelivery.delivery_state == "unread")
            )
        else:
            raise ValueError(f"unsupported KPI query key: {query_key}")
        return int(value or 0)

    async def create_role_definition(self, **values: Any) -> RoleDefinition:
        row = RoleDefinition(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_role_grant(self, **values: Any) -> UserRoleGrant:
        row = UserRoleGrant(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_resource_governance(self, **values: Any) -> CourseResourceGovernance:
        row = CourseResourceGovernance(id=uuid4(), **values)
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
        request_id: str | None,
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
            request_id=request_id,
            metadata_=metadata,
            created_at=datetime.now(UTC),
        )
        self.session.add(row)
        await self.session.flush()
        return row
