# Status: real

"""Contract-shape regression for retrieval → ``EvidenceChunkDTO``.

Pinned by ``docs/api/evidence-contract.md`` v1 (2026-06-16). The intent is:

- Real RAG retrieval (via ``RetrievalService``) produces ``ChunkHit`` rows whose
  metadata, when projected through ``evidence_card_to_dto``, validates as
  ``EvidenceChunkDTO`` with all required fields populated.
- The DTO validator rejects ``source_url=None`` for non-``manual`` platforms.
- Offline fixtures (``default_evidence_fixtures``) also satisfy the contract,
  because the harness falls back to them when the DB is empty.

Run with: ``uv run pytest backend/tests/rag/test_evidence_contract.py -q``
"""

from __future__ import annotations

import pytest

from app.db.seeds.seed_course_websec import run as seed_course_websec
from app.runtime.harness.fixtures import default_evidence_fixtures
from app.runtime.harness.types import EvidenceCard
from app.schemas.evidence import CollectionMode, EvidenceChunkDTO, evidence_card_to_dto
from app.services.knowledge.retrieval_service import RetrievalService


@pytest.mark.anyio
async def test_retrieval_projects_to_contract_dto(sqlite_session) -> None:
    await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    hits = await RetrievalService(sqlite_session).retrieve(
        "SQL 注入 参数化查询",
        domain="course_websec",
        top_k=5,
    )
    assert len(hits) >= 3, "seed should yield enough chunks for the demo query"

    for hit in hits:
        # ChunkHit -> EvidenceCard-shaped object via attribute access; the
        # projection helper accepts anything that exposes the right attrs.
        card = EvidenceCard(
            chunk_id=str(hit.chunk_id),
            document_id=str(hit.document_id),
            domain="course_websec",
            source=str(hit.metadata.get("source_url") or hit.document_id),
            excerpt=hit.snippet,
            reliability=float(hit.metadata.get("reliability") or 0.6),
            score=float(hit.score),
            metadata=dict(hit.metadata),
        )

        dto = evidence_card_to_dto(card)

        # Required fields all populated, contract-compliant.
        assert dto.chunk_id == str(hit.chunk_id)
        assert dto.document_id == str(hit.document_id)
        assert dto.chunk_text, "chunk_text must not be empty"
        assert 0.0 <= dto.score <= 1.0
        assert dto.platform, "platform required"
        assert dto.rights_note, "rights_note required"

        # Conditional: source_url is required iff platform != 'manual'
        # (seed has both OWASP/PortSwigger platforms AND fallback 'manual'
        # platform docs for nodes that don't ship a custom SOURCE_PROFILE).
        if dto.platform != "manual":
            assert dto.source_url, (
                f"chunk {dto.chunk_id} on platform={dto.platform!r} must carry source_url"
            )

        # asset_type comes from documents.source_type or metadata fallback;
        # legacy seed values 'markdown_full' / 'manual_import' still allowed per contract §4.3.
        assert dto.asset_type in {"markdown_full", "manual_import", "web_article", "markdown", "pdf"}, (
            f"unexpected asset_type {dto.asset_type!r}"
        )


@pytest.mark.anyio
async def test_offline_fixtures_satisfy_contract() -> None:
    """Harness fallback fixtures must round-trip through the DTO."""
    for hit in default_evidence_fixtures("course_websec"):
        dto = evidence_card_to_dto(hit)
        assert isinstance(dto, EvidenceChunkDTO)
        assert dto.platform
        assert dto.rights_note
        if dto.platform != "manual":
            assert dto.source_url, (
                f"fixture {hit['chunk_id']} platform={dto.platform} must carry source_url"
            )


def test_manual_platform_allows_null_source_url() -> None:
    """Contract §1: source_url is optional only when platform == 'manual'."""
    dto = EvidenceChunkDTO(
        chunk_id="c-1",
        document_id="d-1",
        chunk_text="教师手工录入的演示内容",
        score=0.5,
        platform="manual",
        rights_note="internal teaching note",
        source_url=None,
    )
    assert dto.source_url is None
    assert dto.platform == "manual"


def test_video_transcript_carries_timestamp() -> None:
    """Contract §5: video_transcript should populate timestamp."""
    dto = EvidenceChunkDTO(
        chunk_id="c-1",
        document_id="d-1",
        chunk_text="演示视频字幕片段。",
        score=0.7,
        platform="bili",
        rights_note="保留原视频链接",
        source_url="https://www.bilibili.com/video/example",
        asset_type="video_transcript",
        timestamp=180.0,
    )
    assert dto.timestamp == 180.0
    assert dto.asset_type == "video_transcript"


def test_collection_mode_rejects_unknown_value() -> None:
    """CollectionMode is a closed enum (contract §4.2)."""
    with pytest.raises(Exception):
        EvidenceChunkDTO(
            chunk_id="c-1",
            document_id="d-1",
            chunk_text="x",
            score=0.5,
            platform="manual",
            rights_note="x",
            collection_mode="hand_crawl",  # type: ignore[arg-type]
        )


def test_collection_mode_accepts_all_documented_values() -> None:
    for member in CollectionMode:
        dto = EvidenceChunkDTO(
            chunk_id="c-1",
            document_id="d-1",
            chunk_text="x",
            score=0.5,
            platform="manual",
            rights_note="x",
            collection_mode=member,
        )
        assert dto.collection_mode == member
