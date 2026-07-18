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
import re
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.llm.embeddings.errors import EmbeddingError
from app.llm.embeddings.service import EmbeddingService

logger = logging.getLogger(__name__)

_MIN_CANDIDATE_POOL = 128
_CANDIDATE_MULTIPLIER = 16
_MAX_CANDIDATE_POOL = 2048


class EvidenceHit(BaseModel):
    chunk_id: UUID | str
    document_id: UUID | str | None = None
    domain: str
    chunk_text: str
    source: str | None = None
    reliability: float = Field(default=0.0, ge=0.0, le=1.0)
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


def _course_evidence_allowed(domain: str, metadata: dict[str, Any]) -> bool:
    """Keep retained supplementary imports out of the Web Security course."""
    return domain != "course_websec" or metadata.get("course_eligible") is not False


async def retrieve(
    query: str,
    *,
    domain: str = "course_websec",
    top_k: int = 8,
    filter: dict[str, Any] | None = None,
) -> list[EvidenceHit]:
    """返回针对 ``query`` 召回的 chunk hits。

    没有数据库 / 没有目标 profile 的 ready embedding 时返回空列表。
    Embedding provider 故障会显式传播，避免被误报为“没有证据”。
    """
    try:
        from app.db.models.chunk import Chunk
        from app.db.session import get_sessionmaker
    except Exception as exc:  # pragma: no cover - 仅当数据库层缺失时触发
        logger.warning("retriever: db layer unavailable, returning empty hits: %s", exc)
        return []

    try:
        settings = get_settings()
        service = EmbeddingService()
        try:
            query_result = await service.embed_query(query)
        finally:
            await service.aclose()
        if query_result.dimension != settings.EMBEDDING_DIM:
            raise ValueError(
                f"query embedding dimension {query_result.dimension} does not match "
                f"settings.EMBEDDING_DIM={settings.EMBEDDING_DIM}"
            )
        embedding = query_result.vectors[0]

        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            candidate_limit = min(
                max(top_k * _CANDIDATE_MULTIPLIER, _MIN_CANDIDATE_POOL),
                _MAX_CANDIDATE_POOL,
            )
            stmt = (
                select(Chunk)
                .where(Chunk.domain == domain)
                .where(Chunk.embedding_status == "ready")
                .where(Chunk.embedding.is_not(None))
                .where(Chunk.metadata_["embedding_profile"].as_string() == settings.EMBEDDING_PROFILE)
                .order_by(Chunk.id.asc())
                .limit(candidate_limit)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            if not rows:
                return []

            hits: list[EvidenceHit] = []
            query_terms = _tokenise(query)
            for chunk in rows:
                keyword_score = 0.0
                low = (chunk.chunk_text or "").lower()
                for token in query_terms:
                    if token in low:
                        keyword_score += 0.1
                vec_score = 0.0
                if chunk.embedding is not None and embedding:
                    try:
                        doc_vector = list(chunk.embedding)
                        if len(doc_vector) != settings.EMBEDDING_DIM:
                            logger.warning(
                                "retriever: skipping chunk %s with dimension %s",
                                chunk.id,
                                len(doc_vector),
                            )
                            continue
                        vec_score = _cosine(embedding, doc_vector)
                    except Exception:  # noqa: BLE001
                        vec_score = 0.0
                combined = 0.6 * vec_score + 0.4 * min(keyword_score, 1.0)
                if combined <= 0:
                    continue
                metadata = chunk.metadata_ if hasattr(chunk, "metadata_") else {}
                # Imported PDFs may remain in the unified knowledge tables for
                # later domains, while only course-eligible evidence may serve
                # the Web Security Basics product path.
                if not _course_evidence_allowed(domain, metadata):
                    continue
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
    except EmbeddingError:
        raise
    except ValueError:
        raise
    except Exception as exc:  # pragma: no cover
        logger.warning("retriever: unexpected error: %s", exc)
        return []


def _tokenise(query: str) -> list[str]:
    """Extract stable ASCII terms and CJK phrases/bigrams for keyword fusion."""
    lowered = (query or "").lower()
    ascii_terms = re.findall(r"[a-z0-9_+-]{2,}", lowered)
    cjk_terms = re.findall(r"[\u4e00-\u9fff]{2,}", lowered)
    expanded: list[str] = []
    for term in cjk_terms:
        expanded.append(term)
        if len(term) > 2:
            expanded.extend(term[index : index + 2] for index in range(len(term) - 1))
    return list(dict.fromkeys(ascii_terms + expanded))


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
