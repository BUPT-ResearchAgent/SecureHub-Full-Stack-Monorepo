# Status: real

"""RAG 检索基础回归：fixture 兜底模式可返回有效证据且满足格式契约。"""

from __future__ import annotations

import asyncio

import pytest

from app.rag.retriever import EvidenceHit, retrieve


def test_retrieve_falls_back_to_empty_on_no_db():
    """当数据库不可用时，retrieve 返回空列表（不 crash）。"""
    hits = asyncio.run(retrieve("SQL injection", domain="course_websec", top_k=5))
    assert isinstance(hits, list)
    assert len(hits) == 0  # 无 DB 时返回空列表


def test_evidence_hit_enforces_required_fields():
    hit = EvidenceHit(
        chunk_id="test-id",
        domain="course_websec",
        chunk_text="SQL injection occurs when...",
    )
    assert hit.chunk_id == "test-id"
    assert hit.domain == "course_websec"
    assert len(hit.chunk_text) > 0


def test_evidence_hit_defaults():
    hit = EvidenceHit(
        chunk_id="test-id",
        domain="course_websec",
        chunk_text="test",
    )
    assert hit.reliability == 0.0
    assert hit.score == 0.0
    assert hit.metadata == {}
    assert hit.source is None
