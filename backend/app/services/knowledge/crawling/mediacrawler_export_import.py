# Status: real

from __future__ import annotations

import csv
from dataclasses import dataclass
from hashlib import sha256
import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit
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

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MediaCrawlerImportResult:
    document_ids: list[UUID]
    chunk_count: int
    asset_count: int
    content_count: int
    comment_count: int
    skipped_count: int = 0
    domain: str = "course_websec"


async def import_mediacrawler_exports(
    paths: list[Path],
    *,
    session: AsyncSession,
    platform: str | None = None,
    domain: str = "course_websec",
    storage_prefix: str = "course_websec/mediacrawler",
    rights_note: str | None = None,
    storage_local_root: Path | None = None,
) -> MediaCrawlerImportResult:
    contents: list[tuple[dict[str, Any], Path]] = []
    comments: list[tuple[dict[str, Any], Path]] = []
    skipped_count = 0
    for path in _expand_paths(paths):
        items, skipped = _read_export_items(path)
        skipped_count += skipped
        for item in items:
            item_type = infer_item_type(item, file_hint=path.name)
            if item_type == "comments":
                comments.append((item, path))
            elif item_type == "contents":
                contents.append((item, path))

    grouped_comments: dict[str, list[dict[str, Any]]] = {}
    for comment, _path in comments:
        key = media_parent_key(comment, platform=platform)
        if key is not None:
            grouped_comments.setdefault(key, []).append(_sanitize_comment(comment))

    storage = StorageService(session, local_root=storage_local_root)
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
        skipped_count=skipped_count,
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
    stored_item = _redact_sensitive_media_fields(source.raw_item)
    item_bytes = json.dumps(stored_item, ensure_ascii=False, indent=2).encode("utf-8")
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
        sanitized_comments = [_sanitize_comment(comment) for comment in source.comments]
        comments_bytes = json.dumps(sanitized_comments, ensure_ascii=False, indent=2).encode("utf-8")
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
                    "comment_count": len(sanitized_comments),
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


def _read_export_items(path: Path) -> tuple[list[dict[str, Any]], int]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        items: list[dict[str, Any]] = []
        skipped = 0
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                skipped += 1
                logger.warning("skipped line %s in %s: parse error: %s", line_no, path, exc)
                print(f"warning: skipped line {line_no}: parse error: {exc}")
                continue
            if isinstance(payload, dict):
                items.append(payload)
            else:
                skipped += 1
                logger.warning("skipped line %s in %s: expected object", line_no, path)
        return items, skipped
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [dict(item) for item in payload if isinstance(item, dict)], 0
        if isinstance(payload, dict):
            for key in ("items", "contents", "data", "records"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [dict(item) for item in value if isinstance(item, dict)], 0
            return [payload], 0
        return [], 0
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            return [dict(row) for row in csv.DictReader(fh)], 0
    return [], 0


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


def _redact_sensitive_media_fields(item: dict[str, Any]) -> dict[str, Any]:
    redacted = _redact_value(item)
    if not isinstance(redacted, dict):
        return {}
    return redacted


def _sanitize_comment(comment: dict[str, Any]) -> dict[str, Any]:
    content = _first_present(comment, "content", "comment_content", "text", "message")
    nickname = _first_present(comment, "nickname", "user_nickname", "user_name", "author")
    created_time = _first_present(comment, "created_time", "create_time", "time", "pubdate")
    like_count = _first_present(comment, "like_count", "liked_count")

    sanitized: dict[str, Any] = {"content": str(content).strip() if content is not None else ""}
    if nickname is not None and str(nickname).strip():
        sanitized["nickname"] = str(nickname).strip()
    if created_time is not None and created_time != "":
        sanitized["created_time"] = created_time
    if like_count is not None and like_count != "":
        sanitized["like_count"] = like_count
    return sanitized


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, child in value.items():
            if _is_sensitive_key(str(key)):
                continue
            redacted[str(key)] = _redact_value(child)
        return redacted
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, str) and _looks_like_url_with_query(value):
        return _strip_url_query(value)
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().strip()
    compact = normalized.replace("-", "_")
    flat = compact.replace("_", "")
    exact_sensitive = {
        "avatar",
        "avatar_url",
        "bili_jct",
        "cookie",
        "cookies",
        "csrf",
        "csrf_token",
        "credential",
        "credentials",
        "face",
        "head_url",
        "homepage",
        "home_page",
        "home_url",
        "ip",
        "ip_location",
        "last_ip",
        "mid",
        "refresh_token",
        "sec_uid",
        "sessdata",
        "session",
        "session_id",
        "sid",
        "sign",
        "signature",
        "token",
        "uid",
        "user_home",
        "user_homepage",
        "user_id",
        "user_link",
        "user_url_token",
        "xsec_token",
    }
    sensitive_fragments = (
        "avatar",
        "cookie",
        "credential",
        "csrf",
        "home_url",
        "homepage",
        "ip_location",
        "session",
        "signature",
        "sign",
        "token",
        "user_id",
        "userid",
        "xsec",
    )
    return compact in exact_sensitive or flat in exact_sensitive or any(
        fragment in compact or fragment in flat for fragment in sensitive_fragments
    )


def _first_present(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = item.get(key)
        if value is not None and value != "":
            return value
    return None


def _looks_like_url_with_query(value: str) -> bool:
    parts = urlsplit(value)
    return bool(parts.scheme and parts.netloc and parts.query)


def _strip_url_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
