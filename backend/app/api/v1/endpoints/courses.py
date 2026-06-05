# Status: [planned]

from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()

ResourceType = Literal["doc", "ppt", "mindmap", "quiz", "lab", "video"]


class CoursePlanRequest(BaseModel):
    user_id: str
    selected_kp_ids: list[str] = Field(default_factory=list)
    time_budget_hours: int | None = None


class CoursePlanResponse(BaseModel):
    task_id: str
    status: str


class GenerateResourceRequest(BaseModel):
    user_id: str
    kp_id: str | None = None
    preferences: dict[str, str] = Field(default_factory=dict)


class GenerateResourceResponse(BaseModel):
    task_id: str
    resource_type: ResourceType
    status: str


@router.post("/courses/{course_id}/plan", response_model=CoursePlanResponse)
async def plan_learning_path(course_id: str, payload: CoursePlanRequest) -> CoursePlanResponse:
    raise NotImplementedError("TODO: enqueue task_orchestrator.GenerateLearningPath")


@router.post("/courses/{course_id}/resources/generate", response_model=GenerateResourceResponse)
async def generate_resource(
    course_id: str,
    payload: GenerateResourceRequest,
    type: ResourceType = Query(...),
) -> GenerateResourceResponse:
    raise NotImplementedError("TODO: enqueue course resource generation workflow")
