# Status: real

"""Authorization-aware orchestration for teaching classes and student groups."""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.education.education_domain import (
    GovernanceAuditEvent,
    StudentGroup,
    StudentGroupMember,
    TeachingClass,
)
from app.db.models.identity.user import User
from app.repositories.education.education_domain import EducationRepository
from app.schemas.education import (
    ChangeStudentGroupMemberRequest,
    CreateStudentGroupRequest,
    RosterStudentDTO,
    StudentGroupDTO,
    StudentGroupListDTO,
    StudentGroupMemberDTO,
    TeachingClassDTO,
    TeachingClassListDTO,
    TeachingClassRosterDTO,
)

_COURSE_TEACHER_ROLES = {"course_teacher", "hybrid"}


class EducationDomainError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 403) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class EducationService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = EducationRepository(session)

    async def list_classes(
        self, *, actor: User, course_id: UUID | None = None
    ) -> TeachingClassListDTO:
        self._require_course_teacher_role(actor)
        if course_id is not None:
            assignment = await self.repository.get_course_teacher_assignment(
                course_id=course_id, teacher_id=actor.id
            )
            if assignment is None:
                raise EducationDomainError(
                    "COURSE_ACCESS_DENIED", "当前教师未获该课程的教学授权。"
                )
        classes = await self.repository.list_classes_for_teacher(
            teacher_id=actor.id, course_id=course_id
        )
        counts = await self.repository.enrollment_counts([row.id for row in classes])
        return TeachingClassListDTO(
            items=[self._class_dto(row, student_count=counts.get(row.id, 0)) for row in classes]
        )

    async def get_roster(self, *, actor: User, class_id: UUID) -> TeachingClassRosterDTO:
        teaching_class = await self._require_class_scope(actor=actor, class_id=class_id)
        rows = await self.repository.list_roster(class_id)
        return TeachingClassRosterDTO(
            teaching_class=self._class_dto(teaching_class, student_count=len(rows)),
            students=[
                RosterStudentDTO(
                    id=student.id,
                    display_name=student.display_name,
                    enrollment_status=enrollment.status,  # type: ignore[arg-type]
                    enrolled_at=enrollment.enrolled_at,
                )
                for enrollment, student in rows
            ],
        )

    async def get_groups(self, *, actor: User, class_id: UUID) -> StudentGroupListDTO:
        teaching_class = await self._require_class_scope(actor=actor, class_id=class_id)
        groups = await self.repository.list_groups(class_id)
        member_rows = await self.repository.list_group_members([group.id for group in groups])
        members_by_group: dict[UUID, list[StudentGroupMemberDTO]] = defaultdict(list)
        for member, student in member_rows:
            members_by_group[member.group_id].append(self._member_dto(member, student.display_name))
        roster_count = len(await self.repository.list_roster(class_id))
        return StudentGroupListDTO(
            teaching_class=self._class_dto(teaching_class, student_count=roster_count),
            items=[
                self._group_dto(group, members_by_group.get(group.id, [])) for group in groups
            ],
        )

    async def create_group(
        self,
        *,
        actor: User,
        class_id: UUID,
        payload: CreateStudentGroupRequest,
        idempotency_key: str,
    ) -> StudentGroupDTO:
        await self._require_class_scope(actor=actor, class_id=class_id)
        fingerprint = self._fingerprint(
            {"operation": "student_group.create", "class_id": str(class_id), "name": payload.name}
        )
        replay = await self._get_replay(
            actor_user_id=actor.id, idempotency_key=idempotency_key, fingerprint=fingerprint
        )
        if replay is not None:
            group = await self.repository.get_group(replay.object_id)
            if group is None or group.teaching_class_id != class_id:
                raise EducationDomainError(
                    "IDEMPOTENCY_CONFLICT", "幂等请求已关联到不可用的分组。", 409
                )
            return self._group_dto(group, [])

        existing = await self.repository.get_group_by_name(class_id=class_id, name=payload.name)
        if existing is not None:
            raise EducationDomainError(
                "IDEMPOTENCY_CONFLICT", "该班级已有同名分组，请使用原请求键重试。", 409
            )
        group = await self.repository.create_group(
            class_id=class_id, name=payload.name, actor_user_id=actor.id
        )
        await self.repository.write_audit(
            actor_user_id=actor.id,
            action="student_group.create",
            object_type="student_group",
            object_id=group.id,
            reason=payload.reason,
            result_status="succeeded",
            request_id=idempotency_key,
            metadata={"request_fingerprint": fingerprint, "teaching_class_id": str(class_id)},
        )
        return self._group_dto(group, [])

    async def change_group_member(
        self,
        *,
        actor: User,
        class_id: UUID,
        group_id: UUID,
        payload: ChangeStudentGroupMemberRequest,
        idempotency_key: str,
    ) -> StudentGroupMemberDTO:
        await self._require_class_scope(actor=actor, class_id=class_id)
        group = await self.repository.get_group_for_class(group_id=group_id, class_id=class_id)
        if group is None:
            raise EducationDomainError("GROUP_SCOPE_DENIED", "分组不属于当前教学班。")
        fingerprint = self._fingerprint(
            {
                "operation": "student_group.member_change",
                "class_id": str(class_id),
                "group_id": str(group_id),
                "student_id": str(payload.student_id),
                "action": payload.action,
            }
        )
        replay = await self._get_replay(
            actor_user_id=actor.id, idempotency_key=idempotency_key, fingerprint=fingerprint
        )
        if replay is not None:
            member = await self.repository.get_group_member(
                group_id=group_id, student_id=payload.student_id
            )
            student = await self.repository.get_user(payload.student_id)
            if member is None or student is None or replay.object_id != member.id:
                raise EducationDomainError(
                    "IDEMPOTENCY_CONFLICT", "幂等请求未能恢复原成员状态。", 409
                )
            return self._member_dto(member, student.display_name)

        member = await self.repository.get_group_member(
            group_id=group_id, student_id=payload.student_id
        )
        if payload.action == "add":
            enrollment = await self.repository.get_active_enrollment(
                class_id=class_id, student_id=payload.student_id
            )
            if enrollment is None:
                raise EducationDomainError(
                    "ENROLLMENT_REQUIRED", "学生未在当前教学班有效选课，不能加入分组。"
                )
            if member is None:
                member = await self.repository.create_group_member(
                    group_id=group_id,
                    student_id=payload.student_id,
                    status="active",
                    actor_user_id=actor.id,
                )
                result_status = "succeeded"
            elif member.status != "active":
                member = await self.repository.set_group_member_state(
                    member, status="active", actor_user_id=actor.id
                )
                result_status = "succeeded"
            else:
                result_status = "no_op"
        else:
            if member is None:
                raise EducationDomainError(
                    "ENROLLMENT_REQUIRED", "学生不是当前分组的有效成员，无法移除。"
                )
            if member.status != "removed":
                member = await self.repository.set_group_member_state(
                    member, status="removed", actor_user_id=actor.id
                )
                result_status = "succeeded"
            else:
                result_status = "no_op"

        student = await self.repository.get_user(payload.student_id)
        if student is None:
            raise EducationDomainError("ENROLLMENT_REQUIRED", "学生身份不存在或已不可用。")
        await self.repository.write_audit(
            actor_user_id=actor.id,
            action=f"student_group.member_{payload.action}",
            object_type="student_group_member",
            object_id=member.id,
            reason=payload.reason,
            result_status=result_status,
            request_id=idempotency_key,
            metadata={
                "request_fingerprint": fingerprint,
                "teaching_class_id": str(class_id),
                "group_id": str(group_id),
                "student_id": str(payload.student_id),
            },
        )
        return self._member_dto(member, student.display_name)

    async def _require_class_scope(self, *, actor: User, class_id: UUID) -> TeachingClass:
        self._require_course_teacher_role(actor)
        teaching_class = await self.repository.get_class(class_id)
        if teaching_class is None:
            raise EducationDomainError("CLASS_NOT_FOUND", "教学班不存在或已被移除。", 404)
        scoped_class = await self.repository.get_teacher_class(
            teacher_id=actor.id, class_id=class_id
        )
        if scoped_class is None:
            raise EducationDomainError(
                "COURSE_ACCESS_DENIED", "当前教师无权访问该教学班或所属课程。"
            )
        return scoped_class

    @staticmethod
    def _require_course_teacher_role(actor: User) -> None:
        if actor.role not in _COURSE_TEACHER_ROLES:
            raise EducationDomainError(
                "TEACHER_ROLE_REQUIRED", "当前账号不具备课程教学班管理身份。"
            )

    async def _get_replay(
        self, *, actor_user_id: UUID, idempotency_key: str, fingerprint: str
    ) -> GovernanceAuditEvent | None:
        event = await self.repository.get_audit_by_request(
            actor_user_id=actor_user_id, request_id=idempotency_key
        )
        if event is None:
            return None
        metadata = event.metadata_ if isinstance(event.metadata_, dict) else {}
        if metadata.get("request_fingerprint") != fingerprint:
            raise EducationDomainError(
                "IDEMPOTENCY_CONFLICT", "相同幂等键不能用于不同的教学关系操作。", 409
            )
        return event

    @staticmethod
    def _fingerprint(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _class_dto(row: TeachingClass, *, student_count: int) -> TeachingClassDTO:
        return TeachingClassDTO(
            id=row.id,
            course_id=row.course_id,
            code=row.code,
            name=row.name,
            status=row.status,  # type: ignore[arg-type]
            student_count=student_count,
        )

    @staticmethod
    def _member_dto(row: StudentGroupMember, display_name: str) -> StudentGroupMemberDTO:
        return StudentGroupMemberDTO(
            id=row.id,
            student_id=row.student_id,
            display_name=display_name,
            status=row.status,  # type: ignore[arg-type]
            changed_at=row.changed_at,
        )

    @staticmethod
    def _group_dto(
        row: StudentGroup, members: list[StudentGroupMemberDTO]
    ) -> StudentGroupDTO:
        return StudentGroupDTO(
            id=row.id,
            teaching_class_id=row.teaching_class_id,
            name=row.name,
            status=row.status,  # type: ignore[arg-type]
            members=members,
        )
