# Status: real

"""Evidence DTO mirrored by the frontend SSE contract."""

from datetime import datetime

from pydantic import BaseModel


class EvidenceChunkDTO(BaseModel):
    chunk_id: str
    document_id: str
    source_url: str | None = None
    platform: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime | None = None
    rights_note: str | None = None
    asset_type: str | None = None
    excerpt: str
    page_no: int | None = None
    chapter: str | None = None
    timestamp: float | None = None
    reliability: float | None = None
