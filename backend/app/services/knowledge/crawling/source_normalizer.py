# Status: real

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from app.services.knowledge.crawling.scrapling_client import ScrapedPage


@dataclass(slots=True)
class SourceMetadata:
    platform: str
    source_url: str
    author: str
    fetched_at: datetime
    published_at: str | None = None
    license: str = "unknown"
    rights_note: str = "教学演示用途；保留原始来源，不批量转载。"
    asset_type: str = "web_article"
    reliability: float = 0.75
    extra: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        metadata = {
            "platform": self.platform,
            "source_url": self.source_url,
            "author": self.author,
            "published_at": self.published_at,
            "fetched_at": self.fetched_at.isoformat(),
            "license": self.license,
            "rights_note": self.rights_note,
            "asset_type": self.asset_type,
            "reliability": self.reliability,
            "trust_score": self.reliability,
        }
        metadata.update(self.extra or {})
        return metadata


@dataclass(slots=True)
class NormalizedSource:
    domain: str
    source_type: str
    title: str
    url: str
    raw_text: str
    html_text: str
    metadata: dict[str, Any]


def normalize_web_source(
    page: ScrapedPage,
    *,
    domain: str = "course_websec",
    source_type: str = "scrapling_public",
    platform: str | None = None,
    title: str | None = None,
    author: str | None = None,
    published_at: str | None = None,
    license: str = "unknown",
    rights_note: str | None = None,
    asset_type: str = "web_article",
    reliability: float = 0.75,
    css_selector: str | None = None,
    xpath: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> NormalizedSource:
    final_url = page.final_url or page.url
    normalized_platform = platform or _platform_from_url(final_url)
    raw_text = page.extract_text(css_selector=css_selector, xpath=xpath)
    normalized_title = title or page.title or _title_from_url(final_url)
    if not raw_text:
        raise ValueError(f"source produced no readable text: {final_url}")

    metadata = SourceMetadata(
        platform=normalized_platform,
        source_url=final_url,
        author=author or _default_author(normalized_platform),
        published_at=published_at,
        fetched_at=page.fetched_at,
        license=license,
        rights_note=rights_note or "公开网页资料；仅用于课程知识库演示，保留链接与来源。",
        asset_type=asset_type,
        reliability=reliability,
        extra=extra_metadata,
    ).to_dict()
    metadata["status_code"] = page.status_code
    return NormalizedSource(
        domain=domain,
        source_type=source_type,
        title=normalized_title,
        url=final_url,
        raw_text=raw_text,
        html_text=page.html_text,
        metadata=metadata,
    )


def _platform_from_url(url: str) -> str:
    host = urlparse(url).hostname or "web"
    if "owasp.org" in host:
        return "owasp"
    if "portswigger.net" in host:
        return "portswigger"
    if "github.com" in host or "githubusercontent.com" in host:
        return "github"
    return host.removeprefix("www.").split(".")[0] or "web"


def _default_author(platform: str) -> str:
    return {
        "github": "GitHub repository maintainers",
        "owasp": "OWASP",
        "portswigger": "PortSwigger Web Security Academy",
    }.get(platform, "Public web source")


def _title_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    if not path:
        return urlparse(url).hostname or "Untitled web source"
    return path.rsplit("/", 1)[-1].replace("-", " ").replace("_", " ").strip() or path
