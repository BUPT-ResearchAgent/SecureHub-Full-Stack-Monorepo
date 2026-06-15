# Status: real

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from typing import Any


SUPPORTED_MEDIACRAWLER_PLATFORMS = frozenset({"bili", "bilibili", "xhs", "zhihu"})


@dataclass(slots=True)
class NormalizedMediaSource:
    domain: str
    source_type: str
    platform: str
    title: str
    url: str
    raw_text: str
    raw_item: dict[str, Any]
    metadata: dict[str, Any]
    comments: list[dict[str, Any]]


def normalize_mediacrawler_content(
    item: dict[str, Any],
    *,
    platform: str | None = None,
    domain: str = "course_websec",
    comments: list[dict[str, Any]] | None = None,
    fetched_at: datetime | None = None,
    rights_note: str | None = None,
) -> NormalizedMediaSource:
    normalized_platform = normalize_platform(platform or infer_platform(item))
    if normalized_platform == "xhs":
        return _normalize_xhs(item, domain, comments or [], fetched_at, rights_note)
    if normalized_platform == "bili":
        return _normalize_bili(item, domain, comments or [], fetched_at, rights_note)
    if normalized_platform == "zhihu":
        return _normalize_zhihu(item, domain, comments or [], fetched_at, rights_note)
    raise ValueError(f"unsupported MediaCrawler platform: {platform}")


def normalize_platform(platform: str) -> str:
    lowered = platform.lower().strip()
    if lowered in {"bili", "bilibili", "b站", "哔哩哔哩"}:
        return "bili"
    if lowered in {"xhs", "xiaohongshu", "小红书"}:
        return "xhs"
    if lowered in {"zhihu", "知乎"}:
        return "zhihu"
    raise ValueError(f"unsupported MediaCrawler platform: {platform}")


def infer_platform(item: dict[str, Any]) -> str:
    keys = set(item)
    if {"note_id", "note_url"} & keys or {"collected_count", "xsec_token"} & keys:
        return "xhs"
    if {"video_id", "video_url", "video_cover_url"} & keys:
        return "bili"
    if {"content_id", "content_url", "question_id"} & keys:
        return "zhihu"
    raise ValueError("cannot infer MediaCrawler platform from item fields")


def infer_item_type(item: dict[str, Any], *, file_hint: str = "") -> str:
    lowered = file_hint.lower()
    if "comment" in lowered or "comments" in lowered:
        return "comments"
    if "creator" in lowered or "creators" in lowered:
        return "creators"
    if "content" in lowered or "contents" in lowered or "video" in lowered or "note" in lowered:
        return "contents"
    if "comment_id" in item or "parent_comment_id" in item:
        return "comments"
    if "content_id" in item or "note_id" in item or "video_id" in item:
        return "contents"
    return "contents"


def media_parent_key(item: dict[str, Any], *, platform: str | None = None) -> str | None:
    try:
        normalized_platform = normalize_platform(platform or infer_platform(item))
    except ValueError:
        normalized_platform = platform or ""
    if normalized_platform == "xhs":
        return _string_or_none(item.get("note_id"))
    if normalized_platform == "bili":
        return _string_or_none(item.get("video_id"))
    if normalized_platform == "zhihu":
        return _string_or_none(item.get("content_id"))
    return (
        _string_or_none(item.get("note_id"))
        or _string_or_none(item.get("video_id"))
        or _string_or_none(item.get("content_id"))
    )


def _normalize_xhs(
    item: dict[str, Any],
    domain: str,
    comments: list[dict[str, Any]],
    fetched_at: datetime | None,
    rights_note: str | None,
) -> NormalizedMediaSource:
    title = _string_or_none(item.get("title")) or "小红书学习笔记"
    desc = _string_or_none(item.get("desc")) or ""
    url = _string_or_none(item.get("note_url")) or f"https://www.xiaohongshu.com/explore/{item.get('note_id')}"
    author = _string_or_none(item.get("nickname")) or "小红书公开作者"
    published_at = _timestamp_to_iso(item.get("time"))
    metadata = _base_metadata(
        platform="xhs",
        url=url,
        author=author,
        published_at=published_at,
        fetched_at=fetched_at,
        rights_note=rights_note,
        extra={
            "media_id": _string_or_none(item.get("note_id")),
            "media_type": _string_or_none(item.get("type")) or "note",
            "source_keyword": item.get("source_keyword"),
            "tags": _jsonish(item.get("tag_list")),
            "metrics": {
                "liked_count": item.get("liked_count"),
                "collected_count": item.get("collected_count"),
                "comment_count": item.get("comment_count"),
                "share_count": item.get("share_count"),
            },
            "cover_or_images": _jsonish(item.get("image_list")),
        },
    )
    return NormalizedMediaSource(
        domain=domain,
        source_type="mediacrawler_export",
        platform="xhs",
        title=title,
        url=url,
        raw_text=_build_text(title, author, desc, comments, metadata),
        raw_item=item,
        metadata=metadata,
        comments=comments,
    )


