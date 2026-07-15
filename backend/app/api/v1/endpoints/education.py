# Status: real

"""Teacher-scoped education relationship HTTP adapters."""

from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query

from app.deps import RequiredCurrentUserDep, SessionDep
from app.schemas.education import (
    ChangeStudentGroupMemberRequest,
    CreateStudentGroupRequest,
    StudentGroupDTO,
    StudentGroupListDTO,
    StudentGroupMemberDTO,
    TeachingClassListDTO,
    TeachingClassRosterDTO,
)
from app.services.education.education_service import EducationDomainError, EducationService

router = APIRouter(prefix="/teacher/education")


def _raise_domain_error(error: EducationDomainError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    ) from error


@router.get("/classes", response_model=TeachingClassListDTO)
async def list_teaching_classes(
    session: SessionDep,
    user: RequiredCurrentUserDep,
    course_id: UUID | None = Query(default=None),
) -> TeachingClassListDTO:
    try:
        return await EducationService(session).list_classes(actor=user, course_id=course_id)
    except EducationDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.get("/classes/{class_id}/roster", response_model=TeachingClassRosterDTO)
async def get_teaching_class_roster(
    class_id: UUID,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> TeachingClassRosterDTO:
    try:
        return await EducationService(session).get_roster(actor=user, class_id=class_id)
    except EducationDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.get("/classes/{class_id}/groups", response_model=StudentGroupListDTO)
async def get_teaching_class_groups(
    class_id: UUID,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> StudentGroupListDTO:
    try:
        return await EducationService(session).get_groups(actor=user, class_id=class_id)
    except EducationDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/classes/{class_id}/groups", response_model=StudentGroupDTO, status_code=201)
async def create_teaching_class_group(
    class_id: UUID,
    payload: CreateStudentGroupRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=128),
) -> StudentGroupDTO:
    try:
        result = await EducationService(session).create_group(
            actor=user,
            class_id=class_id,
            payload=payload,
            idempotency_key=idempotency_key,
        )
        await session.commit()
        return result
    except EducationDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post(
    "/classes/{class_id}/groups/{group_id}/members",
    response_model=StudentGroupMemberDTO,
)
async def change_teaching_class_group_member(
    class_id: UUID,
    group_id: UUID,
    payload: ChangeStudentGroupMemberRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=128),
) -> StudentGroupMemberDTO:
    try:
        result = await EducationService(session).change_group_member(
            actor=user,
            class_id=class_id,
            group_id=group_id,
            payload=payload,
            idempotency_key=idempotency_key,
        )
        await session.commit()
        return result
    except EducationDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


__all__ = ["router"]
