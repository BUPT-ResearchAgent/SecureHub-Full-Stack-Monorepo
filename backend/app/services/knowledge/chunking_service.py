# Status: real

"""Per task brief §6.1 — ChunkingService splits a document into ``chunks``
rows with ``embedding_status='pending'``. EmbeddingService later fills the
vectors.
"""

from collections.abc import Sequence
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge.chunk import Chunk
from app.repositories.knowledge.chunks import ChunkRepository
from app.repositories.knowledge.documents import DocumentRepository


class ChunkingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def split_text(text: str, *, size: int = 600, overlap: int = 100) -> list[str]:
        cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        if not cleaned:
            return []
        if size <= 0:
            raise ValueError("size must be positive")
        if overlap < 0 or overlap >= size:
            raise ValueError("overlap must be non-negative and smaller than size")

        chunks: list[str] = []
        start = 0
        while start < len(cleaned):
            end = min(start + size, len(cleaned))
            chunks.append(cleaned[start:end])
            if end == len(cleaned):
                break
            start = end - overlap
        return chunks

    async def chunk_document(
        self,
        document_id: UUID,
        *,
        size: int = 600,
        overlap: int = 100,
        metadata: dict[str, object] | None = None,
    ) -> Sequence[UUID]:
        """Return the freshly inserted chunk ids in chunk-index order."""
        documents = DocumentRepository(self.session)
        document = await documents.get_by_id(document_id)
        if document is None:
            raise ValueError(f"document not found: {document_id}")
        if not document.raw_text:
            return []

        chunks = ChunkRepository(self.session)
        existing = await chunks.list_by_document(document_id)
        if existing:
            return [row.id for row in existing]

        source_metadata = dict(document.metadata_ or {})
        if metadata:
            source_metadata.update(metadata)

        rows: list[Chunk] = []
        for index, text in enumerate(self.split_text(document.raw_text, size=size, overlap=overlap)):
            chunk_id = uuid5(NAMESPACE_URL, f"securehub:chunk:{document_id}:{index}")
            rows.append(
                Chunk(
                    id=chunk_id,
                    document_id=document_id,
                    domain=document.domain,
                    chunk_text=text,
                    chunk_index=index,
                    token_count=len(text.split()),
                    embedding=None,
                    embedding_status="pending",
                    metadata_=source_metadata | {"chunker": "fixed_window_v1"},
                )
            )

        await chunks.bulk_create(rows)
        return [row.id for row in rows]
