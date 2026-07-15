# Status: real

"""T5 password-policy lifecycle and explainable API-risk disposition.

Password policy state is intentionally version-based.  Legacy accounts are
identified from their persisted compliance record, never by reading, scanning,
or attempting to infer properties from ``users.hashed_password``.  Hash access
only occurs for normal current-password authentication or writing a newly
validated password.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password, verify_password
from app.db.models.identity.user import User
from app.db.models.security.account_security import (
    AccountPasswordCompliance,
    ApiRequestAuditEvent,
    ApiRiskAction,
    ApiRiskEvent,
    ApiRiskRule,
    PasswordPolicy,
)
from app.repositories.security.security import SecurityRepository
from app.schemas.security import (
    ApiRiskActionDTO,
    ApiRiskEventDTO,
    ApiRiskReleaseRequest,
    ApiRiskReviewRequest,
    ApiRiskRuleActivateRequest,
    ApiRiskRuleCreateRequest,
    ApiRiskRuleDTO,
    PasswordChangeRequest,
    PasswordComplianceDTO,
    PasswordExemptionRequest,
    PasswordPolicyActivateRequest,
    PasswordPolicyCreateRequest,
    PasswordPolicyDTO,
    PasswordResetRequest,
)

DEFAULT_PASSWORD_RULES: dict[str, Any] = {
    "min_length": 8,
    "max_length": 72,
    "require_upper": True,
    "require_lower": True,
    "require_digit": True,
    "require_symbol": True,
}
_VALID_RULE_KEYS = set(DEFAULT_PASSWORD_RULES)
_REMEDIATION_WINDOW = timedelta(days=7)
_BREAK_GLASS_WINDOW = timedelta(hours=24)


class SecurityDomainError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 403) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class RedactedRequestObservation:
    """Only fields permitted to enter the request-audit persistence boundary."""

    route_template: str
    method: str
    actor_user_id: UUID | None
    ip_hash: str | None
    device_hash: str | None
    rate_bucket: str
    request_size_bucket: str
    correlation_id: str | None
    redaction_version: str = "v1"


@dataclass(frozen=True)
class RiskDecision:
    audit_id: UUID
    decision: str
    risk_event_id: UUID | None
    explanation: dict[str, Any]


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def opaque_identifier_hash(value: str | None, *, secret: str) -> str | None:
    """Return a keyed, non-reversible correlation hash without retaining input."""

    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return hmac.new(
        secret.encode("utf-8"),
        f"securehub-api-risk-v1:{normalized}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def request_size_bucket(content_length: int | None) -> str:
    if content_length is None or content_length <= 1024:
        return "0-1KiB"
    if content_length <= 16 * 1024:
        return "1-16KiB"
    if content_length <= 256 * 1024:
        return "16-256KiB"
    return "256KiB+"


class SecurityGovernanceService:
    """Application service for T5 state transitions and risk outcomes."""

    def __init__(self, session: AsyncSession) -> None:
        self.repository = SecurityRepository(session)

    async def ensure_default_password_policy(self) -> PasswordPolicy:
        """Idempotently bootstrap the conservative v1 policy for fresh databases.

        The baseline is policy metadata, not an account-password inspection.
        Migrations seed the same row for production; this helper supports ORM
        metadata test databases without granting any user extra authority.
        """

        active = await self.repository.get_active_password_policy()
        if active is not None:
            return active
        now = datetime.now(UTC)
        return await self.repository.create_password_policy(
            version_no=await self.repository.next_password_policy_version(),
            rules_json=dict(DEFAULT_PASSWORD_RULES),
            status="active",
            created_by=None,
            activated_at=now,
            retired_at=None,
            note="T5 baseline policy; no legacy password hash is evaluated.",
        )

    @staticmethod
    def validate_password_for_rules(password: str, rules: dict[str, Any]) -> None:
        unexpected = set(rules) - _VALID_RULE_KEYS
        if unexpected:
            raise SecurityDomainError(
                "PASSWORD_POLICY_VIOLATION",
                f"密码策略包含未受支持字段: {', '.join(sorted(unexpected))}",
                400,
            )
        try:
            min_length = int(rules.get("min_length", DEFAULT_PASSWORD_RULES["min_length"]))
            max_length = int(rules.get("max_length", DEFAULT_PASSWORD_RULES["max_length"]))
        except (TypeError, ValueError) as exc:
            raise SecurityDomainError("PASSWORD_POLICY_VIOLATION", "密码策略长度配置无效。", 400) from exc
        if min_length < 8 or max_length > 72 or min_length > max_length:
            raise SecurityDomainError("PASSWORD_POLICY_VIOLATION", "密码策略长度范围无效。", 400)
        has_upper = any(char.isupper() for char in password)
        has_lower = any(char.islower() for char in password)
        has_digit = any(char.isdigit() for char in password)
        has_symbol = any(not char.isalnum() for char in password)
        checks = (
            len(password) >= min_length,
            len(password.encode("utf-8")) <= max_length,
            not bool(rules.get("require_upper", True)) or has_upper,
            not bool(rules.get("require_lower", True)) or has_lower,
            not bool(rules.get("require_digit", True)) or has_digit,
            not bool(rules.get("require_symbol", True)) or has_symbol,
        )
        if not all(checks):
            raise SecurityDomainError(
                "PASSWORD_POLICY_VIOLATION",
                "密码不符合当前版本的长度和字符类别要求。",
                400,
            )

    async def validate_new_password(self, password: str) -> PasswordPolicy:
        policy = await self.ensure_default_password_policy()
        self.validate_password_for_rules(password, dict(policy.rules_json or {}))
        return policy

    async def register_compliant_password(self, *, user: User, policy: PasswordPolicy) -> None:
        now = datetime.now(UTC)
        compliance = await self.repository.get_compliance(user.id)
        if compliance is None:
            compliance = await self.repository.create_compliance(
                user_id=user.id,
                evaluated_policy_version=policy.version_no,
                status="compliant",
                remediation_due_at=None,
                last_notified_at=None,
                remediated_at=now,
                exemption_expires_at=None,
                updated_by=user.id,
                exemption_reason=None,
            )
        else:
            compliance.evaluated_policy_version = policy.version_no
            compliance.status = "compliant"
            compliance.remediation_due_at = None
            compliance.remediated_at = now
            compliance.exemption_expires_at = None
            compliance.updated_by = user.id
            compliance.exemption_reason = None
            await self.repository.session.flush()
        await self.repository.write_business_audit(
            actor_user_id=user.id,
            action="password_policy.register_compliant",
            object_type="account_password_compliance",
            object_id=compliance.id,
            reason="注册时以明文密码完成当前策略校验。",
            result_status="succeeded",
            request_id=None,
            metadata={"policy_version": policy.version_no, "status": compliance.status},
        )

    async def evaluate_login_compliance(self, *, user: User) -> PasswordComplianceDTO:
        """Evaluate only persisted policy-version state before issuing a token."""

        now = datetime.now(UTC)
        policy = await self.ensure_default_password_policy()
        compliance = await self.repository.get_compliance(user.id)
        if self._allows_login(compliance, policy.version_no, now):
            assert compliance is not None
            return self._compliance_dto(compliance, policy.version_no, now)

        # A policy migration must never lock every T4 administrator.  If an
        # existing security administrator is the only possible recovery path,
        # create a time-bounded, auditable exemption rather than infer anything
        # from that account's password hash.
        if await self.repository.is_security_admin(user.id):
            recovery_count = await self.repository.count_recovery_administrators(
                policy_version=policy.version_no, now=now
            )
            if recovery_count == 0:
                compliance = await self._upsert_temporary_exemption(
                    user=user,
                    policy=policy,
                    reason="自动 break-glass：防止策略切换锁死全部管理员。",
                    expires_at=now + _BREAK_GLASS_WINDOW,
                )
                await self.repository.write_business_audit(
                    actor_user_id=user.id,
                    action="password_policy.break_glass",
                    object_type="account_password_compliance",
                    object_id=compliance.id,
                    reason=compliance.exemption_reason,
                    result_status="succeeded",
                    request_id=None,
                    metadata={"policy_version": policy.version_no, "expires_at": compliance.exemption_expires_at.isoformat() if compliance.exemption_expires_at else None},
                )
                return self._compliance_dto(compliance, policy.version_no, now)

        compliance = await self._upsert_remediation_required(
            user=user, current=compliance, policy=policy, now=now
        )
        return self._compliance_dto(compliance, policy.version_no, now)

    async def get_my_compliance(self, *, user: User) -> PasswordComplianceDTO:
        policy = await self.ensure_default_password_policy()
        now = datetime.now(UTC)
        compliance = await self.repository.get_compliance(user.id)
        if compliance is None:
            return PasswordComplianceDTO(
                user_id=user.id,
                evaluated_policy_version=0,
                required_policy_version=policy.version_no,
                status="remediation_required",
                remediation_due_at=None,
                last_notified_at=None,
                remediated_at=None,
                exemption_expires_at=None,
                notification_pending=True,
                login_allowed=False,
            )
        return self._compliance_dto(compliance, policy.version_no, now)

    async def change_own_password(
        self, *, user: User, payload: PasswordChangeRequest
    ) -> PasswordComplianceDTO:
        if not verify_password(payload.current_password, user.hashed_password):
            raise SecurityDomainError("PASSWORD_CHANGE_FORBIDDEN", "当前密码验证失败。", 403)
        policy = await self.validate_new_password(payload.new_password)
        now = datetime.now(UTC)
        # Only the freshly validated value is hashed and persisted.  Neither
        # cleartext request value enters an audit row or any security table.
        user.hashed_password = hash_password(payload.new_password)
        compliance = await self._mark_remediated(user=user, policy=policy, now=now)
        await self.repository.write_business_audit(
            actor_user_id=user.id,
            action="password_policy.change_self",
            object_type="account_password_compliance",
            object_id=compliance.id,
            reason=payload.reason.strip(),
            result_status="succeeded",
            request_id=None,
            metadata={"policy_version": policy.version_no, "status": compliance.status},
        )
        return self._compliance_dto(compliance, policy.version_no, now)

    async def reset_password_as_admin(
        self, *, actor: User, target_user_id: UUID, payload: PasswordResetRequest
    ) -> PasswordComplianceDTO:
        await self._require_security_admin(actor)
        target = await self.repository.get_user(target_user_id)
        if target is None or not target.is_active:
            raise SecurityDomainError("PASSWORD_CHANGE_FORBIDDEN", "目标账号不存在或已停用。", 404)
        policy = await self.validate_new_password(payload.new_password)
        now = datetime.now(UTC)
        target.hashed_password = hash_password(payload.new_password)
        compliance = await self._mark_remediated(
            user=target, policy=policy, now=now, updated_by=actor.id
        )
        await self.repository.write_business_audit(
            actor_user_id=actor.id,
            action="password_policy.admin_reset",
            object_type="account_password_compliance",
            object_id=compliance.id,
            reason=payload.reason.strip(),
            result_status="succeeded",
            request_id=None,
            metadata={"target_user_id": str(target.id), "policy_version": policy.version_no},
        )
        return self._compliance_dto(compliance, policy.version_no, now)

    async def grant_password_exemption(
        self, *, actor: User, target_user_id: UUID, payload: PasswordExemptionRequest
    ) -> PasswordComplianceDTO:
        await self._require_security_admin(actor)
        target = await self.repository.get_user(target_user_id)
        if target is None or not target.is_active:
            raise SecurityDomainError("BREAK_GLASS_REQUIRED", "目标账号不存在或已停用。", 404)
        policy = await self.ensure_default_password_policy()
        now = datetime.now(UTC)
        compliance = await self._upsert_temporary_exemption(
            user=target,
            policy=policy,
            reason=payload.reason.strip(),
            expires_at=now + timedelta(hours=payload.expires_in_hours),
            updated_by=actor.id,
        )
        await self.repository.write_business_audit(
            actor_user_id=actor.id,
            action="password_policy.grant_exemption",
            object_type="account_password_compliance",
            object_id=compliance.id,
            reason=payload.reason.strip(),
            result_status="succeeded",
            request_id=None,
            metadata={"target_user_id": str(target.id), "expires_at": compliance.exemption_expires_at.isoformat() if compliance.exemption_expires_at else None},
        )
        return self._compliance_dto(compliance, policy.version_no, now)

    async def create_password_policy(
        self, *, actor: User, payload: PasswordPolicyCreateRequest
    ) -> PasswordPolicyDTO:
        await self._require_security_admin(actor)
        rules = dict(payload.rules)
        # Validate shape with a harmless sentinel; composition requirements are
        # the same ones applied to an actual password at registration/change.
        self._validate_rules_shape(rules)
        policy = await self.repository.create_password_policy(
            version_no=await self.repository.next_password_policy_version(),
            rules_json=rules,
            status="draft",
            created_by=actor.id,
            activated_at=None,
            retired_at=None,
            note=payload.note.strip() if payload.note else None,
        )
        await self.repository.write_business_audit(
            actor_user_id=actor.id,
            action="password_policy.create",
            object_type="password_policy",
            object_id=policy.id,
            reason=policy.note,
            result_status="succeeded",
            request_id=None,
            metadata={"version": policy.version_no, "status": policy.status},
        )
        return self._policy_dto(policy)

    async def activate_password_policy(
        self, *, actor: User, policy_id: UUID, payload: PasswordPolicyActivateRequest
    ) -> PasswordPolicyDTO:
        await self._require_security_admin(actor)
        policy = await self.repository.get_password_policy(policy_id)
        if policy is None or policy.status == "retired":
            raise SecurityDomainError("PASSWORD_POLICY_VIOLATION", "密码策略不存在或已退役。", 404)
        self._validate_rules_shape(dict(policy.rules_json or {}))
        now = datetime.now(UTC)
        for existing in await self.repository.list_active_password_policies():
            if existing.id != policy.id:
                existing.status = "retired"
                existing.retired_at = now
        # Flush the retirement before activating the replacement.  The
        # partial unique index permits only one active policy, and SQLAlchemy
        # is not required to order separate row updates by business state.
        await self.repository.session.flush()
        policy.status = "active"
        policy.activated_at = now
        policy.retired_at = None
        await self.repository.session.flush()

        # Provision a bounded recovery route for the actor.  This is an
        # explicit exemption state, not an assertion that the old password
        # satisfies the new policy.
        await self._upsert_temporary_exemption(
            user=actor,
            policy=policy,
            reason="策略激活自动 break-glass；到期前必须完成改密。",
            expires_at=now + _BREAK_GLASS_WINDOW,
        )
        await self.repository.write_business_audit(
            actor_user_id=actor.id,
            action="password_policy.activate",
            object_type="password_policy",
            object_id=policy.id,
            reason=payload.reason.strip(),
            result_status="succeeded",
            request_id=None,
            metadata={"version": policy.version_no, "break_glass_hours": 24},
        )
        return self._policy_dto(policy)

    async def create_api_risk_rule(
        self, *, actor: User, payload: ApiRiskRuleCreateRequest
    ) -> ApiRiskRuleDTO:
        await self._require_security_admin(actor)
        rule = await self.repository.create_risk_rule(
            code=payload.code,
            version_no=await self.repository.next_risk_rule_version(payload.code),
            scope=payload.scope,
            predicate=dict(payload.predicate),
            threshold=payload.threshold,
            window_seconds=payload.window_seconds,
            action=payload.action,
            status="draft",
            created_by=actor.id,
            activated_at=None,
            retired_at=None,
        )
        await self.repository.write_business_audit(
            actor_user_id=actor.id,
            action="api_risk_rule.create",
            object_type="api_risk_rule",
            object_id=rule.id,
            reason="创建待激活 API 风险规则。",
            result_status="succeeded",
            request_id=None,
            metadata={"code": rule.code, "version": rule.version_no, "scope": rule.scope},
        )
        return self._rule_dto(rule)

    async def activate_api_risk_rule(
        self, *, actor: User, rule_id: UUID, payload: ApiRiskRuleActivateRequest
    ) -> ApiRiskRuleDTO:
        await self._require_security_admin(actor)
        rule = await self.repository.get_risk_rule(rule_id)
        if rule is None or rule.status == "retired":
            raise SecurityDomainError("RISK_RULE_INVALID", "风险规则不存在或已退役。", 404)
        now = datetime.now(UTC)
        for existing in await self.repository.list_active_risk_rules_by_code(rule.code):
            if existing.id != rule.id:
                existing.status = "retired"
                existing.retired_at = now
        # Retire the previous revision before the replacement reaches the
        # partial one-active-per-code index.
        await self.repository.session.flush()
        rule.status = "active"
        rule.activated_at = now
        rule.retired_at = None
        await self.repository.session.flush()
        await self.repository.write_business_audit(
            actor_user_id=actor.id,
            action="api_risk_rule.activate",
            object_type="api_risk_rule",
            object_id=rule.id,
            reason=payload.reason.strip(),
            result_status="succeeded",
            request_id=None,
            metadata={"code": rule.code, "version": rule.version_no},
        )
        return self._rule_dto(rule)

    async def observe_redacted_request(
        self, observation: RedactedRequestObservation
    ) -> RiskDecision:
        """Persist a redacted event, calculate active rules, and return the strongest outcome."""

        now = datetime.now(UTC)
        audit = await self.repository.create_request_audit(
            occurred_at=now,
            route_template=observation.route_template,
            method=observation.method.upper(),
            outcome_status=0,
            actor_user_id=observation.actor_user_id,
            ip_hash=observation.ip_hash,
            device_hash=observation.device_hash,
            rate_bucket=observation.rate_bucket,
            request_size_bucket=observation.request_size_bucket,
            correlation_id=observation.correlation_id,
            redaction_version=observation.redaction_version,
            expires_at=now + timedelta(days=30),
        )
        strongest = "allow"
        primary_event_id: UUID | None = None
        primary_explanation: dict[str, Any] = {"matched_rules": 0}
        precedence = {"allow": 0, "throttle": 1, "block": 2}

        for rule in await self.repository.get_active_risk_rules():
            predicate = dict(rule.predicate or {})
            if not self._rule_matches_request(rule, observation):
                continue
            count = await self.repository.count_windowed_requests(
                scope=rule.scope,
                actor_user_id=observation.actor_user_id,
                ip_hash=observation.ip_hash,
                device_hash=observation.device_hash,
                route_template=observation.route_template,
                method=observation.method.upper(),
                window_start=now - timedelta(seconds=rule.window_seconds),
                predicate=predicate,
            )
            if count < rule.threshold:
                continue
            decision = {"alert": "allow", "throttle": "throttle", "block": "block"}[rule.action]
            severity = {"alert": "medium", "throttle": "high", "block": "critical"}[rule.action]
            event_status = "alerted" if rule.action == "alert" else "mitigated"
            explanation = {
                "rule_code": rule.code,
                "rule_version": rule.version_no,
                "scope": rule.scope,
                "matched_count": count,
                "threshold": rule.threshold,
                "window_seconds": rule.window_seconds,
                "route_template": observation.route_template,
                "method": observation.method.upper(),
                "redaction_version": observation.redaction_version,
            }
            event = await self.repository.create_risk_event(
                request_audit_id=audit.id,
                rule_id=rule.id,
                baseline_version=f"{rule.code}:v{rule.version_no}",
                severity=severity,
                explanation=explanation,
                decision=decision,
                status=event_status,
                opened_at=now,
            )
            await self.repository.create_risk_action(
                risk_event_id=event.id,
                action=rule.action,
                actor_user_id=None,
                reason="脱敏请求窗口达到已激活规则阈值。",
                result="automatic",
                metadata_={"rule_code": rule.code, "matched_count": count, "threshold": rule.threshold},
                created_at=now,
            )
            if precedence[decision] >= precedence[strongest]:
                strongest = decision
                primary_event_id = event.id
                primary_explanation = explanation

        return RiskDecision(
            audit_id=audit.id,
            decision=strongest,
            risk_event_id=primary_event_id,
            explanation=primary_explanation,
        )

    async def complete_request_audit(self, *, audit_id: UUID, outcome_status: int) -> None:
        audit = await self.repository.session.get(ApiRequestAuditEvent, audit_id)
        if audit is not None:
            audit.outcome_status = max(0, min(int(outcome_status), 599))
            await self.repository.session.flush()

    async def list_api_risk_events(self, *, actor: User) -> list[ApiRiskEventDTO]:
        await self._require_security_admin(actor)
        return [await self._event_dto(event) for event in await self.repository.list_risk_events()]

    async def release_api_risk_event(
        self, *, actor: User, event_id: UUID, payload: ApiRiskReleaseRequest
    ) -> ApiRiskEventDTO:
        await self._require_security_admin(actor)
        event = await self.repository.get_risk_event(event_id)
        if event is None:
            raise SecurityDomainError("RISK_RELEASE_FORBIDDEN", "风险事件不存在。", 404)
        now = datetime.now(UTC)
        event.status = "released"
        event.decision = "released"
        await self.repository.session.flush()
        await self.repository.create_risk_action(
            risk_event_id=event.id,
            action="release",
            actor_user_id=actor.id,
            reason=payload.reason.strip(),
            result="succeeded",
            metadata_={"manual": True},
            created_at=now,
        )
        await self.repository.write_business_audit(
            actor_user_id=actor.id,
            action="api_risk_event.release",
            object_type="api_risk_event",
            object_id=event.id,
            reason=payload.reason.strip(),
            result_status="succeeded",
            request_id=None,
            metadata={"previous_decision": event.explanation.get("rule_code") if event.explanation else None},
        )
        return await self._event_dto(event)

    async def review_api_risk_event(
        self, *, actor: User, event_id: UUID, payload: ApiRiskReviewRequest
    ) -> ApiRiskEventDTO:
        await self._require_security_admin(actor)
        event = await self.repository.get_risk_event(event_id)
        if event is None:
            raise SecurityDomainError("RISK_RELEASE_FORBIDDEN", "风险事件不存在。", 404)
        now = datetime.now(UTC)
        if payload.disposition == "false_positive":
            event.status = "false_positive"
            event.decision = "allow"
        elif payload.disposition == "false_negative":
            # Preserve the original explainable event while labeling the
            # assessor's retrospective finding.  It does not punish a user.
            event.status = "observed"
        await self.repository.session.flush()
        await self.repository.create_risk_action(
            risk_event_id=event.id,
            action="review",
            actor_user_id=actor.id,
            reason=payload.reason.strip(),
            result=payload.disposition,
            metadata_={"manual": True},
            created_at=now,
        )
        await self.repository.write_business_audit(
            actor_user_id=actor.id,
            action="api_risk_event.review",
            object_type="api_risk_event",
            object_id=event.id,
            reason=payload.reason.strip(),
            result_status=payload.disposition,
            request_id=None,
            metadata={"disposition": payload.disposition},
        )
        return await self._event_dto(event)

    async def _mark_remediated(
        self,
        *,
        user: User,
        policy: PasswordPolicy,
        now: datetime,
        updated_by: UUID | None = None,
    ) -> AccountPasswordCompliance:
        compliance = await self.repository.get_compliance(user.id)
        actor_id = updated_by or user.id
        if compliance is None:
            compliance = await self.repository.create_compliance(
                user_id=user.id,
                evaluated_policy_version=policy.version_no,
                status="remediated",
                remediation_due_at=None,
                last_notified_at=None,
                remediated_at=now,
                exemption_expires_at=None,
                updated_by=actor_id,
                exemption_reason=None,
            )
        else:
            compliance.evaluated_policy_version = policy.version_no
            compliance.status = "remediated"
            compliance.remediation_due_at = None
            compliance.remediated_at = now
            compliance.exemption_expires_at = None
            compliance.updated_by = actor_id
            compliance.exemption_reason = None
            await self.repository.session.flush()
        return compliance

    async def _upsert_remediation_required(
        self,
        *,
        user: User,
        current: AccountPasswordCompliance | None,
        policy: PasswordPolicy,
        now: datetime,
    ) -> AccountPasswordCompliance:
        original_version = current.evaluated_policy_version if current is not None else 0
        if current is None:
            current = await self.repository.create_compliance(
                user_id=user.id,
                evaluated_policy_version=original_version,
                status="remediation_required",
                remediation_due_at=now + _REMEDIATION_WINDOW,
                last_notified_at=now,
                remediated_at=None,
                exemption_expires_at=None,
                updated_by=user.id,
                exemption_reason=None,
            )
        else:
            current.status = "remediation_required"
            current.remediation_due_at = now + _REMEDIATION_WINDOW
            current.exemption_expires_at = None
            current.exemption_reason = None
            current.updated_by = user.id
            if current.last_notified_at is None or _utc(current.last_notified_at) <= now - timedelta(days=1):
                current.last_notified_at = now
            await self.repository.session.flush()
        await self.repository.write_business_audit(
            actor_user_id=user.id,
            action="password_policy.remediation_notice",
            object_type="account_password_compliance",
            object_id=current.id,
            reason="账号记录的已评估策略版本落后于当前版本；未读取密码哈希。",
            result_status="remediation_required",
            request_id=None,
            metadata={
                "evaluated_policy_version": original_version,
                "required_policy_version": policy.version_no,
                "notification_at": current.last_notified_at.isoformat() if current.last_notified_at else None,
            },
        )
        return current

    async def _upsert_temporary_exemption(
        self,
        *,
        user: User,
        policy: PasswordPolicy,
        reason: str,
        expires_at: datetime,
        updated_by: UUID | None = None,
    ) -> AccountPasswordCompliance:
        compliance = await self.repository.get_compliance(user.id)
        if compliance is None:
            compliance = await self.repository.create_compliance(
                user_id=user.id,
                evaluated_policy_version=policy.version_no,
                status="temporarily_exempt",
                remediation_due_at=expires_at,
                last_notified_at=datetime.now(UTC),
                remediated_at=None,
                exemption_expires_at=expires_at,
                updated_by=updated_by or user.id,
                exemption_reason=reason,
            )
        else:
            compliance.evaluated_policy_version = policy.version_no
            compliance.status = "temporarily_exempt"
            compliance.remediation_due_at = expires_at
            compliance.last_notified_at = datetime.now(UTC)
            compliance.exemption_expires_at = expires_at
            compliance.updated_by = updated_by or user.id
            compliance.exemption_reason = reason
            await self.repository.session.flush()
        return compliance

    async def _require_security_admin(self, actor: User) -> None:
        if not await self.repository.is_security_admin(actor.id):
            raise SecurityDomainError("ADMIN_ROLE_REQUIRED", "当前账号不具备安全治理管理员权限。")

    @staticmethod
    def _allows_login(
        compliance: AccountPasswordCompliance | None, policy_version: int, now: datetime
    ) -> bool:
        if compliance is None or compliance.evaluated_policy_version != policy_version:
            return False
        if compliance.status in {"compliant", "remediated"}:
            return True
        return (
            compliance.status == "temporarily_exempt"
            and (_utc(compliance.exemption_expires_at) or now) > now
        )

    @staticmethod
    def _validate_rules_shape(rules: dict[str, Any]) -> None:
        unexpected = set(rules) - _VALID_RULE_KEYS
        if unexpected:
            raise SecurityDomainError(
                "PASSWORD_POLICY_VIOLATION",
                f"密码策略包含未受支持字段: {', '.join(sorted(unexpected))}",
                400,
            )
        min_length = rules.get("min_length", DEFAULT_PASSWORD_RULES["min_length"])
        max_length = rules.get("max_length", DEFAULT_PASSWORD_RULES["max_length"])
        try:
            min_length = int(min_length)
            max_length = int(max_length)
        except (TypeError, ValueError) as exc:
            raise SecurityDomainError("PASSWORD_POLICY_VIOLATION", "密码策略长度配置无效。", 400) from exc
        if min_length < 8 or max_length > 72 or min_length > max_length:
            raise SecurityDomainError("PASSWORD_POLICY_VIOLATION", "密码策略长度范围无效。", 400)
        for key in ("require_upper", "require_lower", "require_digit", "require_symbol"):
            if key in rules and not isinstance(rules[key], bool):
                raise SecurityDomainError("PASSWORD_POLICY_VIOLATION", f"{key} 必须是布尔值。", 400)

    @staticmethod
    def _rule_matches_request(rule: ApiRiskRule, observation: RedactedRequestObservation) -> bool:
        predicate = dict(rule.predicate or {})
        route_template = predicate.get("route_template")
        if isinstance(route_template, str) and route_template and route_template != observation.route_template:
            return False
        route_prefix = predicate.get("route_prefix")
        if isinstance(route_prefix, str) and route_prefix and not observation.route_template.startswith(route_prefix):
            return False
        method = predicate.get("method")
        return not isinstance(method, str) or not method or method.upper() == observation.method.upper()

    @staticmethod
    def _policy_dto(policy: PasswordPolicy) -> PasswordPolicyDTO:
        return PasswordPolicyDTO(
            id=policy.id,
            version_no=policy.version_no,
            rules=dict(policy.rules_json or {}),
            status=policy.status,  # type: ignore[arg-type]
            activated_at=policy.activated_at,
            retired_at=policy.retired_at,
            note=policy.note,
        )

    @staticmethod
    def _rule_dto(rule: ApiRiskRule) -> ApiRiskRuleDTO:
        return ApiRiskRuleDTO(
            id=rule.id,
            code=rule.code,
            version_no=rule.version_no,
            scope=rule.scope,  # type: ignore[arg-type]
            predicate=dict(rule.predicate or {}),
            threshold=rule.threshold,
            window_seconds=rule.window_seconds,
            action=rule.action,  # type: ignore[arg-type]
            status=rule.status,  # type: ignore[arg-type]
            activated_at=rule.activated_at,
        )

    @staticmethod
    def _compliance_dto(
        compliance: AccountPasswordCompliance, required_policy_version: int, now: datetime
    ) -> PasswordComplianceDTO:
        login_allowed = SecurityGovernanceService._allows_login(
            compliance, required_policy_version, now
        )
        return PasswordComplianceDTO(
            user_id=compliance.user_id,
            evaluated_policy_version=compliance.evaluated_policy_version,
            required_policy_version=required_policy_version,
            status=compliance.status,  # type: ignore[arg-type]
            remediation_due_at=compliance.remediation_due_at,
            last_notified_at=compliance.last_notified_at,
            remediated_at=compliance.remediated_at,
            exemption_expires_at=compliance.exemption_expires_at,
            notification_pending=(compliance.status == "remediation_required"),
            login_allowed=login_allowed,
        )

    async def _event_dto(self, event: ApiRiskEvent) -> ApiRiskEventDTO:
        return ApiRiskEventDTO(
            id=event.id,
            request_audit_id=event.request_audit_id,
            rule_id=event.rule_id,
            baseline_version=event.baseline_version,
            severity=event.severity,  # type: ignore[arg-type]
            explanation=dict(event.explanation or {}),
            decision=event.decision,  # type: ignore[arg-type]
            status=event.status,  # type: ignore[arg-type]
            opened_at=event.opened_at,
            actions=[self._action_dto(action) for action in await self.repository.list_risk_actions(event.id)],
        )

    @staticmethod
    def _action_dto(action: ApiRiskAction) -> ApiRiskActionDTO:
        return ApiRiskActionDTO(
            id=action.id,
            action=action.action,  # type: ignore[arg-type]
            actor_user_id=action.actor_user_id,
            reason=action.reason,
            result=action.result,  # type: ignore[arg-type]
            created_at=action.created_at,
        )