def _normalize_bili(
    item: dict[str, Any],
    domain: str,
    comments: list[dict[str, Any]],
    fetched_at: datetime | None,
    rights_note: str | None,
) -> NormalizedMediaSource:
    title = _string_or_none(item.get("title")) or "B站教学视频"
    desc = _string_or_none(item.get("desc")) or ""
    url = _string_or_none(item.get("video_url")) or f"https://www.bilibili.com/video/{item.get('video_id')}"
    author = _string_or_none(item.get("nickname")) or "B站公开作者"
    published_at = _timestamp_to_iso(item.get("create_time"))
    metadata = _base_metadata(
        platform="bili",
        url=url,
        author=author,
        published_at=published_at,
        fetched_at=fetched_at,
        rights_note=rights_note,
        extra={
            "media_id": _string_or_none(item.get("video_id")),
            "media_type": _string_or_none(item.get("video_type")) or "video",
            "source_keyword": item.get("source_keyword"),
            "cover_url": item.get("video_cover_url"),
            "metrics": {
                "liked_count": item.get("liked_count"),
                "play_count": item.get("video_play_count"),
                "favorite_count": item.get("video_favorite_count"),
                "share_count": item.get("video_share_count"),
                "coin_count": item.get("video_coin_count"),
                "danmaku_count": item.get("video_danmaku"),
                "comment_count": item.get("video_comment"),
            },
        },
    )
    return NormalizedMediaSource(
        domain=domain,
        source_type="mediacrawler_export",
        platform="bili",
        title=title,
        url=url,
        raw_text=_build_text(title, author, desc, comments, metadata),
        raw_item=item,
        metadata=metadata,
        comments=comments,
    )


def _normalize_zhihu(
    item: dict[str, Any],
    domain: str,
    comments: list[dict[str, Any]],
    fetched_at: datetime | None,
    rights_note: str | None,
) -> NormalizedMediaSource:
    title = _string_or_none(item.get("title")) or "知乎学习资料"
    text = _string_or_none(item.get("content_text")) or _string_or_none(item.get("desc")) or ""
    url = _string_or_none(item.get("content_url")) or f"https://www.zhihu.com/question/{item.get('question_id')}"
    author = _string_or_none(item.get("user_nickname")) or "知乎公开作者"
    published_at = _timestamp_to_iso(item.get("created_time"))
    metadata = _base_metadata(
        platform="zhihu",
        url=url,
        author=author,
        published_at=published_at,
        fetched_at=fetched_at,
        rights_note=rights_note,
        extra={
            "media_id": _string_or_none(item.get("content_id")),
            "media_type": _string_or_none(item.get("content_type")) or "content",
            "question_id": item.get("question_id"),
            "source_keyword": item.get("source_keyword"),
            "metrics": {
                "voteup_count": item.get("voteup_count"),
                "comment_count": item.get("comment_count"),
            },
        },
    )
    return NormalizedMediaSource(
        domain=domain,
        source_type="mediacrawler_export",
        platform="zhihu",
        title=title,
        url=url,
        raw_text=_build_text(title, author, text, comments, metadata),
        raw_item=item,
        metadata=metadata,
        comments=comments,
    )


def _base_metadata(
    *,
    platform: str,
    url: str,
    author: str,
    published_at: str | None,
    fetched_at: datetime | None,
    rights_note: str | None,
    extra: dict[str, Any],
) -> dict[str, Any]:
    fetched = fetched_at or datetime.now(UTC)
    metadata = {
        "platform": platform,
        "source_url": url,
        "author": author,
        "published_at": published_at,
        "fetched_at": fetched.isoformat(),
        "license": "platform terms / non-commercial learning reference",
        "rights_note": rights_note
        or "MediaCrawler 离线导出样本；仅用于学习与比赛演示，保留平台链接与作者信息，不批量转载。",
        "asset_type": "media_item_json",
        "reliability": 0.65,
        "trust_score": 0.65,
        "collection_mode": "mediacrawler_export",
    }
    metadata.update({key: value for key, value in extra.items() if value is not None})
    return metadata


def _build_text(
    title: str,
    author: str,
    body: str,
    comments: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> str:
    parts = [
        f"# {title}",
        "",
        f"- 平台：{metadata['platform']}",
        f"- 作者：{author}",
        f"- 来源：{metadata['source_url']}",
    ]
    if metadata.get("published_at"):
        parts.append(f"- 发布时间：{metadata['published_at']}")
    if metadata.get("source_keyword"):
        parts.append(f"- 来源关键词：{metadata['source_keyword']}")
    if metadata.get("metrics"):
        parts.append(f"- 互动指标：{json.dumps(metadata['metrics'], ensure_ascii=False)}")
    parts.extend(["", "## 正文", "", body.strip() or "（原始导出未提供正文，仅保留来源与元数据。）"])
    if comments:
        parts.extend(["", "## 采样评论", ""])
        for comment in comments[:10]:
            content = _string_or_none(comment.get("content")) or ""
            nickname = _string_or_none(
                comment.get("nickname") or comment.get("user_nickname")
            ) or "匿名用户"
            if content:
                parts.append(f"- {nickname}: {content}")
    return "\n".join(parts)


def _timestamp_to_iso(value: object) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, str) and not value.isdigit():
        return value
    try:
        timestamp = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return str(value)
    if timestamp > 10_000_000_000:
        timestamp = int(timestamp / 1000)
    return datetime.fromtimestamp(timestamp, tz=UTC).isoformat()


def _jsonish(value: object) -> object:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("[", "{")):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                return value
    return value


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
