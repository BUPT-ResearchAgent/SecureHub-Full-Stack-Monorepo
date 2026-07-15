# Status: real

"""Idempotent seed for demo identities, policy state, and the student persona."""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.db.models.identity.user import User
from app.db.seeds._constants import (
    DEMO_ACCOUNTS,
    DEMO_USER_CAPABILITIES,
    DEMO_USER_DIMENSIONS,
    DEMO_USER_ID,
    DEMO_USER_PASSWORD,
    SECURITY_REMEDIATION_DEMO_USER_EMAIL,
    SECURITY_REMEDIATION_DEMO_USER_ID,
    SECURITY_REMEDIATION_DEMO_USER_NAME,
    SECURITY_REMEDIATION_DEMO_USER_PASSWORD,
)
from app.db.session import get_sessionmaker
from app.repositories.identity.capabilities import UserCapabilityRepository
from app.repositories.identity.profiles import UserProfileRepository
from app.repositories.identity.users import UserRepository
from app.services.security.security_service import SecurityGovernanceService


async def _seed_remediation_demo(
    *,
    session: AsyncSession,
    users: UserRepository,
    security: SecurityGovernanceService,
) -> None:
    """Reset the explicit local remediation fixture without reading a hash."""

    user = await users.get_by_id(SECURITY_REMEDIATION_DEMO_USER_ID)
    if user is None:
        user = await users.get_by_email(SECURITY_REMEDIATION_DEMO_USER_EMAIL)
    if user is None:
        user = await users.create(
            user_id=SECURITY_REMEDIATION_DEMO_USER_ID,
            email=SECURITY_REMEDIATION_DEMO_USER_EMAIL,
            display_name=SECURITY_REMEDIATION_DEMO_USER_NAME,
            hashed_password=hash_password(SECURITY_REMEDIATION_DEMO_USER_PASSWORD),
            is_active=True,
            role="student",
        )
    else:
        user.email = SECURITY_REMEDIATION_DEMO_USER_EMAIL
        user.display_name = SECURITY_REMEDIATION_DEMO_USER_NAME
        user.hashed_password = hash_password(SECURITY_REMEDIATION_DEMO_USER_PASSWORD)
        user.is_active = True
        user.role = "student"
        await session.flush()

    compliance = await security.repository.get_compliance(user.id)
    reset_required = (
        compliance is None
        or compliance.evaluated_policy_version != 0
        or compliance.status != "remediation_required"
    )
    if not reset_required:
        return

    # The seed author knows it just installed the intentionally legacy
    # plaintext fixture.  It records a legacy version state directly rather
    # than inferring anything from ``users.hashed_password``.
    if compliance is not None:
        compliance.evaluated_policy_version = 0
        compliance.status = "remediation_required"
        compliance.remediation_due_at = None
        compliance.last_notified_at = None
        compliance.remediated_at = None
        compliance.exemption_expires_at = None
        compliance.updated_by = user.id
        compliance.exemption_reason = None
        await session.flush()

    # The seeded state is explicit: it does not call normal login evaluation
    # (which may need administrator-governance tables) and never infers a
    # policy result from the password hash.
    policy = await security.ensure_default_password_policy()
    now = datetime.now(UTC)
    if compliance is None:
        compliance = await security.repository.create_compliance(
            user_id=user.id,
            evaluated_policy_version=0,
            status="remediation_required",
            remediation_due_at=now + timedelta(days=7),
            last_notified_at=now,
            remediated_at=None,
            exemption_expires_at=None,
            updated_by=user.id,
            exemption_reason=None,
        )
    else:
        compliance.evaluated_policy_version = 0
        compliance.status = "remediation_required"
        compliance.remediation_due_at = now + timedelta(days=7)
        compliance.last_notified_at = now
        compliance.remediated_at = None
        compliance.exemption_expires_at = None
        compliance.updated_by = user.id
        compliance.exemption_reason = None
        await session.flush()
    await security.repository.write_business_audit(
        actor_user_id=user.id,
        action="password_policy.seed_remediation_demo",
        object_type="account_password_compliance",
        object_id=compliance.id,
        reason="受控本地演示种子显式标记为旧策略账号；未读取密码哈希。",
        result_status="remediation_required",
        request_id=None,
        metadata={
            "evaluated_policy_version": 0,
            "required_policy_version": policy.version_no,
            "fixture": "local_password_remediation_demo",
        },
    )


async def _seed(session: AsyncSession) -> None:
    users = UserRepository(session)
    profiles = UserProfileRepository(session)
    caps = UserCapabilityRepository(session)
    security = SecurityGovernanceService(session)

    for role, user_id, email, display_name in DEMO_ACCOUNTS:
        user = await users.get_by_id(user_id)
        if user is None:
            user = await users.get_by_email(email)
        if user is None:
            await users.create(
                user_id=user_id,
                email=email,
                display_name=display_name,
                hashed_password=hash_password(DEMO_USER_PASSWORD),
                is_active=True,
                role=role,
            )
            continue

        user.email = email
        user.display_name = display_name
        user.hashed_password = hash_password(DEMO_USER_PASSWORD)
        user.is_active = True
        user.role = role
        await session.flush()

    # The regular presentation accounts all use a known seed plaintext.  It
    # is validated against the active policy before their policy-version state
    # is marked compliant; no password hash is read, scanned, or inferred.
    policy = await security.validate_new_password(DEMO_USER_PASSWORD)
    for _role, user_id, _email, _display_name in DEMO_ACCOUNTS:
        user = await users.get_by_id(user_id)
        assert user is not None
        compliance = await security.repository.get_compliance(user.id)
        if (
            compliance is None
            or compliance.evaluated_policy_version != policy.version_no
            or compliance.status not in {"compliant", "remediated"}
        ):
            await security.register_compliant_password(user=user, policy=policy)

    await _seed_remediation_demo(session=session, users=users, security=security)

    await profiles.upsert(user_id=DEMO_USER_ID, dimensions=DEMO_USER_DIMENSIONS)

    for dimension, score, confidence in DEMO_USER_CAPABILITIES:
        await caps.upsert_score(
            user_id=DEMO_USER_ID,
            dimension=dimension,
            score=score,
            confidence=confidence,
            evidence_count=0,
        )


async def run(session: AsyncSession | None = None) -> int:
    if session is not None:
        await _seed(session)
        return len(DEMO_USER_CAPABILITIES)

    sm = get_sessionmaker()
    async with sm() as own_session:
        await _seed(own_session)
        await own_session.commit()
    return len(DEMO_USER_CAPABILITIES)


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(run())
