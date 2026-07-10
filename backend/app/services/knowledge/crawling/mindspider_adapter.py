# Status: real

"""MindSpider reference-topic normalizer.

This adapter intentionally consumes only local fixture-style topic JSON. It
does not run MindSpider, register an agent, or create platform-specific tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge.ingestion_service import IngestionRequest, IngestionService
from app.services.storage.storage_service import StorageService


RIGHTS_NOTE = "MindSpider 参考级；仅 hot_analyst P2 demo；不涉及实际爬虫"


@dataclass(slots=True)
class NormalizedMindSpiderTopic:
    domain: str
    source_type: str
    title: str
    url: str
    raw_text: str
    raw_item: dict[str, Any]
    metadata: dict[str, Any]


@dataclass(slots=True)
class MindSpiderImportResult:
    document_ids: list[UUID]
    chunk_count: int
    asset_count: int
    topic_count: int
    domain: str = "news"


async def import_mindspider_fixture(
    fixture_path: Path,
    *,
    session: AsyncSession,
    domain: str = "news",
    storage_prefix: str = "news/mindspider_reference",
    storage_local_root: Path | None = None,
) -> MindSpiderImportResult:
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    topics = payload.get("topics", []) if isinstance(payload, dict) else []
    if not isinstance(topics, list):
        raise ValueError("MindSpider fixture must contain a topics list")

    storage = StorageService(session, local_root=storage_local_root)
    ingestion = IngestionService(session)
    document_ids: list[UUID] = []
    chunk_count = 0
    asset_count = 0
    topic_count = 0
    for topic in topics:
        if not isinstance(topic, dict):
            continue
        topic_count += 1
        source = normalize_mindspider_topic(topic, domain=domain)
        raw_item = redact_fixture_topic(source.raw_item)
        item_bytes = json.dumps(raw_item, ensure_ascii=False, indent=2).encode("utf-8")
        item_key = f"{storage_prefix}/{source.metadata['topic_id']}.json"
        await storage.put_bytes(
            object_key=item_key,
            content=item_bytes,
            mime_type="application/json; charset=utf-8",
            original_filename=fixture_path.name,
            metadata={
                "domain": domain,
                "asset_type": "media_item_json",
                "platform": "mindspider_reference",
                "source_url": source.url,
            },
        )
        result = await ingestion.ingest(
            IngestionRequest(
                domain=source.domain,
                source_type=source.source_type,
                title=source.title,
                url=source.url,
                raw_text=source.raw_text,
                content_hash=sha256(source.raw_text.encode("utf-8")).hexdigest(),
                metadata=source.metadata,
                assets=[
                    {
                        "asset_type": "media_item_json",
                        "object_key": item_key,
                        "mime_type": "application/json; charset=utf-8",
                        "size_bytes": len(item_bytes),
                        "content_hash": sha256(item_bytes).hexdigest(),
                        "metadata": {
                            "source_path": str(fixture_path),
                            "platform": "mindspider_reference",
                            "source_url": source.url,
                        },
                    }
                ],
            )
        )
        document_ids.append(result.document_id)
        chunk_count += result.chunk_count
        asset_count += result.asset_count

    return MindSpiderImportResult(
        document_ids=document_ids,
        chunk_count=chunk_count,
        asset_count=asset_count,
        topic_count=topic_count,
        domain=domain,
    )


def normalize_mindspider_topic(
    topic: dict[str, Any],
    *,
    domain: str = "news",
    fetched_at: datetime | None = None,
) -> NormalizedMindSpiderTopic:
    topic_id = _string_or_none(topic.get("topic_id")) or "mindspider-topic"
    keyword = _string_or_none(topic.get("keyword")) or topic_id
    abstract = _string_or_none(topic.get("abstract")) or ""
    platforms = _string_list(topic.get("platforms"))
    sample_urls = _string_list(topic.get("sample_urls"))
    collected_at = _string_or_none(topic.get("collected_at"))
    fetched = fetched_at or datetime.now(UTC)
    source_url = sample_urls[0] if sample_urls else f"mindspider-reference://{topic_id}"

    metadata = {
        "platform": "mindspider_reference",
        "source_url": source_url,
        "author": "MindSpider reference fixture",
        "published_at": collected_at,
        "fetched_at": fetched.isoformat(),
        "license": "reference fixture / non-commercial demo",
        "rights_note": RIGHTS_NOTE,
        "asset_type": "media_item_json",
        "collection_mode": "mindspider_reference",
        "topic_id": topic_id,
        "keyword": keyword,
        "hot_score": topic.get("hot_score"),
        "sentiment": topic.get("sentiment"),
        "cross_platforms": platforms,
        "sample_urls": sample_urls,
        "reliability": 0.45,
        "trust_score": 0.45,
    }

    raw_text = _build_topic_text(
        keyword=keyword,
        abstract=abstract,
        platforms=platforms,
        hot_score=topic.get("hot_score"),
        sentiment=_string_or_none(topic.get("sentiment")),
        sample_urls=sample_urls,
    )
    return NormalizedMindSpiderTopic(
        domain=domain,
        source_type="mindspider_reference",
        title=keyword,
        url=source_url,
        raw_text=raw_text,
        raw_item=topic,
        metadata=metadata,
    )


def _build_topic_text(
    *,
    keyword: str,
    abstract: str,
    platforms: list[str],
    hot_score: object,
    sentiment: str | None,
    sample_urls: list[str],
) -> str:
    parts = [
        f"# {keyword}",
        "",
        f"- 参考平台：{', '.join(platforms) if platforms else '未提供'}",
        f"- 热度分：{hot_score if hot_score is not None else '未提供'}",
    ]
    if sentiment:
        parts.append(f"- 情绪倾向：{sentiment}")
    if sample_urls:
        parts.append(f"- 样例链接：{sample_urls[0]}")
    parts.extend(["", "## 主题摘要", "", abstract or "（fixture 未提供摘要。）"])
    return "\n".join(parts)


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def redact_fixture_topic(topic: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "topic_id",
        "keyword",
        "platforms",
        "hot_score",
        "sample_urls",
        "collected_at",
        "sentiment",
        "abstract",
    }
    return {key: value for key, value in topic.items() if key in allowed}
