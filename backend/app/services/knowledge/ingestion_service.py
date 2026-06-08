# Status: planned

"""Per task brief §6.1 — IngestionService accepts a document payload
(content + URL + optional file path), writes a row to ``documents``, registers
the source assets in ``document_assets``, and hands off to ChunkingService.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class IngestionRequest:
    domain: str
    source_type: str
    title: str
    url: str | None = None
    raw_text: str | None = None
    metadata: dict[str, Any] | None = None
    assets: list[dict[str, Any]] | None = None  # [{asset_type, object_key, mime_type, ...}]


@dataclass(slots=True)
class IngestionResult:
    document_id: UUID
    chunk_count: int
    asset_count: int


class IngestionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ingest(self, request: IngestionRequest) -> IngestionResult:
        raise NotImplementedError("planned: P1 — implements §6.1 ingestion pipeline")
