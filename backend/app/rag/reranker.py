# Status: [planned]

from app.rag.retriever import EvidenceHit


async def rerank(query: str, hits: list[EvidenceHit], *, top_k: int = 5) -> list[EvidenceHit]:
    raise NotImplementedError("TODO: rerank hits with BGE reranker or small LLM")
