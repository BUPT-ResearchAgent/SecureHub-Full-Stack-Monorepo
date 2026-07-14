# Status: real

"""Course and learning path DTOs for the A3 main path."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

LearningPathNodeStatus = Literal["locked", "ready", "in_progress", "done"]


class CourseDTO(BaseModel):
    id: str
    code: str
    title: str
    description: str | None = None
    progress: float | None = None


class LearningPathNodeDTO(BaseModel):
    node_id: str
    title: str
    status: LearningPathNodeStatus
    prerequisites: list[str]


class LearningPathDTO(BaseModel):
    course_id: UUID | str
    path: list[LearningPathNodeDTO]


class CoursePlanRequest(BaseModel):
    user_id: UUID
    target_node_id: UUID
    options: dict[str, object] | None = None
    # Fixture runs are explicit. The production default is real and never
    # silently downgrades to canned content.
    mode: Literal["fixture", "real"] = "real"
    provider: str | None = None
    model: str | None = None


class CoursePlanResponse(BaseModel):
    course_id: UUID | str
    path: list[LearningPathNodeDTO]
