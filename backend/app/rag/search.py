# Status: real

"""统一的 RAG 检索 service。

封装：
- ``retrieve`` 真实数据库查询；
- 兜底 fixture 注入（用于无数据库 / chunks 为空时仍能给前端展示证据）；
- 提供给 ``POST /api/v1/rag/search`` 端点直接调用。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.rag.evidence_builder import Evidence, build_evidence
from app.rag.reranker import rerank
from app.rag.retriever import EvidenceHit, retrieve
from app.runtime.harness.fixtures import default_evidence_fixtures


class RagSearchRequest(BaseModel):
    domain: str = "course_websec"
    query: str
    top_k: int = 5
    filters: dict[str, Any] | None = None


class RagSearchResponse(BaseModel):
    hits: list[EvidenceHit]
    evidence_cards: list[Evidence]
    fallback: bool = False


async def search(req: RagSearchRequest) -> RagSearchResponse:
    hits = await retrieve(
        req.query,
        domain=req.domain,
        top_k=req.top_k * 2,
        filter=req.filters,
    )
    fallback = False
    if not hits:
        fallback = True
        hits = [
            EvidenceHit(
                chunk_id=str(hit["chunk_id"]),
                document_id=hit.get("document_id"),
                domain=str(hit.get("domain") or req.domain),
                chunk_text=str(hit.get("chunk_text") or hit.get("excerpt") or ""),
                source=hit.get("source"),
                reliability=float(hit.get("reliability", 0.0)),
                score=float(hit.get("score", 0.0)),
                metadata=dict(hit.get("metadata") or {}),
            )
            for hit in default_evidence_fixtures(req.domain)
        ][: max(req.top_k, 3)]
    reordered = await rerank(req.query, hits, top_k=req.top_k)
    return RagSearchResponse(
        hits=reordered,
        evidence_cards=build_evidence(reordered),
        fallback=fallback,
    )
