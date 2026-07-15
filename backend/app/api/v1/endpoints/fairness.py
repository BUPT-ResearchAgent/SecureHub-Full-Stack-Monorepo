# Status: real

"""Consent-gated fairness monitoring, reviews, and appeals HTTP adapters."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.deps import RequiredCurrentUserDep, SessionDep
from app.schemas.fairness import (
    AppealableGradeListDTO,
    FairnessAppealCreateRequest,
    FairnessAppealDTO,
    FairnessAppealListDTO,
    FairnessAppealResolveRequest,
    FairnessConsentDTO,
    FairnessConsentRequest,
    FairnessConsentWithdrawRequest,
    FairnessDashboardDTO,
    FairnessGroupAssignmentDTO,
    FairnessGroupAssignmentRequest,
    FairnessMetricRunDTO,
    FairnessMetricRunRequest,
    FairnessPolicyCreateRequest,
    FairnessPolicyDTO,
    FairnessReviewDTO,
    FairnessReviewRequest,
)
from app.services.fairness.fairness_service import FairnessDomainError, FairnessService

router = APIRouter(prefix="/fairness")


def _raise_domain_error(error: FairnessDomainError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    ) from error


@router.get("/policies", response_model=list[FairnessPolicyDTO])
async def list_policies(session: SessionDep, user: RequiredCurrentUserDep) -> list[FairnessPolicyDTO]:
    try:
        return await FairnessService(session).list_policies(actor=user)
    except FairnessDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/policies", response_model=FairnessPolicyDTO, status_code=201)
async def create_policy(
    payload: FairnessPolicyCreateRequest, session: SessionDep, user: RequiredCurrentUserDep
) -> FairnessPolicyDTO:
    try:
        result = await FairnessService(session).create_policy(actor=user, payload=payload)
        await session.commit()
        return result
    except FairnessDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/consents", response_model=FairnessConsentDTO, status_code=201)
async def grant_consent(
    payload: FairnessConsentRequest, session: SessionDep, user: RequiredCurrentUserDep
) -> FairnessConsentDTO:
    try:
        result = await FairnessService(session).grant_consent(actor=user, payload=payload)
        await session.commit()
        return result
    except FairnessDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/consents/{policy_id}/withdraw", response_model=FairnessConsentDTO)
async def withdraw_consent(
    policy_id: UUID,
    payload: FairnessConsentWithdrawRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> FairnessConsentDTO:
    try:
        result = await FairnessService(session).withdraw_consent(
            actor=user, policy_id=policy_id, payload=payload
        )
        await session.commit()
        return result
    except FairnessDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post(
    "/policies/{policy_id}/group-assignments",
    response_model=FairnessGroupAssignmentDTO,
    status_code=201,
)
async def assign_group(
    policy_id: UUID,
    payload: FairnessGroupAssignmentRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> FairnessGroupAssignmentDTO:
    try:
        result = await FairnessService(session).assign_group(
            actor=user, policy_id=policy_id, payload=payload
        )
        await session.commit()
        return result
    except FairnessDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/policies/{policy_id}/metric-runs", response_model=FairnessMetricRunDTO, status_code=201)
async def run_metrics(
    policy_id: UUID,
    payload: FairnessMetricRunRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> FairnessMetricRunDTO:
    try:
        result = await FairnessService(session).run_metrics(actor=user, policy_id=policy_id, payload=payload)
        await session.commit()
        return result
    except FairnessDomainError as error:
        await session.commit()  # rejected runs are durable audit evidence
        _raise_domain_error(error)


@router.get("/metric-runs/{run_id}", response_model=FairnessMetricRunDTO)
async def get_metric_run(
    run_id: UUID, session: SessionDep, user: RequiredCurrentUserDep
) -> FairnessMetricRunDTO:
    try:
        return await FairnessService(session).get_metric_run(actor=user, run_id=run_id)
    except FairnessDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.get("/dashboard", response_model=FairnessDashboardDTO)
async def get_dashboard(session: SessionDep, user: RequiredCurrentUserDep) -> FairnessDashboardDTO:
    try:
        return await FairnessService(session).dashboard(actor=user)
    except FairnessDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/alerts/{alert_id}/reviews", response_model=FairnessReviewDTO, status_code=201)
async def review_alert(
    alert_id: UUID,
    payload: FairnessReviewRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> FairnessReviewDTO:
    try:
        result = await FairnessService(session).review_alert(actor=user, alert_id=alert_id, payload=payload)
        await session.commit()
        return result
    except FairnessDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/appeals", response_model=FairnessAppealDTO, status_code=201)
async def create_appeal(
    payload: FairnessAppealCreateRequest, session: SessionDep, user: RequiredCurrentUserDep
) -> FairnessAppealDTO:
    try:
        result = await FairnessService(session).create_appeal(actor=user, payload=payload)
        await session.commit()
        return result
    except FairnessDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.get("/appeals/me/grades", response_model=AppealableGradeListDTO)
async def list_appealable_grades(
    session: SessionDep, user: RequiredCurrentUserDep
) -> AppealableGradeListDTO:
    try:
        return await FairnessService(session).list_appealable_grades(actor=user)
    except FairnessDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.get("/appeals", response_model=FairnessAppealListDTO)
async def list_appeals(session: SessionDep, user: RequiredCurrentUserDep) -> FairnessAppealListDTO:
    try:
        return await FairnessService(session).list_appeals(actor=user)
    except FairnessDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/appeals/{appeal_id}/resolve", response_model=FairnessAppealDTO)
async def resolve_appeal(
    appeal_id: UUID,
    payload: FairnessAppealResolveRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> FairnessAppealDTO:
    try:
        result = await FairnessService(session).resolve_appeal(
            actor=user, appeal_id=appeal_id, payload=payload
        )
        await session.commit()
        return result
    except FairnessDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


__all__ = ["router"]
