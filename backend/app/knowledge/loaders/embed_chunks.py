# Status: [planned]

from uuid import UUID

from pydantic import BaseModel


class EmbedChunksResult(BaseModel):
    embedded_chunk_ids: list[UUID]
    skipped_chunk_ids: list[UUID]


async def embed_chunks(chunk_ids: list[UUID]) -> EmbedChunksResult:
    raise NotImplementedError("TODO: generate embeddings and write pgvector values idempotently")
