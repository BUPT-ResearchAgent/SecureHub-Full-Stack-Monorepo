# Status: real

"""Profile HTTP adapters.

``POST /profile/chat`` only creates and observes a durable
``profile_build_v1`` root. RuntimeEngine owns every Skill call and persistence
step after the root transaction has committed.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.v1.endpoints.workflow_adapter import (
    durable_sse_response,
    start_product_workflow,
    workflow_service,
)
from app.deps import CurrentUserDep, SessionDep
from app.repositories.identity.capabilities import UserCapabilityRepository
from app.repositories.identity.profiles import UserProfileRepository
from app.services.workflow_application_service import WorkflowApplicationService


router = APIRouter()


class ProfileChatRequest(BaseModel):
    # Kept for wire compatibility. The authenticated identity below is the
    # sole durable root owner and payload user_id is never trusted.
    user_id: str = "demo"
    message: str = Field(min_length=1)
    dialogue_turns: list[dict[str, str]] = Field(default_factory=list)
    mode: Literal["fixture", "real"] = "real"
    provider: str | None = None
    model: str | None = None


class ProfileChatResponse(BaseModel):
    task_id: str
    status: str
    persona: dict[str, Any]
    next_question: str | None = None


class UserProfileResponse(BaseModel):
    user_id: str
    dimensions: dict[str, Any]
    capabilities: list[dict[str, Any]] = Field(default_factory=list)
    updated_at: str | None = None


class UserProfileUpdate(BaseModel):
    dimensions: dict[str, Any]


def _service(request: Request) -> WorkflowApplicationService:
    return workflow_service(request)


async def _profile_response(
    session: SessionDep,
    user_id: UUID,
    dimensions: dict[str, Any],
    updated_at: Any,
) -> UserProfileResponse:
    capabilities = await UserCapabilityRepository(session).list_by_user(user_id)
    return UserProfileResponse(
        user_id=str(user_id),
        dimensions=dimensions,
        capabilities=[
            {
                "dimension": row.dimension,
                "score": row.score,
                "confidence": row.confidence,
                "evidence_count": row.evidence_count,
            }
            for row in capabilities
        ],
        updated_at=updated_at.isoformat() if updated_at else None,
    )


@router.post("/profile/chat")
async def build_profile_from_chat(
    payload: ProfileChatRequest,
    request: Request,
    current_user_id: CurrentUserDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> StreamingResponse:
    service = _service(request)
    start = await start_product_workflow(
        service,
        workflow="profile_build_v1",
        actor_user_id=current_user_id,
        input_payload={
            "message": payload.message,
            "dialogue_turns": payload.dialogue_turns,
            "domain": "course_websec",
        },
        mode=payload.mode,
        provider=payload.provider,
        model=payload.model,
        idempotency_key=idempotency_key,
    )
    return durable_sse_response(service, start, actor_user_id=current_user_id)


@router.get("/profile/me", response_model=UserProfileResponse)
async def get_current_profile(
    session: SessionDep,
    current_user_id: CurrentUserDep,
) -> UserProfileResponse:
    """Return the authenticated profile without treating ``me`` as a UUID."""
    profile = await UserProfileRepository(session).get_by_user_id(current_user_id)
    if profile is None:
        return await _profile_response(session, current_user_id, {}, None)
    return await _profile_response(session, current_user_id, profile.dimensions or {}, profile.updated_at)


@router.get("/profile/{user_id}", response_model=UserProfileResponse)
async def get_profile(user_id: UUID, session: SessionDep) -> UserProfileResponse:
    profile = await UserProfileRepository(session).get_by_user_id(user_id)
    if profile is None:
        return await _profile_response(session, user_id, {}, None)
    return await _profile_response(session, user_id, profile.dimensions or {}, profile.updated_at)


@router.put("/profile/{user_id}", response_model=UserProfileResponse)
async def update_profile(user_id: str, payload: UserProfileUpdate) -> UserProfileResponse:
    return UserProfileResponse(user_id=user_id, dimensions=payload.dimensions)
