# Status: real

"""Evidence-bound policy, hot-event, and job-signal course update adapters."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.deps import RequiredCurrentUserDep, SessionDep
from app.schemas.collaboration import (
    CourseUpdateDecisionRequest,
    CourseUpdateSuggestionDTO,
    CreateCourseUpdateSuggestionRequest,
    ExternalSignalDTO,
    ExternalSignalIngestRequest,
)
from app.services.collaboration.collaboration_service import (
    CollaborationDomainError,
    CollaborationService,
)

router = APIRouter(prefix="/course-updates")


def _raise_domain_error(error: CollaborationDomainError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    ) from error


@router.post("/signals", response_model=ExternalSignalDTO, status_code=201)
async def ingest_external_signal(
    payload: ExternalSignalIngestRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> ExternalSignalDTO:
    try:
        result = await CollaborationService(session).ingest_external_signal(actor=user, payload=payload)
        await session.commit()
        return result
    except CollaborationDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.get("/signals", response_model=list[ExternalSignalDTO])
async def list_external_signals(
    session: SessionDep, user: RequiredCurrentUserDep
) -> list[ExternalSignalDTO]:
    try:
        return await CollaborationService(session).list_external_signals(actor=user)
    except CollaborationDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/suggestions", response_model=CourseUpdateSuggestionDTO, status_code=201)
async def create_course_update_suggestion(
    payload: CreateCourseUpdateSuggestionRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> CourseUpdateSuggestionDTO:
    try:
        result = await CollaborationService(session).create_course_update_suggestion(
            actor=user, payload=payload
        )
        await session.commit()
        return result
    except CollaborationDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.get("/courses/{course_id}/suggestions", response_model=list[CourseUpdateSuggestionDTO])
async def list_course_update_suggestions(
    course_id: UUID,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> list[CourseUpdateSuggestionDTO]:
    try:
        return await CollaborationService(session).list_course_update_suggestions(
            actor=user, course_id=course_id
        )
    except CollaborationDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/suggestions/{suggestion_id}/decision", response_model=CourseUpdateSuggestionDTO)
async def decide_course_update_suggestion(
    suggestion_id: UUID,
    payload: CourseUpdateDecisionRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> CourseUpdateSuggestionDTO:
    try:
        result = await CollaborationService(session).decide_course_update_suggestion(
            actor=user, suggestion_id=suggestion_id, payload=payload
        )
        await session.commit()
        return result
    except CollaborationDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


__all__ = ["router"]
