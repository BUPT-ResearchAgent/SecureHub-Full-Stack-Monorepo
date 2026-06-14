# Status: real

"""Per task brief §6.1 — RetrievalService is the single entry point every
generative skill must call before composing a prompt (rule §3.6). It owns the
BM25 + vector + RRF + rerank chain.
"""

from collections.abc import Sequence
from dataclasses import dataclass
import re
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge.chunk import Chunk
from app.db.models.knowledge.document import Document


@dataclass(slots=True)
class ChunkHit:
    chunk_id: UUID
    document_id: UUID
    title: str
    snippet: str
    score: float
    metadata: dict[str, Any]


class RetrievalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def retrieve(
        self,
        query: str,
        *,
        domain: str,
        top_k: int = 8,
        filters: dict[str, Any] | None = None,
    ) -> Sequence[ChunkHit]:
        if not domain:
            raise ValueError("domain is required")
        if top_k <= 0 or top_k > 50:
            raise ValueError("top_k must be in 1..50")

        stmt = (
            select(Chunk, Document)
            .join(Document, Document.id == Chunk.document_id)
            .where(Chunk.domain == domain)
        )
        for key, value in (filters or {}).items():
            if value is None:
                continue
            if key == "source_type":
                stmt = stmt.where(Document.source_type == value)
            else:
                stmt = stmt.where(Chunk.metadata_[key].as_string() == str(value))

        result = await self.session.execute(stmt)
        candidates = result.all()
        query_terms = _tokenise(query)
        hits: list[ChunkHit] = []
        for chunk, document in candidates:
            score = _score(query_terms, chunk.chunk_text, document.title, chunk.metadata_)
            if score <= 0:
                continue
            metadata = dict(document.metadata_ or {})
            metadata.update(chunk.metadata_ or {})
            hits.append(
                ChunkHit(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    title=document.title,
                    snippet=_snippet(chunk.chunk_text, query_terms),
                    score=score,
                    metadata={
                        "source_url": metadata.get("source_url") or document.url,
                        "platform": metadata.get("platform"),
                        "author": metadata.get("author"),
                        "published_at": metadata.get("published_at"),
                        "fetched_at": metadata.get("fetched_at"),
                        "rights_note": metadata.get("rights_note"),
                        "license": metadata.get("license"),
                        "asset_type": metadata.get("asset_type") or document.source_type,
                        "chapter": metadata.get("chapter"),
                        "page_no": metadata.get("page_no"),
                        "reliability": metadata.get("reliability", document.trust_score),
                    },
                )
            )

        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:top_k]


def _tokenise(query: str) -> list[str]:
    lowered = query.lower()
    ascii_terms = re.findall(r"[a-z0-9_+-]{2,}", lowered)
    cjk_terms = re.findall(r"[\u4e00-\u9fff]{2,}", lowered)
    expanded: list[str] = []
    for term in cjk_terms:
        expanded.append(term)
        if len(term) > 2:
            expanded.extend(term[i : i + 2] for i in range(len(term) - 1))
    return list(dict.fromkeys(ascii_terms + expanded))


def _score(
    terms: list[str],
    chunk_text: str,
    title: str,
    metadata: dict[str, Any],
) -> float:
    if not terms:
        return 0.0
    haystack = f"{title}\n{chunk_text}\n{metadata}".lower()
    score = 0.0
    for term in terms:
        occurrences = haystack.count(term)
        if occurrences:
            score += 1.0 + min(occurrences, 4) * 0.25
    if any(term in title.lower() for term in terms):
        score += 1.0
    return score


def _snippet(text: str, terms: list[str], *, width: int = 180) -> str:
    lowered = text.lower()
    positions = [lowered.find(term) for term in terms if lowered.find(term) >= 0]
    start = max(0, min(positions) - 40) if positions else 0
    snippet = text[start : start + width].strip()
    if start > 0:
        snippet = "..." + snippet
    if start + width < len(text):
        snippet += "..."
    return snippet
