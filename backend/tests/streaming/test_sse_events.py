# Status: real

"""SSE 事件序列化和响应封装测试。"""

from __future__ import annotations

import pytest

from app.streaming.events import (
    DoneEvent,
    ErrorEvent,
    EvidenceEvent,
    ProgressEvent,
    TokenEvent,
)


def test_token_event_serializes_to_sse_format():
    event = TokenEvent(content="Hello", event="token")
    sse_text = event.to_sse()
    assert sse_text.startswith("event: token\n")
    assert "data:" in sse_text
    assert "Hello" in sse_text


def test_evidence_event_serializes_to_sse_format():
    event = EvidenceEvent(
        event="evidence",
        chunk_id="chunk-1",
        source="OWASP",
        excerpt="SQL injection occurs when...",
        reliability=0.95,
    )
    sse_text = event.to_sse()
    assert sse_text.startswith("event: evidence\n")
    assert "chunk-1" in sse_text
    assert "OWASP" in sse_text


def test_progress_event_serializes_to_sse_format():
    event = ProgressEvent(
        event="progress",
        node_name="retrieve",
        status="running",
        agent_id="career_planner",
        skill_id="BuildLearningPersona",
        percentage=20,
    )
    sse_text = event.to_sse()
    assert "event: progress" in sse_text
    assert "retrieve" in sse_text


def test_done_event_serializes_to_sse_format():
    event = DoneEvent(
        event="done",
        run_id="run-1",
        final_output_ref="agent_runs/run-1",
        quality_score=0.92,
    )
    sse_text = event.to_sse()
    assert "event: done" in sse_text
    assert "run-1" in sse_text


def test_error_event_serializes_to_sse_format():
    event = ErrorEvent(
        event="error",
        code="INSUFFICIENT_EVIDENCE",
        message="Not enough evidence chunks",
        recoverable=False,
    )
    sse_text = event.to_sse()
    assert "event: error" in sse_text
    assert "INSUFFICIENT_EVIDENCE" in sse_text


def test_sse_response_factory_importable():
    from app.streaming.sse import sse_response

    assert callable(sse_response)
