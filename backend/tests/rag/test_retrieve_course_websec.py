# Status: real

import pytest
from sqlalchemy import select

from app.db.models.learning.quiz_item import QuizItem
from app.db.seeds.seed_course_websec import run as seed_course_websec
from app.services.knowledge.retrieval_service import RetrievalService


RAG_SMOKE_QUERIES = [
    ("SQL 注入是什么", {"SQL", "注入"}),
    ("SQL 注入如何防御", {"SQL", "防御"}),
    ("参数化查询的作用", {"参数化", "查询"}),
    ("XSS 和 SQL 注入的区别", {"XSS", "SQL"}),
    ("文件上传漏洞风险", {"文件", "上传"}),
]


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
        assert hit.metadata["collection_mode"] == "manual"
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


@pytest.mark.anyio
async def test_course_websec_fixed_rag_smoke_queries(sqlite_session) -> None:
    await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    retriever = RetrievalService(sqlite_session)
    for query, expected_terms in RAG_SMOKE_QUERIES:
        hits = await retriever.retrieve(query, domain="course_websec", top_k=12)

        assert len(hits) >= 3, f"{query!r} should have enough evidence"
        joined = "\n".join(f"{hit.title}\n{hit.snippet}" for hit in hits)
        for term in expected_terms:
            assert term in joined, f"{query!r} should retrieve evidence containing {term!r}"


@pytest.mark.anyio
async def test_course_websec_seeds_sql_injection_quiz_items(sqlite_session) -> None:
    await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    quiz_items = (
        await sqlite_session.execute(
            select(QuizItem).where(QuizItem.question.like("%SQL 注入%"))
        )
    ).scalars().all()

    assert len(quiz_items) >= 5
    assert {item.type for item in quiz_items} >= {
        "single_choice",
        "multi_choice",
        "short_answer",
    }
    assert all(item.kp_id for item in quiz_items)
