# Status: [planned]

from pydantic import BaseModel

from app.rag.retriever import EvidenceHit


class Evidence(BaseModel):
    chunk_id: str
    source: str
    excerpt: str
    reliability: float
    citation: str


def build_evidence(hits: list[EvidenceHit]) -> list[Evidence]:
    return [
        Evidence(
            chunk_id=str(hit.chunk_id),
            source=hit.source or "unknown",
            excerpt=hit.chunk_text[:240],
            reliability=hit.reliability,
            citation=f"{hit.source or 'unknown'}#{hit.chunk_id}",
        )
        for hit in hits
    ]
