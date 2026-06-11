# Status: real

"""文档切分器。

策略：
- 按段落 / 句号优先切分；
- 控制每个 chunk 在 ``chunk_size`` 上下，相邻 chunk 之间保留 ``overlap`` 字符的重叠；
- 维护 ``chunk_index`` 与近似 ``token_count``（字数 / 1.6 估算）。
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

_SENTENCE_END = re.compile(r"(?<=[。！？!?\.\n])\s+")


class TextChunk(BaseModel):
    chunk_text: str
    chunk_index: int
    token_count: int
    metadata: dict[str, str] = Field(default_factory=dict)


def _split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_END.split(text) if p.strip()]
    if parts:
        return parts
    return [text.strip()] if text.strip() else []


def _approx_tokens(text: str) -> int:
    # 粗略估算：中文 1 字 ≈ 1 token，英文按空格分；最终除以 1.4 做兜底
    chinese = sum(1 for ch in text if "一" <= ch <= "鿿")
    english_words = len(re.findall(r"[A-Za-z]+", text))
    return max(1, int((chinese + english_words) / 1.0))


def chunk_document(
    text: str,
    *,
    chunk_size: int = 700,
    overlap: int = 100,
) -> list[TextChunk]:
    """将整段文本切成重叠的 ``TextChunk`` 列表。"""
    text = (text or "").strip()
    if not text:
        return []

    if len(text) <= chunk_size:
        return [
            TextChunk(
                chunk_text=text,
                chunk_index=0,
                token_count=_approx_tokens(text),
            )
        ]

    sentences = _split_sentences(text)
    chunks: list[TextChunk] = []
    buf = ""
    for sentence in sentences:
        if len(buf) + len(sentence) + 1 <= chunk_size or not buf:
            buf = f"{buf} {sentence}".strip() if buf else sentence
            continue
        chunks.append(
            TextChunk(
                chunk_text=buf,
                chunk_index=len(chunks),
                token_count=_approx_tokens(buf),
            )
        )
        # overlap: 从上一 chunk 末尾抓 overlap 个字符再串接当前 sentence
        tail = buf[-overlap:] if overlap > 0 else ""
        buf = (tail + " " + sentence).strip()
    if buf:
        chunks.append(
            TextChunk(
                chunk_text=buf,
                chunk_index=len(chunks),
                token_count=_approx_tokens(buf),
            )
        )
    return chunks
