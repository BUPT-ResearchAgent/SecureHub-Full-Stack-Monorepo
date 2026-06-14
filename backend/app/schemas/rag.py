# Status: real

"""RAG search DTOs for contract-stable evidence retrieval."""

from pydantic import BaseModel, Field

from app.schemas.evidence import EvidenceChunkDTO

JsonObject = dict[str, object]


class RagSearchRequest(BaseModel):
    domain: str
    query: str
    top_k: int = 5
    filters: JsonObject | None = None


class RagSearchResponse(BaseModel):
    chunks: list[EvidenceChunkDTO]
    total: int
