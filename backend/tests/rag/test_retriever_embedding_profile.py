# Status: real

from __future__ import annotations

from uuid import uuid4

import pytest

from app.db.models.knowledge.chunk import Chunk
from app.db.models.knowledge.document import Document
import app.db.session as db_session
from app.llm.embeddings.base import EmbeddingResult
from app.llm.embeddings.errors import EmbeddingProviderError
from app.rag import retriever


class _QueryService:
    def __init__(self, vector: list[float] | None = None, error: Exception | None = None) -> None:
        self.vector = vector or [0.001] * 1024
        self.error = error

    async def embed_query(self, _text: str) -> EmbeddingResult:
        if self.error:
            raise self.error
        return EmbeddingResult(
            vectors=[self.vector],
            provider="fixture",
            model="fixture",
            dimension=len(self.vector),
            profile="qwen-openai-compatible:text-embedding-v4:1024:dense:v1",
        )


@pytest.mark.anyio
async def test_retriever_filters_ready_current_profile(monkeypatch, sqlite_session) -> None:
    target_profile = "qwen-openai-compatible:text-embedding-v4:1024:dense:v1"
    document_id = uuid4()
    document = Document(
        id=document_id,
        domain="course_websec",
        source_type="manual",
        title="SQL",
        url="https://example.test/sql",
        raw_text="SQL injection",
        metadata_={"source_url": "https://example.test/sql", "platform": "manual"},
        trust_score=0.8,
        status="ready",
    )
    ready_current = Chunk(
        document_id=document_id,
        domain="course_websec",
        chunk_text="SQL injection parameterized query defense",
        chunk_index=0,
        embedding=[0.001] * 1024,
        embedding_status="ready",
        metadata_={"embedding_profile": target_profile, "url": "https://example.test/sql"},
    )
    ready_legacy = Chunk(
        document_id=document_id,
        domain="course_websec",
        chunk_text="SQL injection legacy vector should not appear",
        chunk_index=1,
        embedding=[0.001] * 1024,
        embedding_status="ready",
        metadata_={},
    )
    pending_current = Chunk(
        document_id=document_id,
        domain="course_websec",
        chunk_text="SQL injection pending vector should not appear",
        chunk_index=2,
        embedding=[0.001] * 1024,
        embedding_status="pending",
        metadata_={"embedding_profile": target_profile},
    )
    sqlite_session.add_all([document, ready_current, ready_legacy, pending_current])
    await sqlite_session.commit()

    monkeypatch.setattr(retriever, "EmbeddingService", lambda: _QueryService())
    monkeypatch.setattr(db_session, "get_sessionmaker", lambda: lambda: sqlite_session)

    hits = await retriever.retrieve("SQL injection", top_k=5)

    assert [str(hit.chunk_id) for hit in hits] == [str(ready_current.id)]


@pytest.mark.anyio
async def test_retriever_uses_configured_dimension(monkeypatch, sqlite_session) -> None:
    monkeypatch.setattr(retriever, "EmbeddingService", lambda: _QueryService(vector=[0.1] * 3))
    monkeypatch.setattr(db_session, "get_sessionmaker", lambda: lambda: sqlite_session)

    with pytest.raises(ValueError):
        await retriever.retrieve("SQL injection", top_k=5)


@pytest.mark.anyio
async def test_retriever_does_not_swallow_embedding_provider_errors(monkeypatch, sqlite_session) -> None:
    monkeypatch.setattr(
        retriever,
        "EmbeddingService",
        lambda: _QueryService(error=EmbeddingProviderError("provider unavailable")),
    )
    monkeypatch.setattr(db_session, "get_sessionmaker", lambda: lambda: sqlite_session)

    with pytest.raises(EmbeddingProviderError):
        await retriever.retrieve("SQL injection", top_k=5)
