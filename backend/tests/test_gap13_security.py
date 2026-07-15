# Status: real

"""Focused T5 evidence: password remediation and redacted API-risk replay."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.auth.security import hash_password
from app.core.config import Settings
from app.db.models.education.education_domain import GovernanceAuditEvent
from app.db.models.governance.governance import RoleDefinition, UserRoleGrant
from app.db.models.identity.user import User
from app.db.models.security.account_security import AccountPasswordCompliance, ApiRequestAuditEvent
from app.repositories.identity.users import UserRepository
from app.schemas.auth import LoginRequest, PasswordRemediationRequest, RegisterRequest
from app.schemas.security import (
    ApiRiskReleaseRequest,
    ApiRiskReviewRequest,
    ApiRiskRuleActivateRequest,
    ApiRiskRuleCreateRequest,
    PasswordPolicyActivateRequest,
    PasswordPolicyCreateRequest,
    PasswordResetRequest,
)
from app.services.governance.governance_service import GovernanceService
from app.services.identity.auth_service import AuthService
from app.services.security.security_service import (
    RedactedRequestObservation,
    SecurityDomainError,
    SecurityGovernanceService,
    opaque_identifier_hash,
)


@pytest.mark.anyio
async def test_gap13_security_password_remediation_and_api_risk_replay(sqlite_session) -> None:
    """Exercise normal/attack samples without storing their raw credentials or IDs."""

    administrator = User(
        id=uuid4(),
        email="gap13-security-admin@example.test",
        display_name="T5 安全管理员",
        hashed_password=hash_password("LegacyPass1!"),
        role="course_teacher",
    )
    legacy_user = User(
        id=uuid4(),
        email="gap13-legacy@example.test",
        display_name="待整改账号",
        hashed_password=hash_password("LegacyPass1!"),
        role="student",
    )
    reset_target = User(
        id=uuid4(),
        email="gap13-reset@example.test",
        display_name="管理员重置目标",
        hashed_password=hash_password("LegacyPass1!"),
        role="student",
    )
    sqlite_session.add_all([administrator, legacy_user, reset_target])
    await sqlite_session.flush()

    governance = GovernanceService(sqlite_session)
    await governance.ensure_default_definitions()
    admin_role = await sqlite_session.scalar(
        select(RoleDefinition).where(RoleDefinition.code == "administrator", RoleDefinition.status == "active")
    )
    assert admin_role is not None
    sqlite_session.add(
        UserRoleGrant(
            id=uuid4(),
            user_id=administrator.id,
            role_id=admin_role.id,
            granted_by=administrator.id,
            granted_at=datetime.now(UTC),
            status="active",
            reason="T5 focused security governance bootstrap",
        )
    )
    await sqlite_session.flush()

    security = SecurityGovernanceService(sqlite_session)
    baseline = await security.ensure_default_password_policy()
    draft = await security.create_password_policy(
        actor=administrator,
        payload=PasswordPolicyCreateRequest(
            rules={
                "min_length": 14,
                "max_length": 72,
                "require_upper": True,
                "require_lower": True,
                "require_digit": True,
                "require_symbol": True,
            },
            note="T5 staged policy strengthens the baseline.",
        ),
    )
    active = await security.activate_password_policy(
        actor=administrator,
        policy_id=draft.id,
        payload=PasswordPolicyActivateRequest(reason="启用新版弱口令整改策略。"),
    )
    assert active.version_no > baseline.version_no

    # A policy activation gives the final active administrator an explicit,
    # time-bounded recovery route instead of locking every administrator.
    admin_state = await security.evaluate_login_compliance(user=administrator)
    assert admin_state.status == "temporarily_exempt"
    assert admin_state.login_allowed is True
    assert admin_state.exemption_expires_at is not None

    auth = AuthService(sqlite_session, Settings())
    with pytest.raises(HTTPException) as legacy_denied:
        await auth.login(LoginRequest(email=legacy_user.email, password="LegacyPass1!"))
    assert legacy_denied.value.detail["code"] == "PASSWORD_REMEDIATION_REQUIRED"
    legacy_state = await security.get_my_compliance(user=legacy_user)
    assert legacy_state.status == "remediation_required"
    assert legacy_state.evaluated_policy_version == 0
    assert legacy_state.required_policy_version == active.version_no
    assert legacy_state.notification_pending is True

    remediated = await auth.remediate_password(
        PasswordRemediationRequest(
            email=legacy_user.email,
            current_password="LegacyPass1!",
            new_password="RemediatedPass1!",
            reason="完成新版密码策略整改。",
        ),
    )
    assert remediated.status == "remediated"
    assert remediated.login_allowed is True
    login = await auth.login(LoginRequest(email=legacy_user.email, password="RemediatedPass1!"))
    assert login.access_token

    # Registration receives the active policy in real AuthService flow, and
    # administrators can reset without ever exposing a hash in compliance data.
    registered = await auth.register(
        RegisterRequest(
            email="gap13-fresh@example.test",
            password="FreshRegistration1!",
            display_name="新注册整改合规账号",
        )
    )
    fresh_user = await UserRepository(sqlite_session).get_by_id(registered.user.id)
    assert fresh_user is not None
    fresh_state = await security.get_my_compliance(user=fresh_user)
    assert fresh_state.status == "compliant"
    with pytest.raises(HTTPException) as compliant_account_denied:
        await auth.remediate_password(
            PasswordRemediationRequest(
                email=fresh_user.email,
                current_password="FreshRegistration1!",
                new_password="AnonymousRouteDenied1!",
            )
        )
    assert compliant_account_denied.value.status_code == 409
    assert compliant_account_denied.value.detail["code"] == "PASSWORD_REMEDIATION_NOT_REQUIRED"

    reset_state = await security.reset_password_as_admin(
        actor=administrator,
        target_user_id=reset_target.id,
        payload=PasswordResetRequest(
            new_password="AdminResetPass1!",
            reason="管理员在身份核验后执行最小恢复重置。",
        ),
    )
    assert reset_state.status == "remediated"

    with pytest.raises(SecurityDomainError) as non_admin:
        await security.create_api_risk_rule(
            actor=legacy_user,
            payload=ApiRiskRuleCreateRequest(
                code="unauthorized-rule",
                scope="ip",
                predicate={"route_template": "/api/v1/risk"},
                threshold=1,
                action="block",
            ),
        )
    assert non_admin.value.code == "ADMIN_ROLE_REQUIRED"

    block_rule = await security.create_api_risk_rule(
        actor=administrator,
        payload=ApiRiskRuleCreateRequest(
            code="gap13-ip-burst",
            scope="ip",
            predicate={"route_template": "/api/v1/assessments/submit", "method": "POST"},
            threshold=2,
            window_seconds=60,
            action="block",
        ),
    )
    await security.activate_api_risk_rule(
        actor=administrator,
        rule_id=block_rule.id,
        payload=ApiRiskRuleActivateRequest(reason="启用可解释的攻击样本阻断阈值。"),
    )
    secret = "focused-test-redaction-pepper"
    normal_ip = "198.51.100.10"
    attack_ip = "203.0.113.77"
    normal = await security.observe_redacted_request(
        RedactedRequestObservation(
            route_template="/api/v1/courses",
            method="GET",
            actor_user_id=fresh_user.id,
            ip_hash=opaque_identifier_hash(normal_ip, secret=secret),
            device_hash=opaque_identifier_hash("normal-device", secret=secret),
            rate_bucket="202607151820",
            request_size_bucket="0-1KiB",
            correlation_id="gap13-normal-001",
        )
    )
    assert normal.decision == "allow" and normal.risk_event_id is None

    attack_observation = RedactedRequestObservation(
        route_template="/api/v1/assessments/submit",
        method="POST",
        actor_user_id=legacy_user.id,
        ip_hash=opaque_identifier_hash(attack_ip, secret=secret),
        device_hash=opaque_identifier_hash("attack-device", secret=secret),
        rate_bucket="202607151820",
        request_size_bucket="1-16KiB",
        correlation_id="gap13-attack-001",
    )
    first_attack = await security.observe_redacted_request(attack_observation)
    second_attack = await security.observe_redacted_request(attack_observation)
    assert first_attack.decision == "allow"
    assert second_attack.decision == "block"
    assert second_attack.risk_event_id is not None
    await security.complete_request_audit(audit_id=second_attack.audit_id, outcome_status=403)

    released = await security.release_api_risk_event(
        actor=administrator,
        event_id=second_attack.risk_event_id,
        payload=ApiRiskReleaseRequest(reason="管理员复核后解除本次阻断，保留完整回放。"),
    )
    assert released.status == "released"
    false_positive = await security.review_api_risk_event(
        actor=administrator,
        event_id=second_attack.risk_event_id,
        payload=ApiRiskReviewRequest(
            disposition="false_positive", reason="最小攻击样本的人工误报标注演练。"
        ),
    )
    assert false_positive.status == "false_positive"

    alert_rule = await security.create_api_risk_rule(
        actor=administrator,
        payload=ApiRiskRuleCreateRequest(
            code="gap13-retrospective-alert",
            scope="api",
            predicate={"route_template": "/api/v1/risk-retrospective", "method": "POST"},
            threshold=1,
            action="alert",
        ),
    )
    await security.activate_api_risk_rule(
        actor=administrator,
        rule_id=alert_rule.id,
        payload=ApiRiskRuleActivateRequest(reason="记录仅告警样本以支持漏报复核。"),
    )
    retrospective = await security.observe_redacted_request(
        RedactedRequestObservation(
            route_template="/api/v1/risk-retrospective",
            method="POST",
            actor_user_id=legacy_user.id,
            ip_hash=opaque_identifier_hash(attack_ip, secret=secret),
            device_hash=opaque_identifier_hash("attack-device", secret=secret),
            rate_bucket="202607151820",
            request_size_bucket="0-1KiB",
            correlation_id="gap13-retrospective-001",
        )
    )
    assert retrospective.decision == "allow" and retrospective.risk_event_id is not None
    false_negative = await security.review_api_risk_event(
        actor=administrator,
        event_id=retrospective.risk_event_id,
        payload=ApiRiskReviewRequest(
            disposition="false_negative", reason="人工复核确认仅告警未能阻止该攻击样本。"
        ),
    )
    assert any(action.result == "false_negative" for action in false_negative.actions)

    audit_rows = (await sqlite_session.execute(select(ApiRequestAuditEvent))).scalars().all()
    assert audit_rows
    persisted_text = "\n".join(repr(row.__dict__) for row in audit_rows)
    assert normal_ip not in persisted_text and attack_ip not in persisted_text
    assert "normal-device" not in persisted_text and "attack-device" not in persisted_text
    assert "Authorization" not in persisted_text and "Cookie" not in persisted_text
    assert not hasattr((await sqlite_session.scalar(select(AccountPasswordCompliance))), "password")

    business_audits = (await sqlite_session.execute(select(GovernanceAuditEvent))).scalars().all()
    actions = {row.action for row in business_audits}
    assert {
        "password_policy.activate",
        "password_policy.remediation_notice",
        "password_policy.change_self",
        "password_policy.admin_reset",
        "api_risk_rule.activate",
        "api_risk_event.release",
        "api_risk_event.review",
    } <= actions
