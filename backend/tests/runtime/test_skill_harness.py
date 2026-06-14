# Status: real

import asyncio

import pytest

from app.agents._examples.echo_skill import EchoSkill
from app.runtime.harness import Harness, HarnessConfig, HarnessContext, InsufficientEvidence
from app.runtime.harness.fixtures import ChunkHit, MockLLM, MockQualityCheck, MockRetriever


def make_hits(count: int) -> list[ChunkHit]:
    return [
        ChunkHit(
            chunk_id=f"chunk-{idx}",
            document_id="doc-owasp-sql-injection",
            source_url="https://owasp.org/www-community/attacks/SQL_Injection",
            excerpt=f"SQL injection evidence {idx}.",
            chapter="SQL 注入基础",
        )
        for idx in range(count)
    ]


async def run_harness(hits: list[ChunkHit]) -> tuple[object, list[tuple[str, object]], HarnessContext, MockLLM]:
    events: list[tuple[str, object]] = []

    async def writer(event: str, data: object) -> None:
        events.append((event, data))

    retriever = MockRetriever(hits)
    llm = MockLLM()
    quality = MockQualityCheck(score=0.91)
    harness = Harness(retriever=retriever, llm=llm, quality_checker=quality, storage_service=None)
    ctx = HarnessContext(
        user_id="00000000-0000-0000-0000-000000000001",
        course_id="course_websec_intro",
        stream=True,
        sse_writer=writer,
        config=HarnessConfig(min_evidence=1, mock_mode=True, llm_provider="mock"),
    )
    out = await harness.run(EchoSkill(), {"query": "SQL injection"}, ctx)
    return out, events, ctx, llm


def test_skill_harness_happy_path_emits_evidence_and_logs_run() -> None:
    out, events, ctx, llm = asyncio.run(run_harness(make_hits(3)))

    assert out.echoed == "Echo: SQL injection"
    assert out.evidence_chunk_ids == ["chunk-0", "chunk-1", "chunk-2"]
    assert any(event == "evidence" for event, _data in events)
    assert ctx.logged_runs
    assert len(llm.calls) == 1


def test_skill_harness_blocks_llm_when_evidence_is_insufficient() -> None:
    async def scenario() -> MockLLM:
        retriever = MockRetriever([])
        llm = MockLLM()
        harness = Harness(retriever=retriever, llm=llm, quality_checker=MockQualityCheck(), storage_service=None)
        ctx = HarnessContext(config=HarnessConfig(mock_mode=True))
        with pytest.raises(InsufficientEvidence):
            await harness.run(EchoSkill(), {"query": "SQL injection"}, ctx)
        return llm

    llm = asyncio.run(scenario())

    assert llm.calls == []


def test_skill_harness_sse_event_order() -> None:
    _out, events, _ctx, _llm = asyncio.run(run_harness(make_hits(3)))

    event_names = [event for event, _data in events]
    assert event_names == [
        "progress",
        "progress",
        "evidence",
        "progress",
        "token",
        "progress",
        "trace",
        "done",
    ]
    progress_nodes = [data["node_name"] for event, data in events if event == "progress"]
    assert progress_nodes == ["validate", "retrieve", "compose", "quality_check"]
