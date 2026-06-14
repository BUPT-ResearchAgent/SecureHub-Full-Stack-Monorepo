# Status: real

import pytest

from app.db.seeds.seed_course_websec import run as seed_course_websec
from app.services.knowledge.retrieval_service import RetrievalService


@pytest.mark.anyio
async def test_retrieve_course_websec_returns_evidence_fields(sqlite_session) -> None:
    await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    hits = await RetrievalService(sqlite_session).retrieve(
        "SQL 注入 参数化查询",
        domain="course_websec",
        top_k=5,
    )

    assert len(hits) >= 3
    assert hits[0].score > 0
    assert "SQL" in hits[0].snippet or "参数化" in hits[0].snippet
    for hit in hits:
        assert hit.metadata["source_url"]
        assert hit.metadata["platform"]
        assert hit.metadata["author"]
        assert "rights_note" in hit.metadata
        assert hit.metadata["asset_type"] in {"markdown_full", "manual_import"}


@pytest.mark.anyio
async def test_retrieve_course_websec_supports_platform_filter(sqlite_session) -> None:
    await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    hits = await RetrievalService(sqlite_session).retrieve(
        "CSRF Token SameSite",
        domain="course_websec",
        top_k=5,
        filters={"platform": "portswigger"},
    )

    assert hits
    assert all(hit.metadata["platform"] == "portswigger" for hit in hits)
