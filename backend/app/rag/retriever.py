# Status: real

"""RAG 检索器（pgvector + 关键词 score fusion）。

设计：
- 真实模式：从 ``chunks`` 表用 cosine 相似度 + 简单 keyword score 召回 top_k；
- 兜底模式（DB / 向量未就绪）：返回空列表，让 harness 在评估 evidence_floor 时再决定是否
  降级到 fixture；
- ``filter`` 支持 ``domain`` / ``platform`` / ``source_type`` 等 metadata 字段过滤。
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.llm.embedding import embed_one

logger = logging.getLogger(__name__)


class EvidenceHit(BaseModel):
    chunk_id: UUID | str
    document_id: UUID | str | None = None
    domain: str
    chunk_text: str
    source: str | None = None
    reliability: float = Field(default=0.0, ge=0.0, le=1.0)
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


async def retrieve(
    query: str,
    *,
    domain: str = "course_websec",
    top_k: int = 8,
    filter: dict[str, Any] | None = None,
) -> list[EvidenceHit]:
    """返回针对 ``query`` 召回的 chunk hits。

    没有数据库 / 没有 ready 的 embedding 时直接返回空列表，调用方应自行决定是否兜底。
    """
    try:
        from app.db.models.chunk import Chunk
        from app.db.session import get_sessionmaker
    except Exception as exc:  # pragma: no cover - 仅当数据库层缺失时触发
        logger.warning("retriever: db layer unavailable, returning empty hits: %s", exc)
        return []

    try:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            # 先做 keyword score 兜底，能在无 embedding 时仍命中
            stmt = (
                select(Chunk)
                .where(Chunk.domain == domain)
                .limit(top_k * 4)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            if not rows:
                return []

            embedding = await embed_one(query, dimension=getattr(rows[0].embedding, "__len__", lambda: 1024)() if rows[0].embedding else 1024)

            hits: list[EvidenceHit] = []
            q_lower = (query or "").lower()
            for chunk in rows:
                keyword_score = 0.0
                low = (chunk.chunk_text or "").lower()
                for token in [t for t in q_lower.split() if t]:
                    if token in low:
                        keyword_score += 0.1
                vec_score = 0.0
                if chunk.embedding is not None and embedding:
                    try:
                        vec_score = _cosine(embedding, list(chunk.embedding))
                    except Exception:  # noqa: BLE001
                        vec_score = 0.0
                combined = 0.6 * vec_score + 0.4 * min(keyword_score, 1.0)
                if combined <= 0:
                    continue
                metadata = chunk.metadata_ if hasattr(chunk, "metadata_") else {}
                if filter:
                    skip = False
                    for fk, fv in filter.items():
                        actual = metadata.get(fk)
                        if isinstance(fv, list):
                            if actual not in fv:
                                skip = True
                                break
                        elif actual != fv:
                            skip = True
                            break
                    if skip:
                        continue
                hits.append(
                    EvidenceHit(
                        chunk_id=str(chunk.id),
                        document_id=str(chunk.document_id) if chunk.document_id else None,
                        domain=chunk.domain,
                        chunk_text=chunk.chunk_text or "",
                        source=(metadata or {}).get("source") or (metadata or {}).get("url"),
                        reliability=float((metadata or {}).get("reliability", 0.6)),
                        score=combined,
                        metadata=metadata or {},
                    )
                )
            hits.sort(key=lambda h: h.score, reverse=True)
            return hits[:top_k]
    except SQLAlchemyError as exc:
        logger.warning("retriever: DB query failed: %s", exc)
        return []
    except Exception as exc:  # pragma: no cover
        logger.warning("retriever: unexpected error: %s", exc)
        return []


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    # 已经是单位向量时无需归一；保险起见仍处理一遍
    import math

    norm_a = math.sqrt(sum(x * x for x in a[:n])) or 1.0
    norm_b = math.sqrt(sum(x * x for x in b[:n])) or 1.0
    return dot / (norm_a * norm_b)
