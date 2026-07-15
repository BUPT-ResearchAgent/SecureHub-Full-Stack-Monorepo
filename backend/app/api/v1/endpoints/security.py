# Status: real

"""T5 HTTP adapters for password remediation and API-risk governance."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.deps import RequiredCurrentUserDep, SessionDep
from app.schemas.security import (
    ApiRiskEventDTO,
    ApiRiskEventListDTO,
    ApiRiskReleaseRequest,
    ApiRiskReviewRequest,
    ApiRiskRuleActivateRequest,
    ApiRiskRuleCreateRequest,
    ApiRiskRuleDTO,
    PasswordComplianceDTO,
    PasswordExemptionRequest,
    PasswordPolicyActivateRequest,
    PasswordPolicyCreateRequest,
    PasswordPolicyDTO,
    PasswordResetRequest,
)
from app.services.security.security_service import SecurityDomainError, SecurityGovernanceService

router = APIRouter(prefix="/security")


def _raise_domain_error(error: SecurityDomainError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    ) from error


@router.get("/password-compliance/me", response_model=PasswordComplianceDTO)
async def get_my_password_compliance(
    session: SessionDep, user: RequiredCurrentUserDep
) -> PasswordComplianceDTO:
    try:
        result = await SecurityGovernanceService(session).get_my_compliance(user=user)
        await session.commit()
        return result
    except SecurityDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/password-policies", response_model=PasswordPolicyDTO, status_code=201)
async def create_password_policy(
    payload: PasswordPolicyCreateRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> PasswordPolicyDTO:
    try:
        result = await SecurityGovernanceService(session).create_password_policy(
            actor=user, payload=payload
        )
        await session.commit()
        return result
    except SecurityDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/password-policies/{policy_id}/activate", response_model=PasswordPolicyDTO)
async def activate_password_policy(
    policy_id: UUID,
    payload: PasswordPolicyActivateRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> PasswordPolicyDTO:
    try:
        result = await SecurityGovernanceService(session).activate_password_policy(
            actor=user, policy_id=policy_id, payload=payload
        )
        await session.commit()
        return result
    except SecurityDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/password-compliance/{user_id}/exemption", response_model=PasswordComplianceDTO)
async def grant_password_exemption(
    user_id: UUID,
    payload: PasswordExemptionRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> PasswordComplianceDTO:
    try:
        result = await SecurityGovernanceService(session).grant_password_exemption(
            actor=user, target_user_id=user_id, payload=payload
        )
        await session.commit()
        return result
    except SecurityDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/password-compliance/{user_id}/reset", response_model=PasswordComplianceDTO)
async def reset_password_as_admin(
    user_id: UUID,
    payload: PasswordResetRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> PasswordComplianceDTO:
    try:
        result = await SecurityGovernanceService(session).reset_password_as_admin(
            actor=user, target_user_id=user_id, payload=payload
        )
        await session.commit()
        return result
    except SecurityDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/api-risk/rules", response_model=ApiRiskRuleDTO, status_code=201)
async def create_api_risk_rule(
    payload: ApiRiskRuleCreateRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> ApiRiskRuleDTO:
    try:
        result = await SecurityGovernanceService(session).create_api_risk_rule(actor=user, payload=payload)
        await session.commit()
        return result
    except SecurityDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/api-risk/rules/{rule_id}/activate", response_model=ApiRiskRuleDTO)
async def activate_api_risk_rule(
    rule_id: UUID,
    payload: ApiRiskRuleActivateRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> ApiRiskRuleDTO:
    try:
        result = await SecurityGovernanceService(session).activate_api_risk_rule(
            actor=user, rule_id=rule_id, payload=payload
        )
        await session.commit()
        return result
    except SecurityDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.get("/api-risk/events", response_model=ApiRiskEventListDTO)
async def list_api_risk_events(
    session: SessionDep, user: RequiredCurrentUserDep
) -> ApiRiskEventListDTO:
    try:
        return ApiRiskEventListDTO(
            items=await SecurityGovernanceService(session).list_api_risk_events(actor=user)
        )
    except SecurityDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/api-risk/events/{event_id}/release", response_model=ApiRiskEventDTO)
async def release_api_risk_event(
    event_id: UUID,
    payload: ApiRiskReleaseRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> ApiRiskEventDTO:
    try:
        result = await SecurityGovernanceService(session).release_api_risk_event(
            actor=user, event_id=event_id, payload=payload
        )
        await session.commit()
        return result
    except SecurityDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/api-risk/events/{event_id}/review", response_model=ApiRiskEventDTO)
async def review_api_risk_event(
    event_id: UUID,
    payload: ApiRiskReviewRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> ApiRiskEventDTO:
    try:
        result = await SecurityGovernanceService(session).review_api_risk_event(
            actor=user, event_id=event_id, payload=payload
        )
        await session.commit()
        return result
    except SecurityDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


__all__ = ["router"]
