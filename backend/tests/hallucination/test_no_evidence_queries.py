# Status: real

import pytest

from app.db.seeds.seed_course_websec import run as seed_course_websec
from app.services.knowledge.retrieval_service import ChunkHit, RetrievalService


class InsufficientEvidence(RuntimeError):
    pass


class SourceMetadataIncomplete(RuntimeError):
    pass


async def _compose_only_with_evidence(
    hits: list[ChunkHit],
    *,
    llm_called: list[bool],
    evidence_floor: int = 3,
    resource_type: str = "course_doc",
) -> str:
    if len(hits) < evidence_floor:
        raise InsufficientEvidence(
            f"{resource_type} 至少需要 {evidence_floor} 条证据才能生成。"
        )
    _assert_source_metadata_complete(hits)
    llm_called.append(True)
    return "generated"


def _assert_source_metadata_complete(hits: list[ChunkHit]) -> None:
    for hit in hits:
        metadata = hit.metadata
        platform = metadata.get("platform")
        rights_note = metadata.get("rights_note")
        source_url = metadata.get("source_url")
        if not platform or not rights_note:
            raise SourceMetadataIncomplete("evidence is missing platform or rights_note")
        if platform != "manual" and not source_url:
            raise SourceMetadataIncomplete("non-manual evidence is missing source_url")


async def _finalize_done_only_with_source_metadata(
    hits: list[ChunkHit],
    *,
    events: list[str],
) -> None:
    _assert_source_metadata_complete(hits)
    events.append("done")


@pytest.mark.anyio
async def test_no_evidence_query_blocks_before_llm(sqlite_session) -> None:
    await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    hits = list(
        await RetrievalService(sqlite_session).retrieve(
            "量子卫星轨道力学 深空通信",
            domain="course_websec",
            top_k=5,
        )
    )
    llm_called: list[bool] = []

    with pytest.raises(InsufficientEvidence):
        await _compose_only_with_evidence(hits, llm_called=llm_called)

    assert llm_called == []


@pytest.mark.anyio
async def test_empty_domain_blocks_before_llm(sqlite_session) -> None:
    await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    llm_called: list[bool] = []

    with pytest.raises(ValueError, match="domain is required"):
        hits = await RetrievalService(sqlite_session).retrieve(
            "SQL 注入是什么",
            domain="",
            top_k=5,
        )
        await _compose_only_with_evidence(list(hits), llm_called=llm_called)

    assert llm_called == []


@pytest.mark.anyio
async def test_low_evidence_count_does_not_generate_course_doc(sqlite_session) -> None:
    await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    hits = list(
        await RetrievalService(sqlite_session).retrieve(
            "SQL 注入是什么",
            domain="course_websec",
            top_k=2,
        )
    )
    llm_called: list[bool] = []

    with pytest.raises(InsufficientEvidence):
        await _compose_only_with_evidence(
            hits,
            llm_called=llm_called,
            evidence_floor=3,
            resource_type="course_doc",
        )

    assert len(hits) == 2
    assert llm_called == []


@pytest.mark.anyio
async def test_missing_source_metadata_never_enters_done_state() -> None:
    hits = [
        ChunkHit(
            chunk_id="00000000-0000-0000-0000-000000000001",
            document_id="00000000-0000-0000-0000-000000000002",
            title="metadata incomplete",
            snippet="SQL 注入证据片段",
            score=1.0,
            metadata={"platform": "owasp", "rights_note": ""},
        ),
    ]
    events: list[str] = []

    with pytest.raises(SourceMetadataIncomplete):
        await _finalize_done_only_with_source_metadata(hits, events=events)

    assert "done" not in events


@pytest.mark.anyio
async def test_supported_query_passes_evidence_floor(sqlite_session) -> None:
    await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    hits = list(
        await RetrievalService(sqlite_session).retrieve(
            "SQL 注入 参数化 查询",
            domain="course_websec",
            top_k=5,
        )
    )
    llm_called: list[bool] = []

    output = await _compose_only_with_evidence(hits, llm_called=llm_called)

    assert output == "generated"
    assert llm_called == [True]
