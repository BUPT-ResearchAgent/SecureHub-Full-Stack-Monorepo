# Status: real

"""SQL-only persistence adapter for T4 signals, suggestions, and messages."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select

from app.db.models.agent.agent_run import AgentRun
from app.db.models.collaboration.collaboration import (
    CourseUpdateDecision,
    CourseUpdateImpact,
    CourseUpdateSuggestion,
    ExternalSignal,
    Message,
    MessageDelivery,
)
from app.db.models.education.education_domain import (
    CourseEnrollment,
    CourseTeacherAssignment,
    GovernanceAuditEvent,
    TeachingClass,
    TeachingClassTeacher,
)
from app.db.models.identity.user import User
from app.db.models.knowledge.course import Course
from app.db.models.knowledge.document import Document
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.db.models.workflow_runtime import WorkflowEvidenceSnapshot
from app.repositories.base import BaseRepository


class CollaborationRepository(BaseRepository):
    async def get_user(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_course(self, course_id: UUID) -> Course | None:
        return await self.session.get(Course, course_id)

    async def get_document(self, document_id: UUID) -> Document | None:
        return await self.session.get(Document, document_id)

    async def get_agent_run(self, agent_run_id: UUID) -> AgentRun | None:
        return await self.session.get(AgentRun, agent_run_id)

    async def get_evidence_snapshot(self, evidence_snapshot_id: UUID) -> WorkflowEvidenceSnapshot | None:
        return await self.session.get(WorkflowEvidenceSnapshot, evidence_snapshot_id)

    async def has_teacher_course_scope(self, *, teacher_id: UUID, course_id: UUID) -> bool:
        value = await self.session.scalar(
            select(CourseTeacherAssignment.id).where(
                CourseTeacherAssignment.teacher_id == teacher_id,
                CourseTeacherAssignment.course_id == course_id,
                CourseTeacherAssignment.status == "active",
            )
        )
        return value is not None

    async def has_teacher_class_scope(self, *, teacher_id: UUID, class_id: UUID, course_id: UUID) -> bool:
        value = await self.session.scalar(
            select(TeachingClass.id)
            .join(
                TeachingClassTeacher,
                TeachingClassTeacher.teaching_class_id == TeachingClass.id,
            )
            .join(
                CourseTeacherAssignment,
                and_(
                    CourseTeacherAssignment.course_id == TeachingClass.course_id,
                    CourseTeacherAssignment.teacher_id == TeachingClassTeacher.teacher_id,
                ),
            )
            .where(
                TeachingClass.id == class_id,
                TeachingClass.course_id == course_id,
                TeachingClass.status == "active",
                TeachingClassTeacher.teacher_id == teacher_id,
                TeachingClassTeacher.status == "active",
                CourseTeacherAssignment.status == "active",
            )
        )
        return value is not None

    async def has_active_enrollment(self, *, user_id: UUID, course_id: UUID) -> bool:
        value = await self.session.scalar(
            select(CourseEnrollment.id).where(
                CourseEnrollment.student_id == user_id,
                CourseEnrollment.course_id == course_id,
                CourseEnrollment.status == "enrolled",
            )
        )
        return value is not None

    async def list_recipient_ids_for_course(self, course_id: UUID) -> list[UUID]:
        result = await self.session.execute(
            select(CourseEnrollment.student_id)
            .where(CourseEnrollment.course_id == course_id, CourseEnrollment.status == "enrolled")
            .order_by(CourseEnrollment.student_id)
        )
        return list(dict.fromkeys(result.scalars().all()))

    async def list_recipient_ids_for_class(self, class_id: UUID) -> list[UUID]:
        result = await self.session.execute(
            select(CourseEnrollment.student_id)
            .where(
                CourseEnrollment.teaching_class_id == class_id,
                CourseEnrollment.status == "enrolled",
            )
            .order_by(CourseEnrollment.student_id)
        )
        return list(dict.fromkeys(result.scalars().all()))

    async def get_external_signal(self, signal_id: UUID) -> ExternalSignal | None:
        return await self.session.get(ExternalSignal, signal_id)

    async def get_external_signal_by_fingerprint(
        self, *, kind: str, source_fingerprint: str
    ) -> ExternalSignal | None:
        return await self.session.scalar(
            select(ExternalSignal).where(
                ExternalSignal.kind == kind,
                ExternalSignal.source_fingerprint == source_fingerprint,
            )
        )

    async def list_external_signals(self, *, limit: int = 50) -> Sequence[ExternalSignal]:
        result = await self.session.execute(
            select(ExternalSignal).order_by(ExternalSignal.ingested_at.desc()).limit(limit)
        )
        return result.scalars().all()

    async def next_suggestion_version(self, *, course_id: UUID, signal_id: UUID) -> int:
        value = await self.session.scalar(
            select(func.max(CourseUpdateSuggestion.version_no)).where(
                CourseUpdateSuggestion.course_id == course_id,
                CourseUpdateSuggestion.signal_id == signal_id,
            )
        )
        return int(value or 0) + 1

    async def get_suggestion(self, suggestion_id: UUID) -> CourseUpdateSuggestion | None:
        return await self.session.get(CourseUpdateSuggestion, suggestion_id)

    async def get_suggestion_decision(self, suggestion_id: UUID) -> CourseUpdateDecision | None:
        return await self.session.scalar(
            select(CourseUpdateDecision).where(CourseUpdateDecision.suggestion_id == suggestion_id)
        )

    async def list_suggestions_for_course(
        self, *, course_id: UUID, limit: int = 100
    ) -> Sequence[CourseUpdateSuggestion]:
        result = await self.session.execute(
            select(CourseUpdateSuggestion)
            .where(CourseUpdateSuggestion.course_id == course_id)
            .order_by(CourseUpdateSuggestion.created_at.desc(), CourseUpdateSuggestion.version_no.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def list_suggestion_impacts(self, suggestion_id: UUID) -> Sequence[CourseUpdateImpact]:
        result = await self.session.execute(
            select(CourseUpdateImpact)
            .where(CourseUpdateImpact.suggestion_id == suggestion_id)
            .order_by(CourseUpdateImpact.impact_type, CourseUpdateImpact.knowledge_node_id)
        )
        return result.scalars().all()

    async def knowledge_node_in_course(self, *, knowledge_node_id: UUID, course_id: UUID) -> KnowledgeNode | None:
        return await self.session.scalar(
            select(KnowledgeNode).where(
                KnowledgeNode.id == knowledge_node_id,
                KnowledgeNode.course_id == course_id,
            )
        )

    async def get_message(self, message_id: UUID) -> Message | None:
        return await self.session.get(Message, message_id)

    async def get_message_by_idempotency(
        self, *, sender_user_id: UUID, idempotency_key: str
    ) -> Message | None:
        return await self.session.scalar(
            select(Message).where(
                Message.sender_user_id == sender_user_id,
                Message.idempotency_key == idempotency_key,
            )
        )

    async def get_delivery(self, *, message_id: UUID, recipient_user_id: UUID) -> MessageDelivery | None:
        return await self.session.scalar(
            select(MessageDelivery).where(
                MessageDelivery.message_id == message_id,
                MessageDelivery.recipient_user_id == recipient_user_id,
            )
        )

    async def list_inbox(self, *, recipient_user_id: UUID, limit: int = 100) -> Sequence[tuple[MessageDelivery, Message]]:
        result = await self.session.execute(
            select(MessageDelivery, Message)
            .join(Message, Message.id == MessageDelivery.message_id)
            .where(MessageDelivery.recipient_user_id == recipient_user_id)
            .order_by(Message.sent_at.desc(), Message.created_at.desc())
            .limit(limit)
        )
        return result.all()

    async def list_outbox(self, *, sender_user_id: UUID, limit: int = 100) -> Sequence[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.sender_user_id == sender_user_id)
            .order_by(Message.sent_at.desc(), Message.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def message_delivery_counts(self, message_id: UUID) -> dict[str, int]:
        result = await self.session.execute(
            select(MessageDelivery.delivery_state, func.count(MessageDelivery.id))
            .where(MessageDelivery.message_id == message_id)
            .group_by(MessageDelivery.delivery_state)
        )
        return {str(state): int(count) for state, count in result.all()}

    async def set_all_deliveries_recalled(self, *, message_id: UUID, recalled_at: datetime) -> int:
        result = await self.session.execute(
            select(MessageDelivery).where(MessageDelivery.message_id == message_id)
        )
        rows = result.scalars().all()
        for row in rows:
            row.delivery_state = "recalled"
            row.recalled_at = recalled_at
        await self.session.flush()
        return len(rows)

    async def create_external_signal(self, **values: Any) -> ExternalSignal:
        row = ExternalSignal(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_suggestion(self, **values: Any) -> CourseUpdateSuggestion:
        row = CourseUpdateSuggestion(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_suggestion_impact(self, **values: Any) -> CourseUpdateImpact:
        row = CourseUpdateImpact(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_suggestion_decision(self, **values: Any) -> CourseUpdateDecision:
        row = CourseUpdateDecision(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_message(self, **values: Any) -> Message:
        row = Message(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_message_deliveries(
        self, *, message_id: UUID, recipient_ids: Sequence[UUID], delivered_at: datetime
    ) -> list[MessageDelivery]:
        rows = [
            MessageDelivery(
                id=uuid4(),
                message_id=message_id,
                recipient_user_id=recipient_id,
                delivery_state="unread",
                delivered_at=delivered_at,
            )
            for recipient_id in recipient_ids
        ]
        self.session.add_all(rows)
        await self.session.flush()
        return rows

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
