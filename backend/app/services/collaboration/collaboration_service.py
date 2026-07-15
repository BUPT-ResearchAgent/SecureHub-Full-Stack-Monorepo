# Status: real

"""Authorization-aware orchestration for T4 collaboration and course updates."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.collaboration.collaboration import (
    CourseUpdateDecision,
    CourseUpdateImpact,
    CourseUpdateSuggestion,
    ExternalSignal,
    Message,
    MessageDelivery,
)
from app.db.models.identity.user import User
from app.db.seeds._constants import agent_id, skill_id
from app.repositories.collaboration.collaboration import CollaborationRepository
from app.schemas.collaboration import (
    CourseUpdateDecisionDTO,
    CourseUpdateDecisionRequest,
    CourseUpdateImpactDTO,
    CourseUpdateSuggestionDTO,
    CreateCourseUpdateSuggestionRequest,
    ExternalSignalDTO,
    ExternalSignalIngestRequest,
    MessageDTO,
    MessageInboxDTO,
    MessageInboxItemDTO,
    MessageReadDTO,
    MessageSendRequest,
    RecallMessageRequest,
)

_COURSE_TEACHER_ROLES = {"course_teacher", "hybrid"}
_SIGNAL_SKILL_PROVENANCE = {
    "policy": ("policy_interpreter", "InterpretPolicy"),
    "hot": ("hot_analyst", "AnalyzeHotEvent"),
    "job": ("job_analyst", "AnalyzeJobMarket"),
}
_RECALL_WINDOW = timedelta(minutes=30)
_UNSAFE_MARKERS = ("<script", "javascript:", "<iframe", "data:text/html")


def _as_utc(value: datetime) -> datetime:
    """SQLite can return a naive timestamp for timezone-aware columns."""

    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class CollaborationDomainError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 403) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class CollaborationService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = CollaborationRepository(session)

    async def ingest_external_signal(
        self, *, actor: User, payload: ExternalSignalIngestRequest
    ) -> ExternalSignalDTO:
        self._require_course_teacher(actor)
        document = await self.repository.get_document(payload.source_document_id)
        if document is None:
            raise CollaborationDomainError("SIGNAL_SOURCE_UNTRUSTED", "信号来源文档不存在。", 404)
        run, evidence = await self._require_fixed_agent_evidence(
            kind=payload.kind,
            agent_run_id=payload.agent_run_id,
            evidence_snapshot_id=payload.evidence_snapshot_id,
            source_document_id=payload.source_document_id,
        )
        fingerprint = self._fingerprint(
            {
                "kind": payload.kind,
                "source_document_id": str(payload.source_document_id),
                "agent_run_id": str(run.id),
                "evidence_snapshot_id": str(evidence.id),
                "content_digest": evidence.content_digest,
            }
        )
        existing = await self.repository.get_external_signal_by_fingerprint(
            kind=payload.kind, source_fingerprint=fingerprint
        )
        if existing is not None:
            return await self._signal_dto(existing)

        signal = await self.repository.create_external_signal(
            source_document_id=document.id,
            agent_run_id=run.id,
            evidence_snapshot_id=evidence.id,
            created_by=actor.id,
            kind=payload.kind,
            title=payload.title.strip(),
            source_fingerprint=fingerprint,
            status="validated",
            ingested_at=datetime.now(UTC),
        )
        await self.repository.write_audit(
            actor_user_id=actor.id,
            action="external_signal.ingest",
            object_type="external_signal",
            object_id=signal.id,
            reason="固定 Agent Skill 的 Evidence 已通过来源与关联校验。",
            result_status="succeeded",
            request_id=None,
            metadata={
                "kind": payload.kind,
                "source_document_id": str(document.id),
                "agent_run_id": str(run.id),
                "evidence_snapshot_id": str(evidence.id),
                "source_fingerprint": fingerprint,
            },
        )
        return await self._signal_dto(signal)

    async def list_external_signals(self, *, actor: User) -> list[ExternalSignalDTO]:
        self._require_course_teacher(actor)
        rows = await self.repository.list_external_signals()
        return [await self._signal_dto(row) for row in rows]

    async def create_course_update_suggestion(
        self, *, actor: User, payload: CreateCourseUpdateSuggestionRequest
    ) -> CourseUpdateSuggestionDTO:
        await self._require_teacher_course(actor=actor, course_id=payload.course_id)
        course = await self.repository.get_course(payload.course_id)
        if course is None:
            raise CollaborationDomainError("COURSE_ACCESS_DENIED", "课程不存在或不可访问。", 404)
        signal = await self.repository.get_external_signal(payload.signal_id)
        if signal is None or signal.status != "validated":
            raise CollaborationDomainError(
                "SIGNAL_EVIDENCE_MISSING", "只能基于已验证且有 Evidence 的真实信号生成建议。", 409
            )
        seen_impacts: set[tuple[UUID, str]] = set()
        for impact in payload.impacts:
            key = (impact.knowledge_node_id, impact.impact_type)
            if key in seen_impacts:
                raise CollaborationDomainError(
                    "SUGGESTION_VERSION_CONFLICT", "同一知识点的同类影响不能重复提交。", 409
                )
            seen_impacts.add(key)
            node = await self.repository.knowledge_node_in_course(
                knowledge_node_id=impact.knowledge_node_id, course_id=course.id
            )
            if node is None:
                raise CollaborationDomainError(
                    "COURSE_ACCESS_DENIED", "受影响知识点不属于当前教师课程。"
                )
        version_no = await self.repository.next_suggestion_version(
            course_id=course.id, signal_id=signal.id
        )
        suggestion = await self.repository.create_suggestion(
            course_id=course.id,
            signal_id=signal.id,
            agent_run_id=signal.agent_run_id,
            evidence_snapshot_id=signal.evidence_snapshot_id,
            created_by=actor.id,
            version_no=version_no,
            title=payload.title.strip(),
            diff=payload.diff,
            status="pending_teacher_decision",
        )
        for impact in payload.impacts:
            await self.repository.create_suggestion_impact(
                suggestion_id=suggestion.id,
                knowledge_node_id=impact.knowledge_node_id,
                impact_type=impact.impact_type,
                rationale=impact.rationale.strip(),
            )
        await self.repository.write_audit(
            actor_user_id=actor.id,
            action="course_update_suggestion.create",
            object_type="course_update_suggestion",
            object_id=suggestion.id,
            reason=payload.reason.strip(),
            result_status="succeeded",
            request_id=None,
            metadata={
                "course_id": str(course.id),
                "signal_id": str(signal.id),
                "version_no": version_no,
                "course_row_mutated": False,
                "impact_count": len(payload.impacts),
            },
        )
        return await self._suggestion_dto(suggestion)

    async def list_course_update_suggestions(
        self, *, actor: User, course_id: UUID
    ) -> list[CourseUpdateSuggestionDTO]:
        await self._require_teacher_course(actor=actor, course_id=course_id)
        rows = await self.repository.list_suggestions_for_course(course_id=course_id)
        return [await self._suggestion_dto(row) for row in rows]

    async def decide_course_update_suggestion(
        self,
        *,
        actor: User,
        suggestion_id: UUID,
        payload: CourseUpdateDecisionRequest,
    ) -> CourseUpdateSuggestionDTO:
        suggestion = await self.repository.get_suggestion(suggestion_id)
        if suggestion is None:
            raise CollaborationDomainError("SUGGESTION_VERSION_CONFLICT", "课程更新建议不存在。", 404)
        await self._require_teacher_course(actor=actor, course_id=suggestion.course_id)
        if suggestion.status != "pending_teacher_decision":
            raise CollaborationDomainError(
                "SUGGESTION_ALREADY_DECIDED", "该课程更新建议已处置，不能重复决定。", 409
            )
        if await self.repository.get_suggestion_decision(suggestion.id) is not None:
            raise CollaborationDomainError(
                "SUGGESTION_ALREADY_DECIDED", "该建议已有持久化教师决定。", 409
            )
        decision = await self.repository.create_suggestion_decision(
            suggestion_id=suggestion.id,
            teacher_id=actor.id,
            decision=payload.decision,
            reason=payload.reason.strip(),
            decided_at=datetime.now(UTC),
        )
        suggestion.status = "adopted" if decision.decision == "adopt" else "rejected"
        await self.repository.session.flush()
        # SQLite expires server-managed updated_at after an UPDATE; refresh it
        # before building the async response DTO.
        await self.repository.session.refresh(suggestion)
        await self.repository.write_audit(
            actor_user_id=actor.id,
            action="course_update_suggestion.decide",
            object_type="course_update_suggestion",
            object_id=suggestion.id,
            reason=decision.reason,
            result_status="succeeded",
            request_id=None,
            metadata={
                "decision": decision.decision,
                "course_id": str(suggestion.course_id),
                "course_row_mutated": False,
            },
        )
        return await self._suggestion_dto(suggestion)

    async def send_message(self, *, actor: User, payload: MessageSendRequest) -> MessageDTO:
        course = await self.repository.get_course(payload.course_id)
        if course is None:
            raise CollaborationDomainError("MESSAGE_SCOPE_DENIED", "课程不存在或不可访问。", 404)
        fingerprint = self._fingerprint(
            {
                "scope_type": payload.scope_type,
                "course_id": str(payload.course_id),
                "teaching_class_id": str(payload.teaching_class_id) if payload.teaching_class_id else None,
                "target_user_id": str(payload.target_user_id) if payload.target_user_id else None,
                "subject": payload.subject.strip(),
                "body": payload.body.strip(),
            }
        )
        replay = await self.repository.get_message_by_idempotency(
            sender_user_id=actor.id, idempotency_key=payload.idempotency_key
        )
        if replay is not None:
            if replay.payload_fingerprint != fingerprint:
                raise CollaborationDomainError(
                    "MESSAGE_IDEMPOTENCY_CONFLICT", "相同幂等键不能用于不同的消息内容或范围。", 409
                )
            if replay.safety_state == "rejected":
                raise CollaborationDomainError(
                    "MESSAGE_CONTENT_UNSAFE", "消息正文未通过内容安全校验。", 422
                )
            return await self._message_dto(replay)

        now = datetime.now(UTC)
        if self._is_unsafe_message(payload.subject, payload.body):
            rejected = await self.repository.create_message(
                sender_user_id=actor.id,
                course_id=course.id,
                teaching_class_id=payload.teaching_class_id,
                target_user_id=payload.target_user_id,
                scope_type=payload.scope_type,
                subject=payload.subject.strip(),
                body=payload.body.strip(),
                safety_state="rejected",
                status="draft",
                idempotency_key=payload.idempotency_key,
                payload_fingerprint=fingerprint,
                sent_at=None,
                recall_deadline_at=None,
            )
            await self.repository.write_audit(
                actor_user_id=actor.id,
                action="message.content_rejected",
                object_type="message",
                object_id=rejected.id,
                reason="消息正文命中确定性内容安全规则。",
                result_status="rejected",
                request_id=f"message:{payload.idempotency_key}",
                metadata={"scope_type": payload.scope_type, "course_id": str(course.id)},
            )
            raise CollaborationDomainError("MESSAGE_CONTENT_UNSAFE", "消息正文未通过内容安全校验。", 422)

        recipients = await self._resolve_message_recipients(actor=actor, payload=payload)
        if not recipients:
            raise CollaborationDomainError("RECIPIENT_NOT_FOUND", "当前收件范围没有可投递的有效收件人。", 404)
        message = await self.repository.create_message(
            sender_user_id=actor.id,
            course_id=course.id,
            teaching_class_id=payload.teaching_class_id,
            target_user_id=payload.target_user_id,
            scope_type=payload.scope_type,
            subject=payload.subject.strip(),
            body=payload.body.strip(),
            safety_state="accepted",
            status="sent",
            idempotency_key=payload.idempotency_key,
            payload_fingerprint=fingerprint,
            sent_at=now,
            recall_deadline_at=now + _RECALL_WINDOW,
        )
        await self.repository.create_message_deliveries(
            message_id=message.id, recipient_ids=recipients, delivered_at=now
        )
        await self.repository.write_audit(
            actor_user_id=actor.id,
            action="message.send",
            object_type="message",
            object_id=message.id,
            reason=None,
            result_status="succeeded",
            request_id=f"message:{payload.idempotency_key}",
            metadata={
                "scope_type": message.scope_type,
                "course_id": str(message.course_id),
                "teaching_class_id": str(message.teaching_class_id) if message.teaching_class_id else None,
                "recipient_count": len(recipients),
                "payload_fingerprint": fingerprint,
            },
        )
        await self.repository.write_audit(
            actor_user_id=actor.id,
            action="message.delivery",
            object_type="message",
            object_id=message.id,
            reason=None,
            result_status="succeeded",
            request_id=None,
            metadata={"recipient_count": len(recipients), "delivery_state": "unread"},
        )
        return await self._message_dto(message)

    async def list_inbox(self, *, actor: User) -> MessageInboxDTO:
        rows = await self.repository.list_inbox(recipient_user_id=actor.id)
        items: list[MessageInboxItemDTO] = []
        for delivery, message in rows:
            base = await self._message_dto(message)
            items.append(
                MessageInboxItemDTO(
                    **base.model_dump(),
                    delivery_state=delivery.delivery_state,  # type: ignore[arg-type]
                    delivered_at=delivery.delivered_at,
                    read_at=delivery.read_at,
                )
            )
        return MessageInboxDTO(items=items)

    async def list_outbox(self, *, actor: User) -> list[MessageDTO]:
        rows = await self.repository.list_outbox(sender_user_id=actor.id)
        return [await self._message_dto(row) for row in rows]

    async def mark_message_read(self, *, actor: User, message_id: UUID) -> MessageReadDTO:
        delivery = await self.repository.get_delivery(message_id=message_id, recipient_user_id=actor.id)
        if delivery is None:
            raise CollaborationDomainError("RECIPIENT_NOT_FOUND", "当前账号不是该消息的收件人。", 404)
        if delivery.delivery_state == "recalled":
            raise CollaborationDomainError("MESSAGE_RECALLED", "该消息已撤回，不能标记已读。", 409)
        result_status = "no_op"
        if delivery.delivery_state == "unread":
            delivery.delivery_state = "read"
            delivery.read_at = datetime.now(UTC)
            await self.repository.session.flush()
            result_status = "succeeded"
        await self.repository.write_audit(
            actor_user_id=actor.id,
            action="message.read",
            object_type="message_delivery",
            object_id=delivery.id,
            reason=None,
            result_status=result_status,
            request_id=None,
            metadata={"message_id": str(message_id)},
        )
        return MessageReadDTO(
            message_id=message_id,
            delivery_state=delivery.delivery_state,  # type: ignore[arg-type]
            read_at=delivery.read_at,
        )

    async def recall_message(
        self, *, actor: User, message_id: UUID, payload: RecallMessageRequest
    ) -> MessageDTO:
        message = await self.repository.get_message(message_id)
        if message is None or message.sender_user_id != actor.id:
            raise CollaborationDomainError("MESSAGE_SCOPE_DENIED", "只能撤回自己发送的消息。", 404)
        if message.status not in {"sent", "partially_delivered"}:
            raise CollaborationDomainError("RECALL_WINDOW_EXPIRED", "该消息当前状态不允许撤回。", 409)
        if message.recall_deadline_at is None or datetime.now(UTC) > _as_utc(message.recall_deadline_at):
            raise CollaborationDomainError("RECALL_WINDOW_EXPIRED", "已超过消息撤回时限。", 409)
        recalled_at = datetime.now(UTC)
        message.status = "recalled"
        message.recalled_at = recalled_at
        message.recalled_by = actor.id
        message.recall_reason = payload.reason.strip()
        delivery_count = await self.repository.set_all_deliveries_recalled(
            message_id=message.id, recalled_at=recalled_at
        )
        await self.repository.session.flush()
        await self.repository.session.refresh(message)
        await self.repository.write_audit(
            actor_user_id=actor.id,
            action="message.recall",
            object_type="message",
            object_id=message.id,
            reason=message.recall_reason,
            result_status="succeeded",
            request_id=None,
            metadata={"delivery_count": delivery_count, "recalled_at": recalled_at.isoformat()},
        )
        return await self._message_dto(message)

    async def _resolve_message_recipients(
        self, *, actor: User, payload: MessageSendRequest
    ) -> list[UUID]:
        if payload.scope_type == "course":
            await self._require_teacher_course(actor=actor, course_id=payload.course_id)
            return await self.repository.list_recipient_ids_for_course(payload.course_id)
        if payload.scope_type == "class":
            if payload.teaching_class_id is None:
                raise CollaborationDomainError("MESSAGE_SCOPE_DENIED", "班级消息必须指定教学班。")
            await self._require_teacher_class(
                actor=actor, class_id=payload.teaching_class_id, course_id=payload.course_id
            )
            return await self.repository.list_recipient_ids_for_class(payload.teaching_class_id)
        if payload.target_user_id is None:
            raise CollaborationDomainError("RECIPIENT_NOT_FOUND", "个人消息缺少收件人。", 422)
        target = await self.repository.get_user(payload.target_user_id)
        if target is None or not target.is_active:
            raise CollaborationDomainError("RECIPIENT_NOT_FOUND", "个人收件人不存在或不可用。", 404)
        if actor.role in _COURSE_TEACHER_ROLES:
            await self._require_teacher_course(actor=actor, course_id=payload.course_id)
            if not await self.repository.has_active_enrollment(
                user_id=target.id, course_id=payload.course_id
            ):
                raise CollaborationDomainError(
                    "MESSAGE_SCOPE_DENIED", "教师只能向本人课程的有效选课学生发送个人消息。"
                )
            return [target.id]
        if actor.role == "student":
            if not await self.repository.has_active_enrollment(user_id=actor.id, course_id=payload.course_id):
                raise CollaborationDomainError("MESSAGE_SCOPE_DENIED", "学生未有效选修该课程。")
            if not await self.repository.has_teacher_course_scope(
                teacher_id=target.id, course_id=payload.course_id
            ):
                raise CollaborationDomainError(
                    "MESSAGE_SCOPE_DENIED", "学生只能向当前课程的授权教师发送个人消息。"
                )
            return [target.id]
        raise CollaborationDomainError("MESSAGE_SCOPE_DENIED", "当前账号不具备该消息范围的发送权限。")

    async def _require_fixed_agent_evidence(
        self,
        *,
        kind: str,
        agent_run_id: UUID,
        evidence_snapshot_id: UUID,
        source_document_id: UUID,
    ) -> tuple[Any, Any]:
        run = await self.repository.get_agent_run(agent_run_id)
        evidence = await self.repository.get_evidence_snapshot(evidence_snapshot_id)
        if run is None or run.status != "succeeded" or evidence is None or not evidence.content_digest:
            raise CollaborationDomainError(
                "SIGNAL_EVIDENCE_MISSING", "信号必须引用成功 SkillExecutor 调用的 Evidence Snapshot。", 422
            )
        agent_name, skill_name = _SIGNAL_SKILL_PROVENANCE[kind]
        if run.agent_id != agent_id(agent_name) or run.skill_id != skill_id(agent_name, skill_name):
            raise CollaborationDomainError(
                "SIGNAL_SOURCE_UNTRUSTED", "信号没有来自冻结的政策、热点或岗位分析 Skill。", 422
            )
        linked_by_run = evidence.agent_run_id == run.id
        linked_by_chunk = evidence.chunk_id is not None and evidence.chunk_id in {
            str(chunk_id) for chunk_id in (run.evidence_chunk_ids or [])
        }
        if not linked_by_run and not linked_by_chunk:
            raise CollaborationDomainError(
                "SIGNAL_EVIDENCE_MISSING", "Evidence Snapshot 与固定 AgentRun 没有可验证关联。", 422
            )
        if evidence.document_id != str(source_document_id):
            raise CollaborationDomainError(
                "SIGNAL_SOURCE_UNTRUSTED", "Evidence Snapshot 未指向提交的来源文档。", 422
            )
        return run, evidence

    async def _require_teacher_course(self, *, actor: User, course_id: UUID) -> None:
        self._require_course_teacher(actor)
        if not await self.repository.has_teacher_course_scope(teacher_id=actor.id, course_id=course_id):
            raise CollaborationDomainError("COURSE_ACCESS_DENIED", "当前教师未获该课程的教学授权。")

    async def _require_teacher_class(self, *, actor: User, class_id: UUID, course_id: UUID) -> None:
        self._require_course_teacher(actor)
        if not await self.repository.has_teacher_class_scope(
            teacher_id=actor.id, class_id=class_id, course_id=course_id
        ):
            raise CollaborationDomainError("MESSAGE_SCOPE_DENIED", "当前教师无权向该教学班投递消息。")

    @staticmethod
    def _require_course_teacher(actor: User) -> None:
        if actor.role not in _COURSE_TEACHER_ROLES:
            raise CollaborationDomainError("TEACHER_ROLE_REQUIRED", "当前账号不具备课程教师身份。")

    @staticmethod
    def _is_unsafe_message(subject: str, body: str) -> bool:
        content = f"{subject}\n{body}".strip().lower()
        return not content or any(marker in content for marker in _UNSAFE_MARKERS)

    @staticmethod
    def _fingerprint(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return sha256(encoded.encode("utf-8")).hexdigest()

    async def _signal_dto(self, signal: ExternalSignal) -> ExternalSignalDTO:
        run = await self.repository.get_agent_run(signal.agent_run_id)
        output = run.output_summary if run is not None and isinstance(run.output_summary, dict) else {}
        summary = output.get("summary") or output.get("trend")
        return ExternalSignalDTO(
            id=signal.id,
            kind=signal.kind,  # type: ignore[arg-type]
            title=signal.title,
            source_document_id=signal.source_document_id,
            agent_run_id=signal.agent_run_id,
            evidence_snapshot_id=signal.evidence_snapshot_id,
            source_fingerprint=signal.source_fingerprint,
            status=signal.status,  # type: ignore[arg-type]
            summary=str(summary) if summary else None,
            ingested_at=signal.ingested_at,
        )

    async def _suggestion_dto(self, row: CourseUpdateSuggestion) -> CourseUpdateSuggestionDTO:
        impacts = await self.repository.list_suggestion_impacts(row.id)
        decision = await self.repository.get_suggestion_decision(row.id)
        return CourseUpdateSuggestionDTO(
            id=row.id,
            course_id=row.course_id,
            signal_id=row.signal_id,
            agent_run_id=row.agent_run_id,
            evidence_snapshot_id=row.evidence_snapshot_id,
            version_no=row.version_no,
            title=row.title,
            diff=row.diff if isinstance(row.diff, dict) else {},
            status=row.status,  # type: ignore[arg-type]
            impacts=[
                CourseUpdateImpactDTO(
                    id=impact.id,
                    knowledge_node_id=impact.knowledge_node_id,
                    impact_type=impact.impact_type,  # type: ignore[arg-type]
                    rationale=impact.rationale,
                )
                for impact in impacts
            ],
            decision=self._decision_dto(decision) if decision is not None else None,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def _message_dto(self, row: Message) -> MessageDTO:
        return MessageDTO(
            id=row.id,
            sender_user_id=row.sender_user_id,
            scope_type=row.scope_type,  # type: ignore[arg-type]
            course_id=row.course_id,
            teaching_class_id=row.teaching_class_id,
            target_user_id=row.target_user_id,
            subject=row.subject,
            body=row.body,
            safety_state=row.safety_state,  # type: ignore[arg-type]
            status=row.status,  # type: ignore[arg-type]
            sent_at=row.sent_at,
            recall_deadline_at=row.recall_deadline_at,
            recalled_at=row.recalled_at,
            delivery_counts=await self.repository.message_delivery_counts(row.id),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _decision_dto(row: CourseUpdateDecision) -> CourseUpdateDecisionDTO:
        return CourseUpdateDecisionDTO(
            id=row.id,
            suggestion_id=row.suggestion_id,
            teacher_id=row.teacher_id,
            decision=row.decision,  # type: ignore[arg-type]
            reason=row.reason,
            decided_at=row.decided_at,
        )
