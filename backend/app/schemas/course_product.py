# Status: real

"""Additive DTOs for the data-backed course catalog, graph, and progress API."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CourseCatalogItemDTO(BaseModel):
    id: UUID
    code: str
    title: str
    domain: str
    description: str | None = None
    chapter_count: int
    knowledge_point_count: int
    resource_count: int
    progress_percent: float
    current_knowledge_point_id: UUID | None = None
    current_knowledge_point: str | None = None
    next_recommendation: str | None = None
    core_coverage_percent: float


class CourseKnowledgePointDTO(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str | None = None
    level: int | None = None
    chapter_code: str
    chapter_title: str
    resource_count: int = 0
    evidence_count: int = 0


class CourseChapterDTO(BaseModel):
    code: str
    title: str
    knowledge_point_ids: list[UUID]
    covered_knowledge_point_ids: list[UUID]
    coverage_percent: float


class CourseDetailDTO(CourseCatalogItemDTO):
    chapters: list[CourseChapterDTO]
    knowledge_points: list[CourseKnowledgePointDTO]
    source_platforms: list[str]
    source_manifest: str


class CourseGraphEdgeDTO(BaseModel):
    source_id: UUID
    target_id: UUID
    edge_type: Literal["prerequisite"]
    weight: float


class CourseGraphDTO(BaseModel):
    course_id: UUID
    nodes: list[CourseKnowledgePointDTO]
    edges: list[CourseGraphEdgeDTO]


class CoursePathNodeDTO(BaseModel):
    knowledge_point_id: UUID
    title: str
    status: Literal["locked", "ready", "in_progress", "done"]
    prerequisites: list[UUID]
    rationale: str


class CoursePathDTO(BaseModel):
    course_id: UUID
    capability_dimension: str
    capability_score: float
    strategy: Literal["foundation_first", "accelerated_prerequisite_route"]
    explanation: str
    nodes: list[CoursePathNodeDTO]


class CourseProgressDTO(BaseModel):
    course_id: UUID
    course_code: str
    completed_knowledge_point_ids: list[UUID]
    progress_percent: float
    current_knowledge_point_id: UUID | None = None
    next_knowledge_point_id: UUID | None = None
    next_recommendation: str | None = None
    updated_at: datetime | None = None


class CourseProgressUpdateRequest(BaseModel):
    knowledge_point_id: UUID
    activity_type: Literal["resource", "assessment"]
    activity_id: str = Field(min_length=1, max_length=255)
    workflow_run_id: UUID | None = None
