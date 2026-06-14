# Status: real

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
        cards: list[EvidenceCard] = []
        for hit in hits:
            source = (
                hit.metadata.get("source_url")
                or hit.metadata.get("object_key")
                or str(hit.document_id)
            )
            cards.append(
                EvidenceCard(
                    chunk_id=hit.chunk_id,
                    document_id=hit.document_id,
                    source=str(source),
                    title=hit.title,
                    excerpt=hit.snippet,
                    reliability=float(hit.metadata.get("reliability") or 0.5),
                    metadata=dict(hit.metadata),
                )
            )
        return cards
