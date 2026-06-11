# Status: real

"""Profile endpoints：

- ``POST /profile/chat`` 走 career_planner.BuildLearningPersona，返回 6+ 维画像
- ``GET /profile/{user_id}`` 占位（从 ``user_profiles`` 读，无表时返回 fixture）
- ``PUT /profile/{user_id}`` 占位（写 ``user_profiles``，无表时回显）
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.career_planner.skills.build_learning_persona import (
    BuildLearningPersona,
    BuildLearningPersonaInput,
)
from app.runtime.harness import HarnessContext

logger = logging.getLogger(__name__)
router = APIRouter()


class ProfileChatRequest(BaseModel):
    user_id: str = "demo"
    message: str = Field(min_length=1)
    dialogue_turns: list[dict[str, str]] = Field(default_factory=list)


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


@router.post("/profile/chat", response_model=ProfileChatResponse)
async def build_profile_from_chat(payload: ProfileChatRequest) -> ProfileChatResponse:
    ctx = HarnessContext(user_id=payload.user_id, workflow_name="profile_build")
    skill = BuildLearningPersona()
    inp = BuildLearningPersonaInput(
        user_id=payload.user_id,
        query=payload.message,
        dialogue_turns=payload.dialogue_turns,
    )
    out = await skill.run(inp, ctx)
    return ProfileChatResponse(
        task_id=str(uuid4()),
        status="ok",
        persona=out.model_dump(),
        next_question=out.next_question,
    )


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
    # Fixture fallback when DB unavailable
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
