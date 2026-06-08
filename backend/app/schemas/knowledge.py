# Status: partial-real

"""Pydantic schemas for the ``/api/v1/courses`` + ``/api/v1/rag/search``
surfaces (data-layer v2).
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ---- courses ---------------------------------------------------------------

class CourseOut(BaseModel):
    id: UUID
    code: str
    title: str
    domain: str
    description: str | None = None


class CourseListOut(BaseModel):
    items: list[CourseOut]
    total: int


class KnowledgeNodeOut(BaseModel):
    id: UUID
    name: str
    node_type: str
    level: int | None = None
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeEdgeOut(BaseModel):
    source_id: UUID
    target_id: UUID
    edge_type: str
    weight: float


class KnowledgeMapOut(BaseModel):
    course_id: UUID
    nodes: list[KnowledgeNodeOut]
    edges: list[KnowledgeEdgeOut]


# ---- rag/search ------------------------------------------------------------

class RagSearchIn(BaseModel):
    domain: str = Field(default="course_websec")
    query: str
    top_k: int = Field(default=5, ge=1, le=50)


class RagChunkOut(BaseModel):
    chunk_id: UUID
    document_id: UUID
    title: str
    snippet: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagSearchOut(BaseModel):
    query: str
    domain: str
    hits: list[RagChunkOut]
