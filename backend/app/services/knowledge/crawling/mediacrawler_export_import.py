# Status: real

from __future__ import annotations

import csv
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge.crawling.media_source_normalizer import (
    NormalizedMediaSource,
    infer_item_type,
    media_parent_key,
    normalize_mediacrawler_content,
    normalize_platform,
)
from app.services.knowledge.ingestion_service import IngestionRequest, IngestionService
from app.services.storage.storage_service import StorageService


@dataclass(slots=True)
class MediaCrawlerImportResult:
    document_ids: list[UUID]
    chunk_count: int
    asset_count: int
    content_count: int
    comment_count: int
    domain: str = "course_websec"


async def import_mediacrawler_exports(
    paths: list[Path],
    *,
    session: AsyncSession,
    platform: str | None = None,
    domain: str = "course_websec",
    storage_prefix: str = "course_websec/mediacrawler",
    rights_note: str | None = None,
) -> MediaCrawlerImportResult:
    contents: list[tuple[dict[str, Any], Path]] = []
    comments: list[tuple[dict[str, Any], Path]] = []
    for path in _expand_paths(paths):
        for item in _read_export_items(path):
            item_type = infer_item_type(item, file_hint=path.name)
            if item_type == "comments":
                comments.append((item, path))
            elif item_type == "contents":
                contents.append((item, path))

    grouped_comments: dict[str, list[dict[str, Any]]] = {}
    for comment, _path in comments:
        key = media_parent_key(comment, platform=platform)
        if key is not None:
            grouped_comments.setdefault(key, []).append(comment)

    storage = StorageService(session)
    ingestion = IngestionService(session)
    document_ids: list[UUID] = []
    chunk_count = 0
    asset_count = 0
    for item, source_path in contents:
        parent_key = media_parent_key(item, platform=platform)
        normalized = normalize_mediacrawler_content(
            item,
            platform=platform or _platform_from_path(source_path) or None,
            domain=domain,
            comments=grouped_comments.get(parent_key or "", []),
            rights_note=rights_note,
        )
        result = await _ingest_media_source(
            normalized,
            source_path=source_path,
            storage=storage,
            ingestion=ingestion,
            storage_prefix=storage_prefix,
        )
        document_ids.append(result.document_ids[0])
        chunk_count += result.chunk_count
        asset_count += result.asset_count

    return MediaCrawlerImportResult(
        document_ids=document_ids,
        chunk_count=chunk_count,
        asset_count=asset_count,
        content_count=len(contents),
        comment_count=len(comments),
        domain=domain,
    )


async def _ingest_media_source(
    source: NormalizedMediaSource,
    *,
    source_path: Path,
    storage: StorageService,
    ingestion: IngestionService,
    storage_prefix: str,
) -> MediaCrawlerImportResult:
    item_bytes = json.dumps(source.raw_item, ensure_ascii=False, indent=2).encode("utf-8")
    item_key = f"{storage_prefix}/{source.platform}/{_safe_media_key(source)}.json"
    await storage.put_bytes(
        object_key=item_key,
        content=item_bytes,
        mime_type="application/json; charset=utf-8",
        original_filename=source_path.name,
        metadata={
            "domain": source.domain,
            "asset_type": "media_item_json",
            "platform": source.platform,
            "source_url": source.url,
        },
    )
    item_hash = sha256(item_bytes).hexdigest()

    assets = [
        {
            "asset_type": "media_item_json",
            "object_key": item_key,
            "mime_type": "application/json; charset=utf-8",
            "size_bytes": len(item_bytes),
            "content_hash": item_hash,
            "metadata": {
                "source_path": str(source_path),
                "platform": source.platform,
                "source_url": source.url,
            },
        }
    ]

    if source.comments:
        comments_bytes = json.dumps(source.comments, ensure_ascii=False, indent=2).encode("utf-8")
        comments_key = f"{storage_prefix}/{source.platform}/{_safe_media_key(source)}.comments.json"
        await storage.put_bytes(
            object_key=comments_key,
            content=comments_bytes,
            mime_type="application/json; charset=utf-8",
            original_filename=f"{source_path.stem}.comments.json",
            metadata={
                "domain": source.domain,
                "asset_type": "media_comment_json",
                "platform": source.platform,
                "source_url": source.url,
            },
        )
        assets.append(
            {
                "asset_type": "media_comment_json",
                "object_key": comments_key,
                "mime_type": "application/json; charset=utf-8",
                "size_bytes": len(comments_bytes),
                "content_hash": sha256(comments_bytes).hexdigest(),
                "metadata": {
                    "source_path": str(source_path),
                    "platform": source.platform,
                    "source_url": source.url,
                    "comment_count": len(source.comments),
                },
            }
        )

    ingestion_result = await ingestion.ingest(
        IngestionRequest(
            domain=source.domain,
            source_type=source.source_type,
            title=source.title,
            url=source.url,
            raw_text=source.raw_text,
            metadata=source.metadata,
            assets=assets,
        )
    )
    return MediaCrawlerImportResult(
        document_ids=[ingestion_result.document_id],
        chunk_count=ingestion_result.chunk_count,
        asset_count=ingestion_result.asset_count,
        content_count=1,
        comment_count=len(source.comments),
        domain=source.domain,
    )


def _expand_paths(paths: list[Path]) -> list[Path]:
    expanded: list[Path] = []
    for path in paths:
        if path.is_dir():
            expanded.extend(
                sorted(
                    child
                    for child in path.rglob("*")
                    if child.suffix.lower() in {".json", ".jsonl", ".csv"}
                )
            )
        elif path.suffix.lower() in {".json", ".jsonl", ".csv"}:
            expanded.append(path)
    return expanded


def _read_export_items(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [dict(item) for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("items", "contents", "data", "records"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [dict(item) for item in value if isinstance(item, dict)]
            return [payload]
        return []
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            return [dict(row) for row in csv.DictReader(fh)]
    return []


def _platform_from_path(path: Path) -> str | None:
    lowered = path.as_posix().lower()
    for candidate in ("bilibili", "bili", "xhs", "zhihu"):
        if candidate in lowered:
            return normalize_platform(candidate)
    return None


def _safe_media_key(source: NormalizedMediaSource) -> str:
    media_id = source.metadata.get("media_id") or sha256(source.url.encode("utf-8")).hexdigest()[:12]
    safe_id = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(media_id))
    return safe_id or sha256(source.url.encode("utf-8")).hexdigest()[:12]
