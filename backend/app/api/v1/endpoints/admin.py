# Status: real

"""Server-authoritative administrator governance HTTP adapters."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.deps import RequiredCurrentUserDep, SessionDep
from app.schemas.governance import (
    AdminCourseResourceDTO,
    AdminCourseResourceListDTO,
    AdminKpiDashboardDTO,
    AdminUserListDTO,
    CourseResourceGovernanceRequest,
    RoleGrantDTO,
    RoleGrantRequest,
    RoleRevokeRequest,
)
from app.services.governance.governance_service import GovernanceDomainError, GovernanceService

router = APIRouter(prefix="/admin")


def _raise_domain_error(error: GovernanceDomainError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    ) from error


@router.get("/users", response_model=AdminUserListDTO)
async def list_admin_users(session: SessionDep, user: RequiredCurrentUserDep) -> AdminUserListDTO:
    try:
        return await GovernanceService(session).list_users(actor=user)
    except GovernanceDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/role-grants", response_model=RoleGrantDTO, status_code=201)
async def grant_role(
    payload: RoleGrantRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> RoleGrantDTO:
    try:
        result = await GovernanceService(session).grant_role(actor=user, payload=payload)
        await session.commit()
        return result
    except GovernanceDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/role-grants/{grant_id}/revoke", response_model=RoleGrantDTO)
async def revoke_role(
    grant_id: UUID,
    payload: RoleRevokeRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> RoleGrantDTO:
    try:
        result = await GovernanceService(session).revoke_role(
            actor=user, grant_id=grant_id, payload=payload
        )
        await session.commit()
        return result
    except GovernanceDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.get("/course-resources", response_model=AdminCourseResourceListDTO)
async def list_course_resources(
    session: SessionDep, user: RequiredCurrentUserDep
) -> AdminCourseResourceListDTO:
    try:
        return await GovernanceService(session).list_course_resources(actor=user)
    except GovernanceDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/course-resources/{asset_id}/govern", response_model=AdminCourseResourceDTO)
async def govern_course_resource(
    asset_id: UUID,
    payload: CourseResourceGovernanceRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> AdminCourseResourceDTO:
    try:
        result = await GovernanceService(session).govern_course_resource(
            actor=user, asset_id=asset_id, payload=payload
        )
        await session.commit()
        return result
    except GovernanceDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.get("/kpis", response_model=AdminKpiDashboardDTO)
async def get_admin_kpis(session: SessionDep, user: RequiredCurrentUserDep) -> AdminKpiDashboardDTO:
    try:
        return await GovernanceService(session).get_kpi_dashboard(actor=user)
    except GovernanceDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


__all__ = ["router"]
