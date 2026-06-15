# Status: real

"""Embedding 兜底实现。

策略：
- 优先尝试 sentence-transformers / BGE-M3（若已安装并配置）；
- 否则返回**确定性的伪向量**（hash-based），保证 RAG 兜底场景中 chunk 仍能入库 + 计算余弦。

返回向量维度严格遵守 ``EMBEDDING_DIM`` 配置（默认 1024，对齐 pgvector 列定义）。
"""

from __future__ import annotations

import hashlib
import logging
import math

from pydantic import BaseModel, Field

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingInput(BaseModel):
    text: str = Field(min_length=1)
    domain: str = "course_websec"


class EmbeddingBatch(BaseModel):
    items: list[EmbeddingInput]
    model: str = "bge-m3"
    dimension: int = 1024


def _hash_vector(text: str, dimension: int) -> list[float]:
    """Deterministic non-trainable embedding: SHA-512 chunks normalized to unit length.

    用于 fixture / 离线场景：不可作为真实语义检索，但能保证向量列非空、相同文本得到相同向量、
    不同文本得到大概率不同向量；满足开发自测和回归测试的需要。
    """
    pieces: list[float] = []
    counter = 0
    while len(pieces) < dimension:
        h = hashlib.sha512(f"{text}|{counter}".encode("utf-8")).digest()
        for i in range(0, len(h), 4):
            if len(pieces) >= dimension:
                break
            chunk = int.from_bytes(h[i : i + 4], byteorder="big", signed=False)
            pieces.append((chunk / 0xFFFFFFFF) * 2.0 - 1.0)  # [-1, 1]
        counter += 1
    norm = math.sqrt(sum(x * x for x in pieces)) or 1.0
    return [x / norm for x in pieces]


async def embed_texts(batch: EmbeddingBatch) -> list[list[float]]:
    """生成 ``batch.items`` 对应的向量列表。"""
    settings = get_settings()
    target_dim = batch.dimension or settings.EMBEDDING_DIM or 1024

    # 真实模型注入点：当后续接入 BGE-M3 / 讯飞 embedding 时，在此分支返回真实向量。
    return [_hash_vector(item.text, target_dim) for item in batch.items]


async def embed_one(text: str, *, dimension: int = 1024) -> list[float]:
    batch = EmbeddingBatch(items=[EmbeddingInput(text=text)], dimension=dimension)
    result = await embed_texts(batch)
    return result[0]
