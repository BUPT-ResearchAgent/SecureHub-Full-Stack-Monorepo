# Status: real

"""Profile HTTP adapters.

``POST /profile/chat`` only creates and observes a durable
``profile_build_v1`` root. RuntimeEngine owns every Skill call and persistence
step after the root transaction has committed.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.v1.endpoints.workflow_adapter import (
    durable_sse_response,
    start_product_workflow,
    workflow_service,
)
from app.deps import CurrentUserDep
from app.services.workflow_application_service import WorkflowApplicationService


logger = logging.getLogger(__name__)
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
    updated_at: str | None = None


class UserProfileUpdate(BaseModel):
    dimensions: dict[str, Any]


def _service(request: Request) -> WorkflowApplicationService:
    return workflow_service(request)


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


@router.get("/profile/{user_id}", response_model=UserProfileResponse)
async def get_profile(user_id: str) -> UserProfileResponse:
    try:
        from app.db.models.user_profile import UserProfile
        from app.db.session import get_sessionmaker
        from sqlalchemy import select

        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            row = await session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
            profile = row.scalar_one_or_none()
            if profile is not None:
                return UserProfileResponse(
                    user_id=str(profile.user_id),
                    dimensions=profile.dimensions or {},
                    updated_at=profile.updated_at.isoformat() if profile.updated_at else None,
                )
    except Exception as exc:  # noqa: BLE001
        logger.warning("profile read fallback: %s", exc)
    # This legacy read endpoint is outside the runtime product path. It stays
    # compatible until profile read migration is separately scheduled.
    return UserProfileResponse(
        user_id=user_id,
        dimensions={
            "base_knowledge": "intermediate",
            "cognitive_style": "hands-on",
            "weak_points": ["sql_injection"],
            "preferred_modality": ["doc", "lab"],
            "time_budget": "8h/week",
            "target_direction": "web_security",
        },
    )


@router.put("/profile/{user_id}", response_model=UserProfileResponse)
async def update_profile(user_id: str, payload: UserProfileUpdate) -> UserProfileResponse:
    return UserProfileResponse(user_id=user_id, dimensions=payload.dimensions)
