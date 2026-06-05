# Status: [planned]

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceHit(BaseModel):
    chunk_id: UUID | str
    document_id: UUID | str | None = None
    domain: str
    chunk_text: str
    source: str | None = None
    reliability: float = Field(default=0.0, ge=0.0, le=1.0)
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


async def retrieve(
    query: str,
    *,
    domain: str = "course_websec",
    top_k: int = 8,
    filter: dict[str, Any] | None = None,
) -> list[EvidenceHit]:
    raise NotImplementedError("TODO: run BM25 + pgvector retrieval and RRF fusion")
