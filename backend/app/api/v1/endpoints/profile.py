# Status: [planned]

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class ProfileChatRequest(BaseModel):
    user_id: str
    message: str = Field(min_length=1)
    dialogue_turns: list[dict[str, str]] = Field(default_factory=list)


class ProfileChatResponse(BaseModel):
    task_id: str
    status: str


class UserProfileResponse(BaseModel):
    user_id: str
    dimensions: dict[str, Any]
    updated_at: str | None = None


class UserProfileUpdate(BaseModel):
    dimensions: dict[str, Any]


@router.post("/profile/chat", response_model=ProfileChatResponse)
async def build_profile_from_chat(payload: ProfileChatRequest) -> ProfileChatResponse:
    raise NotImplementedError("TODO: enqueue career_planner.BuildLearningPersona")


@router.get("/profile/{user_id}", response_model=UserProfileResponse)
async def get_profile(user_id: str) -> UserProfileResponse:
    raise NotImplementedError("TODO: read user_profiles.dimensions")


@router.put("/profile/{user_id}", response_model=UserProfileResponse)
async def update_profile(user_id: str, payload: UserProfileUpdate) -> UserProfileResponse:
    raise NotImplementedError("TODO: update user_profiles through persona update workflow")
