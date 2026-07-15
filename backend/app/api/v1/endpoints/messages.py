# Status: real

"""Authenticated interpersonal message and announcement HTTP adapters."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.deps import RequiredCurrentUserDep, SessionDep
from app.schemas.collaboration import (
    MessageDTO,
    MessageInboxDTO,
    MessageReadDTO,
    MessageSendRequest,
    RecallMessageRequest,
)
from app.services.collaboration.collaboration_service import (
    CollaborationDomainError,
    CollaborationService,
)

router = APIRouter(prefix="/messages")


def _raise_domain_error(error: CollaborationDomainError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
    ) from error


@router.post("", response_model=MessageDTO, status_code=201)
async def send_message(
    payload: MessageSendRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> MessageDTO:
    try:
        result = await CollaborationService(session).send_message(actor=user, payload=payload)
        await session.commit()
        return result
    except CollaborationDomainError as error:
        # Content rejection itself is an auditable business event.  It is the
        # only expected error that intentionally persists a rejected message.
        if error.code == "MESSAGE_CONTENT_UNSAFE":
            await session.commit()
        else:
            await session.rollback()
        _raise_domain_error(error)


@router.get("/inbox", response_model=MessageInboxDTO)
async def get_inbox(session: SessionDep, user: RequiredCurrentUserDep) -> MessageInboxDTO:
    try:
        return await CollaborationService(session).list_inbox(actor=user)
    except CollaborationDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.get("/outbox", response_model=list[MessageDTO])
async def get_outbox(session: SessionDep, user: RequiredCurrentUserDep) -> list[MessageDTO]:
    try:
        return await CollaborationService(session).list_outbox(actor=user)
    except CollaborationDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/{message_id}/read", response_model=MessageReadDTO)
async def mark_message_read(
    message_id: UUID,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> MessageReadDTO:
    try:
        result = await CollaborationService(session).mark_message_read(actor=user, message_id=message_id)
        await session.commit()
        return result
    except CollaborationDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


@router.post("/{message_id}/recall", response_model=MessageDTO)
async def recall_message(
    message_id: UUID,
    payload: RecallMessageRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> MessageDTO:
    try:
        result = await CollaborationService(session).recall_message(
            actor=user, message_id=message_id, payload=payload
        )
        await session.commit()
        return result
    except CollaborationDomainError as error:
        await session.rollback()
        _raise_domain_error(error)


__all__ = ["router"]
