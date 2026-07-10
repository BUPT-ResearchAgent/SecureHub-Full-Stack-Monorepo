# Status: real

"""Reranker：在多路召回 hits 之上按 keyword + reliability 重排，截取 top_k。

P0 阶段：不接 BGE Reranker / LLM rerank，使用启发式打分；接口预留，后续接入直接替换实现。
"""

from __future__ import annotations

from app.rag.retriever import EvidenceHit


async def rerank(
    query: str,
    hits: list[EvidenceHit],
    *,
    top_k: int = 5,
) -> list[EvidenceHit]:
    if not hits:
        return []
    q_tokens = [t for t in (query or "").lower().split() if t]

    def score(hit: EvidenceHit) -> float:
        keyword_bonus = 0.0
        body = (hit.chunk_text or "").lower()
        for tok in q_tokens:
            if tok in body:
                keyword_bonus += 0.05
        return hit.score + keyword_bonus + 0.1 * hit.reliability

    reordered = sorted(hits, key=score, reverse=True)
    return reordered[:top_k]
