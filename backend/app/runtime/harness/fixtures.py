# Status: real

from datetime import UTC, datetime

from pydantic import BaseModel


class EvidenceChunkDTO(BaseModel):
    chunk_id: str
    document_id: str
    source_url: str | None = None
    platform: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime | None = None
    rights_note: str | None = None
    asset_type: str | None = None
    excerpt: str
    page_no: int | None = None
    chapter: str | None = None
    timestamp: float | None = None
    reliability: float | None = None


class ChunkHit(BaseModel):
    chunk_id: str
    document_id: str
    excerpt: str
    source_url: str | None = None
    platform: str | None = "owasp"
    author: str | None = "OWASP"
    published_at: datetime | None = None
    fetched_at: datetime | None = None
    rights_note: str | None = "CC BY-SA 4.0"
    asset_type: str | None = "web_article"
    page_no: int | None = None
    chapter: str | None = None
    timestamp: float | None = None
    reliability: float | None = 0.9

    def to_dto(self) -> EvidenceChunkDTO:
        return EvidenceChunkDTO(**self.model_dump())


class MockLLM:
    def __init__(self, response: str | None = None) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    async def chat(self, prompt: str, stream: bool = False) -> str:
        self.calls.append({"prompt": prompt, "stream": stream})
        return self.response or prompt


class MockRetriever:
    def __init__(self, hits: list[ChunkHit] | None = None) -> None:
        self.hits = hits
        self.calls: list[dict[str, object]] = []

    async def retrieve(self, query: str, domain: str, top_k: int) -> list[ChunkHit]:
        self.calls.append({"query": query, "domain": domain, "top_k": top_k})
        if self.hits is not None:
            return self.hits[:top_k]
        now = datetime.now(UTC)
        return [
            ChunkHit(
                chunk_id=f"chunk-{idx}",
                document_id="doc-owasp-sql-injection",
                source_url="https://owasp.org/www-community/attacks/SQL_Injection",
                fetched_at=now,
                excerpt=f"SQL injection fixture evidence {idx}.",
                chapter="SQL 注入基础",
            )
            for idx in range(1, top_k + 1)
        ]


class MockQualityCheck:
    def __init__(self, score: float = 0.86) -> None:
        self.score = score
        self.calls: list[dict[str, object]] = []

    async def check(self, output: BaseModel, evidences: list[ChunkHit]) -> float:
        self.calls.append({"output": output, "evidence_count": len(evidences)})
        return self.score
