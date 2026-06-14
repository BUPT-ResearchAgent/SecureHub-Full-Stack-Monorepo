# Status: real

"""Course and learning path DTOs for the A3 main path."""

from typing import Literal

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
    course_id: str
    path: list[LearningPathNodeDTO]
