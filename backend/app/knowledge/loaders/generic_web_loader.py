# Status: real

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.loaders.course_loader import CourseLoadResult
from app.services.knowledge.crawling.crawler_policy import CrawlPolicy
from app.services.knowledge.crawling.scrapling_client import (
    ScrapedPage,
    ScraplingClient,
    ScraplingFetchOptions,
)
from app.services.knowledge.crawling.source_normalizer import (
    NormalizedSource,
    normalize_web_source,
)
from app.services.knowledge.ingestion_service import IngestionRequest, IngestionService
from app.services.storage.storage_service import StorageService


@dataclass(slots=True)
class WebSourceSpec:
    url: str
    title: str | None = None
    platform: str | None = None
    author: str | None = None
    published_at: str | None = None
    license: str = "unknown"
    rights_note: str | None = None
    source_type: str = "scrapling_public"
    asset_type: str = "web_article"
    reliability: float = 0.75
    css_selector: str | None = None
    xpath: str | None = None
    html_text: str | None = None
    metadata: dict[str, Any] | None = None


async def generic_web_import(
    sources: list[WebSourceSpec],
    *,
    session: AsyncSession,
    domain: str = "course_websec",
    storage_prefix: str = "course_websec/web",
    client: ScraplingClient | None = None,
    policy: CrawlPolicy | None = None,
    fetch_options: ScraplingFetchOptions | None = None,
) -> CourseLoadResult:
    active_policy = policy or CrawlPolicy()
    active_policy.validate_batch_size(len(sources))
    active_client = client or ScraplingClient(policy=active_policy)

    storage = StorageService(session)
    ingestion = IngestionService(session)
    document_ids: list[UUID] = []
    chunk_count = 0
    asset_count = 0

    for source in sources:
        page = (
            ScrapedPage.from_html(source.html_text, url=source.url)
            if source.html_text is not None
            else await active_client.fetch(source.url, options=fetch_options)
        )
        normalized = normalize_web_source(
            page,
            domain=domain,
            source_type=source.source_type,
            platform=source.platform,
            title=source.title,
            author=source.author,
            published_at=source.published_at,
            license=source.license,
            rights_note=source.rights_note,
            asset_type=source.asset_type,
            reliability=source.reliability,
            css_selector=source.css_selector,
            xpath=source.xpath,
            extra_metadata=source.metadata,
        )
        result = await _ingest_normalized_source(
            normalized,
            storage=storage,
            ingestion=ingestion,
            storage_prefix=storage_prefix,
        )
        document_ids.extend(result.document_ids)
        chunk_count += result.chunk_count
        asset_count += result.asset_count

    return CourseLoadResult(
        document_ids=document_ids,
        chunk_count=chunk_count,
        asset_count=asset_count,
        domain=domain,
    )


async def _ingest_normalized_source(
    source: NormalizedSource,
    *,
    storage: StorageService,
    ingestion: IngestionService,
    storage_prefix: str,
) -> CourseLoadResult:
    html_bytes = source.html_text.encode("utf-8")
    digest = sha256(html_bytes).hexdigest()
    object_key = f"{storage_prefix}/{_safe_url_key(source.url)}.html"
    await storage.put_bytes(
        object_key=object_key,
        content=html_bytes,
        mime_type="text/html; charset=utf-8",
        original_filename=f"{_safe_url_key(source.url)}.html",
        metadata={
            "domain": source.domain,
            "asset_type": "raw_html",
            "source_url": source.url,
            "platform": source.metadata.get("platform"),
        },
    )

    result = await ingestion.ingest(
        IngestionRequest(
            domain=source.domain,
            source_type=source.source_type,
            title=source.title,
            url=source.url,
            raw_text=source.raw_text,
            metadata=source.metadata,
            assets=[
                {
                    "asset_type": "raw_html",
                    "object_key": object_key,
                    "mime_type": "text/html; charset=utf-8",
                    "size_bytes": len(html_bytes),
                    "content_hash": digest,
                    "metadata": {
                        "source_url": source.url,
                        "platform": source.metadata.get("platform"),
                    },
                }
            ],
        )
    )
    return CourseLoadResult(
        document_ids=[result.document_id],
        chunk_count=result.chunk_count,
        asset_count=result.asset_count,
        domain=source.domain,
    )


def _safe_url_key(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "web").replace(".", "_")
    path = parsed.path.strip("/").replace("/", "_") or "index"
    suffix = sha256(url.encode("utf-8")).hexdigest()[:10]
    return f"{host}_{path}_{suffix}"
