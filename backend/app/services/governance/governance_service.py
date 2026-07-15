# Status: real

"""Server-authoritative RBAC, resource governance, and live KPI queries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.governance.governance import (
    CourseResourceGovernance,
    KpiDefinition,
    UserRoleGrant,
)
from app.db.models.identity.user import User
from app.repositories.governance.governance import GovernanceRepository
from app.schemas.governance import (
    AdminCourseResourceDTO,
    AdminCourseResourceListDTO,
    AdminKpiDashboardDTO,
    AdminUserDTO,
    AdminUserListDTO,
    CourseResourceGovernanceRequest,
    KpiValueDTO,
    RoleGrantDTO,
    RoleGrantRequest,
    RoleRevokeRequest,
)

_ADMIN_ROLE = "administrator"
_DEFAULT_ADMIN_PERMISSIONS = [
    "admin.users.read",
    "admin.roles.write",
    "admin.resources.govern",
    "admin.kpi.read",
]
_DEFAULT_KPIS: tuple[dict[str, Any], ...] = (
    {
        "code": "active_teaching_classes",
        "query_key": "active_teaching_classes",
        "description": "状态为 active 的教学班总数。",
        "source_relations": ["teaching_classes"],
    },
    {
        "code": "enrolled_students",
        "query_key": "enrolled_students",
        "description": "状态为 enrolled 的课程选课记录总数。",
        "source_relations": ["course_enrollments"],
    },
    {
        "code": "published_grades",
        "query_key": "published_grades",
        "description": "状态为 published 的教师成绩决定总数。",
        "source_relations": ["assessment_grade_decisions"],
    },
    {
        "code": "pending_course_updates",
        "query_key": "pending_course_updates",
        "description": "待课程教师处置的 Evidence 绑定课程更新建议总数。",
        "source_relations": ["course_update_suggestions", "external_signals"],
    },
    {
        "code": "sent_messages_7d",
        "query_key": "sent_messages_7d",
        "description": "最近七天实际投递的站内消息总数。",
        "source_relations": ["messages", "message_deliveries"],
    },
    {
        "code": "unread_deliveries",
        "query_key": "unread_deliveries",
        "description": "当前尚未读取且未撤回的消息投递总数。",
        "source_relations": ["message_deliveries"],
    },
)


class GovernanceDomainError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 403) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class GovernanceService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = GovernanceRepository(session)

    async def ensure_default_definitions(self) -> None:
        """Idempotent metadata bootstrap for tests and fresh demo databases.

        Production migration 1083 writes the same immutable definitions.  This
        helper only fills an empty metadata table for test databases created
        straight from ORM metadata; it never grants any user administrator
        authority.
        """

        if await self.repository.get_active_role_by_code(_ADMIN_ROLE) is None:
            await self.repository.create_role_definition(
                code=_ADMIN_ROLE,
                version_no=1,
                permission_codes=_DEFAULT_ADMIN_PERMISSIONS,
                status="active",
                description="平台治理、角色、课程资源与真实 KPI 管理权限。",
            )
        for definition in _DEFAULT_KPIS:
            current = await self.repository.session.scalar(
                select(KpiDefinition).where(
                    KpiDefinition.code == definition["code"], KpiDefinition.status == "active"
                )
            )
            if current is None:
                row = KpiDefinition(id=uuid4(), version_no=1, status="active", **definition)
                self.repository.session.add(row)
                await self.repository.session.flush()

    async def list_users(self, *, actor: User) -> AdminUserListDTO:
        await self._require_admin(actor)
        users = await self.repository.list_users()
        role_codes = await self.repository.list_role_codes_by_user()
        return AdminUserListDTO(
            items=[
                AdminUserDTO(
                    id=user.id,
                    display_name=user.display_name,
                    email=user.email,
                    product_role=user.role,
                    is_active=user.is_active,
                    governance_roles=role_codes.get(user.id, []),
                )
                for user in users
            ]
        )

    async def grant_role(self, *, actor: User, payload: RoleGrantRequest) -> RoleGrantDTO:
        await self._require_admin(actor)
        target = await self.repository.get_user(payload.user_id)
        if target is None or not target.is_active:
            raise GovernanceDomainError("ROLE_GRANT_FORBIDDEN", "目标用户不存在或已停用。", 404)
        role = await self.repository.get_active_role_by_code(payload.role_code)
        if role is None:
            raise GovernanceDomainError("ROLE_GRANT_FORBIDDEN", "请求的治理角色不存在或未激活。", 404)
        existing = await self.repository.get_active_grant(user_id=target.id, role_id=role.id)
        if existing is not None:
            await self.repository.write_audit(
                actor_user_id=actor.id,
                action="role_grant.create",
                object_type="user_role_grant",
                object_id=existing.id,
                reason=payload.reason.strip(),
                result_status="no_op",
                request_id=None,
                metadata={"target_user_id": str(target.id), "role_code": role.code},
            )
            return self._grant_dto(existing, role.code)
        grant = await self.repository.create_role_grant(
            user_id=target.id,
            role_id=role.id,
            granted_by=actor.id,
            granted_at=datetime.now(UTC),
            status="active",
            reason=payload.reason.strip(),
        )
        await self.repository.write_audit(
            actor_user_id=actor.id,
            action="role_grant.create",
            object_type="user_role_grant",
            object_id=grant.id,
            reason=grant.reason,
            result_status="succeeded",
            request_id=None,
            metadata={"target_user_id": str(target.id), "role_code": role.code},
        )
        return self._grant_dto(grant, role.code)

    async def revoke_role(
        self, *, actor: User, grant_id: UUID, payload: RoleRevokeRequest
    ) -> RoleGrantDTO:
        await self._require_admin(actor)
        grant = await self.repository.get_role_grant(grant_id)
        if grant is None or grant.status != "active":
            raise GovernanceDomainError("ROLE_GRANT_FORBIDDEN", "角色授予不存在或已撤销。", 404)
        role = await self.repository.get_role(grant.role_id)
        if role is None or role.status != "active":
            raise GovernanceDomainError("ROLE_GRANT_FORBIDDEN", "角色定义不可用。", 409)
        if role.code == _ADMIN_ROLE and await self.repository.count_active_role(_ADMIN_ROLE) <= 1:
            raise GovernanceDomainError(
                "LAST_ADMIN_PROTECTED", "不能撤销最后一位可恢复管理员的角色。", 409
            )
        grant.status = "revoked"
        grant.revoked_by = actor.id
        grant.revoked_at = datetime.now(UTC)
        grant.revoke_reason = payload.reason.strip()
        await self.repository.session.flush()
        await self.repository.write_audit(
            actor_user_id=actor.id,
            action="role_grant.revoke",
            object_type="user_role_grant",
            object_id=grant.id,
            reason=grant.revoke_reason,
            result_status="succeeded",
            request_id=None,
            metadata={"target_user_id": str(grant.user_id), "role_code": role.code},
        )
        return self._grant_dto(grant, role.code)

    async def list_course_resources(self, *, actor: User) -> AdminCourseResourceListDTO:
        await self._require_admin(actor)
        rows = await self.repository.list_resource_contexts()
        return AdminCourseResourceListDTO(
            items=[self._resource_dto(asset, binding.course_id, course.code, document, overlay) for asset, binding, document, course, overlay in rows]
        )

    async def govern_course_resource(
        self,
        *,
        actor: User,
        asset_id: UUID,
        payload: CourseResourceGovernanceRequest,
    ) -> AdminCourseResourceDTO:
        await self._require_admin(actor)
        context = await self.repository.get_asset_context(asset_id)
        if context is None:
            raise GovernanceDomainError("RESOURCE_GOVERNANCE_DENIED", "课程资源不存在。", 404)
        asset, binding, document, course = context
        if payload.action == "release" and asset.state == "deleted":
            raise GovernanceDomainError(
                "RESOURCE_GOVERNANCE_DENIED", "已删除资源不能由管理入口直接恢复。", 409
            )
        now = datetime.now(UTC)
        target_state = {"restrict": "restricted", "release": "active", "withdraw": "withdrawn"}[payload.action]
        overlay = await self.repository.get_resource_governance(asset.id)
        if overlay is None:
            overlay = await self.repository.create_resource_governance(
                asset_id=asset.id,
                state=target_state,
                changed_by=actor.id,
                reason=payload.reason.strip(),
                changed_at=now,
            )
        else:
            overlay.state = target_state
            overlay.changed_by = actor.id
            overlay.reason = payload.reason.strip()
            overlay.changed_at = now
        if payload.action in {"restrict", "withdraw"}:
            asset.state = "withdrawn"
            asset.withdrawn_at = now
            asset.withdrawn_by = actor.id
            asset.reason = payload.reason.strip()
        else:
            asset.state = "ready"
            asset.withdrawn_at = None
            asset.withdrawn_by = None
            asset.reason = payload.reason.strip()
        await self.repository.session.flush()
        # Avoid an async lazy load of TimestampMixin.updated_at after state
        # mutation on SQLite-compatible test sessions.
        await self.repository.session.refresh(asset)
        await self.repository.session.refresh(overlay)
        await self.repository.write_audit(
            actor_user_id=actor.id,
            action="course_resource.govern",
            object_type="course_asset_governance",
            object_id=asset.id,
            reason=payload.reason.strip(),
            result_status="succeeded",
            request_id=None,
            metadata={
                "action": payload.action,
                "governance_state": target_state,
                "course_id": str(binding.course_id),
                "asset_state": asset.state,
            },
        )
        return self._resource_dto(asset, binding.course_id, course.code, document, overlay)

    async def get_kpi_dashboard(self, *, actor: User) -> AdminKpiDashboardDTO:
        await self._require_admin(actor)
        now = datetime.now(UTC)
        window_start = now - timedelta(days=7)
        definitions = await self.repository.list_active_kpi_definitions()
        items: list[KpiValueDTO] = []
        for definition in definitions:
            try:
                value = await self.repository.count_kpi(
                    query_key=definition.query_key, window_start=window_start
                )
            except ValueError as exc:
                raise GovernanceDomainError(
                    "KPI_DEFINITION_UNKNOWN", "KPI 定义引用了未受控的查询口径。", 409
                ) from exc
            items.append(
                KpiValueDTO(
                    code=definition.code,
                    definition_version=definition.version_no,
                    description=definition.description,
                    source_relations=list(definition.source_relations or []),
                    time_window="rolling_7d" if definition.query_key == "sent_messages_7d" else "current",
                    value=value,
                    calculated_at=now,
                )
            )
        return AdminKpiDashboardDTO(items=items, calculated_at=now)

    async def _require_admin(self, actor: User) -> None:
        if not await self.repository.has_active_role(user_id=actor.id, role_code=_ADMIN_ROLE):
            raise GovernanceDomainError("ADMIN_ROLE_REQUIRED", "当前账号不具备管理员治理权限。")

    @staticmethod
    def _grant_dto(grant: UserRoleGrant, role_code: str) -> RoleGrantDTO:
        return RoleGrantDTO(
            id=grant.id,
            user_id=grant.user_id,
            role_id=grant.role_id,
            role_code=role_code,
            granted_by=grant.granted_by,
            granted_at=grant.granted_at,
            status=grant.status,  # type: ignore[arg-type]
            reason=grant.reason,
            revoked_at=grant.revoked_at,
        )

    @staticmethod
    def _resource_dto(
        asset: Any,
        course_id: UUID,
        course_code: str,
        document: Any,
        overlay: CourseResourceGovernance | None,
    ) -> AdminCourseResourceDTO:
        return AdminCourseResourceDTO(
            asset_id=asset.id,
            course_id=course_id,
            course_code=course_code,
            document_id=document.id,
            document_title=document.title,
            asset_state=asset.state,
            governance_state=(overlay.state if overlay is not None else "active"),  # type: ignore[arg-type]
            reason=overlay.reason if overlay is not None else asset.reason,
            changed_at=overlay.changed_at if overlay is not None else asset.updated_at,
        )
