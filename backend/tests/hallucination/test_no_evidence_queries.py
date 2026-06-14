# Status: real

import pytest

from app.db.seeds.seed_course_websec import run as seed_course_websec
from app.services.knowledge.retrieval_service import ChunkHit, RetrievalService


class InsufficientEvidence(RuntimeError):
    pass


async def _compose_only_with_evidence(
    hits: list[ChunkHit],
    *,
    llm_called: list[bool],
    evidence_floor: int = 3,
) -> str:
    if len(hits) < evidence_floor:
        raise InsufficientEvidence("至少需要 3 条证据才能生成。")
    llm_called.append(True)
    return "generated"


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
