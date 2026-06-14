# Status: partial-real

"""Profile + capability endpoints for the demo user.

P0 surface:
- ``GET    /profile/me``               — current persona row
- ``PUT    /profile/me``               — overwrite the JSONB persona
- ``GET    /profile/me/capabilities``  — radar-chart capability rows

Legacy compatibility kept:
- ``POST /profile/chat``       — career_planner.BuildLearningPersona (NotImplementedError)
- ``GET  /profile/{user_id}``  — older read shape, now backed by user_profiles
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.deps import CurrentUserDep, SessionDep
from app.repositories.identity.capabilities import UserCapabilityRepository
from app.repositories.identity.profiles import UserProfileRepository
from app.repositories.identity.users import UserRepository
from app.schemas.identity import (
    CapabilityListOut,
    CapabilityOut,
    ProfileOut,
    ProfileUpdateIn,
)

router = APIRouter()


# ---------------- legacy ----------------

class ProfileChatRequest(BaseModel):
    user_id: str
    message: str = Field(min_length=1)
    dialogue_turns: list[dict[str, str]] = Field(default_factory=list)


class ProfileChatResponse(BaseModel):
    task_id: str
    status: str


class LegacyProfileResponse(BaseModel):
    user_id: str
    dimensions: dict[str, Any]
    updated_at: str | None = None


@router.post("/profile/chat", response_model=ProfileChatResponse)
async def build_profile_from_chat(payload: ProfileChatRequest) -> ProfileChatResponse:
    raise NotImplementedError("TODO: enqueue career_planner.BuildLearningPersona")


# ---------------- v2 /me surface (MUST be declared before /{user_id}) ----------------

@router.get("/profile/me", response_model=ProfileOut)
async def get_my_profile(
    session: SessionDep, user_id: CurrentUserDep
) -> ProfileOut:
    users = UserRepository(session)
    profiles = UserProfileRepository(session)

    user = await users.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="demo user missing — run `python -m app.db.seeds.seed_demo`",
        )

    profile = await profiles.get_by_user_id(user_id)
    return ProfileOut(
        user_id=user.id,
        display_name=user.display_name,
        email=user.email,
        dimensions=(profile.dimensions if profile else {}) or {},
        updated_at=profile.updated_at if profile else None,
    )


@router.put("/profile/me", response_model=ProfileOut)
async def update_my_profile(
    payload: ProfileUpdateIn,
    session: SessionDep,
    user_id: CurrentUserDep,
) -> ProfileOut:
    users = UserRepository(session)
    profiles = UserProfileRepository(session)

    user = await users.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="demo user missing"
        )

    row = await profiles.upsert(user_id=user_id, dimensions=payload.dimensions)
    await session.commit()
    return ProfileOut(
        user_id=user.id,
        display_name=user.display_name,
        email=user.email,
        dimensions=row.dimensions or {},
        updated_at=row.updated_at,
    )


@router.get("/profile/me/capabilities", response_model=CapabilityListOut)
async def get_my_capabilities(
    session: SessionDep, user_id: CurrentUserDep
) -> CapabilityListOut:
    repo = UserCapabilityRepository(session)
    rows = await repo.list_by_user(user_id)
    return CapabilityListOut(
        user_id=user_id,
        items=[
            CapabilityOut(
                dimension=row.dimension,
                score=row.score,
                confidence=row.confidence,
                evidence_count=row.evidence_count,
                metadata=row.metadata_ or {},
            )
            for row in rows
        ],
    )


# ---------------- legacy /{user_id} reader (declared AFTER /me so /me wins) ----------------

@router.get("/profile/{user_id}", response_model=LegacyProfileResponse)
async def get_profile_by_id(
    user_id: str, session: SessionDep
) -> LegacyProfileResponse:
    repo = UserProfileRepository(session)
    try:
        parsed_user_id = UUID(user_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid user_id"
        ) from err
    row = await repo.get_by_user_id(parsed_user_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="profile not found"
        )
    return LegacyProfileResponse(
        user_id=str(row.user_id),
        dimensions=row.dimensions or {},
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


__all__ = ["router"]
