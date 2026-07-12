# Status: real

"""Mode-explicit RAG retrieval for the public evidence endpoint."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from app.llm.embeddings.errors import EmbeddingError
from app.rag.evidence_builder import Evidence, build_evidence
from app.rag.reranker import rerank
from app.rag.retriever import EvidenceHit, retrieve
from app.runtime.harness.fixtures import default_evidence_fixtures


class RagSearchRequest(BaseModel):
    domain: str = "course_websec"
    query: str
    top_k: int = 5
    filters: dict[str, Any] | None = None
    mode: Literal["fixture", "real"] = "real"


class RagSearchResponse(BaseModel):
    hits: list[EvidenceHit]
    evidence_cards: list[Evidence]
    mode: Literal["fixture", "real"]


class RagSearchUnavailable(RuntimeError):
    """A real retrieval request cannot fabricate fixture evidence."""


async def search(req: RagSearchRequest) -> RagSearchResponse:
    if req.mode == "fixture":
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
    else:
        try:
            hits = await retrieve(
                req.query,
                domain=req.domain,
                top_k=req.top_k * 2,
                filter=req.filters,
            )
        except EmbeddingError as exc:
            # Provider configuration, authentication and rate limits are an
            # unavailable real retrieval dependency, never permission to
            # substitute fixture evidence.
            raise RagSearchUnavailable("real RAG embedding dependency is unavailable") from exc
        if not hits:
            raise RagSearchUnavailable("real RAG retrieval returned no evidence")
    reordered = await rerank(req.query, hits, top_k=req.top_k)
    return RagSearchResponse(
        hits=reordered,
        evidence_cards=build_evidence(reordered),
        mode=req.mode,
    )
