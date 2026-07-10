# Status: real

import importlib

import pytest
from sqlalchemy import select
from uuid import uuid4

from app.db.models.knowledge.chunk import Chunk
from app.db.models.knowledge.document import Document
from app.knowledge.loaders.embed_chunks import embed_pending_chunks
from app.llm.embeddings.fixture import DeterministicFixtureEmbeddingProvider
from app.llm.embeddings.service import EmbeddingService


@pytest.mark.anyio
async def test_embedding_service_wraps_provider() -> None:
    service = EmbeddingService(DeterministicFixtureEmbeddingProvider())

    result = await service.embed_documents(["SQL injection", "XSS"])
    query = await service.embed_query("SQL injection")

    assert len(result.vectors) == 2
    assert len(query.vectors[0]) == 1024
    assert result.provider == "fixture"


@pytest.mark.anyio
async def test_embed_pending_chunks_updates_metadata(monkeypatch, sqlite_session) -> None:
    document_id = uuid4()
    document = Document(
        id=document_id,
        domain="course_websec",
        source_type="manual",
        title="SQL",
        url="https://example.test/sql",
        raw_text="SQL injection",
        metadata_={"platform": "manual"},
        trust_score=0.8,
        status="ready",
    )
    chunk = Chunk(
        document_id=document_id,
        domain="course_websec",
        chunk_text="SQL injection uses unsafe string concatenation.",
        chunk_index=0,
        token_count=8,
        embedding=None,
        embedding_status="pending",
        metadata_={"platform": "manual", "keep": "yes"},
    )
    sqlite_session.add_all([document, chunk])
    await sqlite_session.commit()

    module = importlib.import_module("app.knowledge.loaders.embed_chunks")

    monkeypatch.setattr(
        module,
        "EmbeddingService",
        lambda: EmbeddingService(DeterministicFixtureEmbeddingProvider()),
    )
    monkeypatch.setattr(module, "get_sessionmaker", lambda: lambda: sqlite_session)

    result = await embed_pending_chunks(domain="course_websec", batch_size=1, limit=1)

    assert result.embedded == 1
    row = (
        await sqlite_session.execute(select(Chunk).where(Chunk.id == chunk.id))
    ).scalar_one()
    assert row.embedding_status == "ready"
    assert len(row.embedding) == 1024
    assert row.metadata_["keep"] == "yes"
    assert row.metadata_["embedding_profile"].startswith("fixture:")
    assert row.metadata_["embedding_dim"] == 1024


@pytest.mark.anyio
async def test_embed_pending_chunks_recovers_processing(monkeypatch, sqlite_session) -> None:
    document_id = uuid4()
    sqlite_session.add(
        Document(
            id=document_id,
            domain="course_websec",
            source_type="manual",
            title="Processing",
            url="https://example.test/processing",
            raw_text="processing",
            metadata_={"platform": "manual"},
            trust_score=0.8,
            status="ready",
        )
    )
    chunk = Chunk(
        document_id=document_id,
        domain="course_websec",
        chunk_text="processing chunk can be recovered after interruption",
        chunk_index=0,
        token_count=8,
        embedding=None,
        embedding_status="processing",
        metadata_={"platform": "manual"},
    )
    sqlite_session.add(chunk)
    await sqlite_session.commit()

    module = importlib.import_module("app.knowledge.loaders.embed_chunks")
    monkeypatch.setattr(
        module,
        "EmbeddingService",
        lambda: EmbeddingService(DeterministicFixtureEmbeddingProvider()),
    )
    monkeypatch.setattr(module, "get_sessionmaker", lambda: lambda: sqlite_session)

    result = await embed_pending_chunks(domain="course_websec", batch_size=1, limit=1)

    assert result.embedded == 1
    row = (
        await sqlite_session.execute(select(Chunk).where(Chunk.id == chunk.id))
    ).scalar_one()
    assert row.embedding_status == "ready"
