# Status: planned

"""Per task brief §6.1 — EvidenceService converts ``ChunkHit`` rows from
RetrievalService into ``EvidenceCard`` payloads the frontend
``CitationPanel`` / ``EvidenceDrawer`` already render.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge.retrieval_service import ChunkHit


@dataclass(slots=True)
class EvidenceCard:
    chunk_id: UUID
    document_id: UUID
    source: str  # URL or asset_key
    title: str
    excerpt: str
    reliability: float  # mapped from documents.trust_score
    metadata: dict[str, Any]


class EvidenceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def build(self, hits: Sequence[ChunkHit]) -> Sequence[EvidenceCard]:
        raise NotImplementedError("planned: P0 — implements §6.1 evidence building")
