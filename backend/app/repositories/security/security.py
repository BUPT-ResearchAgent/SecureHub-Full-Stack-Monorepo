# Status: real

"""SQL-only persistence adapter for T5 account and API-risk governance."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.education.education_domain import GovernanceAuditEvent
from app.db.models.governance.governance import RoleDefinition, UserRoleGrant
from app.db.models.identity.user import User
from app.db.models.security.account_security import (
    AccountPasswordCompliance,
    ApiRequestAuditEvent,
    ApiRiskAction,
    ApiRiskEvent,
    ApiRiskRule,
    PasswordPolicy,
)
from app.repositories.base import BaseRepository


class SecurityRepository(BaseRepository):
    """Owns only persistence queries; policy and detection decisions live in services."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_user(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_active_password_policy(self) -> PasswordPolicy | None:
        return await self.session.scalar(
            select(PasswordPolicy)
            .where(PasswordPolicy.status == "active")
            .order_by(PasswordPolicy.version_no.desc())
        )

    async def get_password_policy(self, policy_id: UUID) -> PasswordPolicy | None:
        return await self.session.get(PasswordPolicy, policy_id)

    async def next_password_policy_version(self) -> int:
        value = await self.session.scalar(select(func.max(PasswordPolicy.version_no)))
        return int(value or 0) + 1

    async def create_password_policy(self, **values: Any) -> PasswordPolicy:
        row = PasswordPolicy(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_active_password_policies(self) -> list[PasswordPolicy]:
        result = await self.session.execute(
            select(PasswordPolicy).where(PasswordPolicy.status == "active")
        )
        return list(result.scalars().all())

    async def get_compliance(self, user_id: UUID) -> AccountPasswordCompliance | None:
        return await self.session.scalar(
            select(AccountPasswordCompliance).where(AccountPasswordCompliance.user_id == user_id)
        )

    async def create_compliance(self, **values: Any) -> AccountPasswordCompliance:
        row = AccountPasswordCompliance(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def is_security_admin(self, user_id: UUID) -> bool:
        """T5 deliberately reuses the T4 server-side ``administrator`` grant."""

        value = await self.session.scalar(
            select(UserRoleGrant.id)
            .join(RoleDefinition, RoleDefinition.id == UserRoleGrant.role_id)
            .where(
                UserRoleGrant.user_id == user_id,
                UserRoleGrant.status == "active",
                RoleDefinition.code == "administrator",
                RoleDefinition.status == "active",
            )
        )
        return value is not None

    async def count_recovery_administrators(
        self, *, policy_version: int, now: datetime
    ) -> int:
        recovery_status = and_(
            AccountPasswordCompliance.evaluated_policy_version == policy_version,
            or_(
                AccountPasswordCompliance.status.in_(("compliant", "remediated")),
                and_(
                    AccountPasswordCompliance.status == "temporarily_exempt",
                    AccountPasswordCompliance.exemption_expires_at.is_not(None),
                    AccountPasswordCompliance.exemption_expires_at > now,
                ),
            ),
        )
        value = await self.session.scalar(
            select(func.count(func.distinct(UserRoleGrant.user_id)))
            .join(RoleDefinition, RoleDefinition.id == UserRoleGrant.role_id)
            .outerjoin(
                AccountPasswordCompliance,
                AccountPasswordCompliance.user_id == UserRoleGrant.user_id,
            )
            .where(
                UserRoleGrant.status == "active",
                RoleDefinition.code == "administrator",
                RoleDefinition.status == "active",
                recovery_status,
            )
        )
        return int(value or 0)

    async def write_business_audit(
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
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_active_risk_rules(self) -> list[ApiRiskRule]:
        result = await self.session.execute(
            select(ApiRiskRule)
            .where(ApiRiskRule.status == "active")
            .order_by(ApiRiskRule.code, ApiRiskRule.version_no.desc())
        )
        return list(result.scalars().all())

    async def get_risk_rule(self, rule_id: UUID) -> ApiRiskRule | None:
        return await self.session.get(ApiRiskRule, rule_id)

    async def next_risk_rule_version(self, code: str) -> int:
        value = await self.session.scalar(
            select(func.max(ApiRiskRule.version_no)).where(ApiRiskRule.code == code)
        )
        return int(value or 0) + 1

    async def create_risk_rule(self, **values: Any) -> ApiRiskRule:
        row = ApiRiskRule(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_active_risk_rules_by_code(self, code: str) -> list[ApiRiskRule]:
        result = await self.session.execute(
            select(ApiRiskRule).where(ApiRiskRule.code == code, ApiRiskRule.status == "active")
        )
        return list(result.scalars().all())

    async def create_request_audit(self, **values: Any) -> ApiRequestAuditEvent:
        row = ApiRequestAuditEvent(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def count_windowed_requests(
        self,
        *,
        scope: str,
        actor_user_id: UUID | None,
        ip_hash: str | None,
        device_hash: str | None,
        route_template: str,
        method: str,
        window_start: datetime,
        predicate: dict[str, Any],
    ) -> int:
        filters = [ApiRequestAuditEvent.occurred_at >= window_start]
        if scope == "user":
            if actor_user_id is None:
                return 0
            filters.append(ApiRequestAuditEvent.actor_user_id == actor_user_id)
        elif scope == "ip":
            if ip_hash is None:
                return 0
            filters.append(ApiRequestAuditEvent.ip_hash == ip_hash)
        elif scope == "device":
            if device_hash is None:
                return 0
            filters.append(ApiRequestAuditEvent.device_hash == device_hash)
        elif scope == "api":
            filters.extend(
                [
                    ApiRequestAuditEvent.route_template == route_template,
                    ApiRequestAuditEvent.method == method,
                ]
            )
        else:
            return 0

        expected_method = predicate.get("method")
        if isinstance(expected_method, str) and expected_method:
            filters.append(ApiRequestAuditEvent.method == expected_method.upper())
        expected_route = predicate.get("route_template")
        if isinstance(expected_route, str) and expected_route:
            filters.append(ApiRequestAuditEvent.route_template == expected_route)
        route_prefix = predicate.get("route_prefix")
        if isinstance(route_prefix, str) and route_prefix:
            filters.append(ApiRequestAuditEvent.route_template.like(f"{route_prefix}%"))

        value = await self.session.scalar(select(func.count(ApiRequestAuditEvent.id)).where(*filters))
        return int(value or 0)

    async def create_risk_event(self, **values: Any) -> ApiRiskEvent:
        row = ApiRiskEvent(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_risk_event(self, event_id: UUID) -> ApiRiskEvent | None:
        return await self.session.get(ApiRiskEvent, event_id)

    async def list_risk_events(self, *, limit: int = 100) -> list[ApiRiskEvent]:
        result = await self.session.execute(
            select(ApiRiskEvent).order_by(ApiRiskEvent.opened_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def create_risk_action(self, **values: Any) -> ApiRiskAction:
        row = ApiRiskAction(id=uuid4(), **values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_risk_actions(self, event_id: UUID) -> list[ApiRiskAction]:
        result = await self.session.execute(
            select(ApiRiskAction)
            .where(ApiRiskAction.risk_event_id == event_id)
            .order_by(ApiRiskAction.created_at)
        )
        return list(result.scalars().all())
