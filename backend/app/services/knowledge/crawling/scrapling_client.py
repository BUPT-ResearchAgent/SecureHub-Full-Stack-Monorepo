# Status: real

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib import import_module
import re
from typing import Any

import httpx
from lxml import html

from app.services.knowledge.crawling.crawler_policy import (
    CrawlPolicy,
    CrawlRequest,
)


@dataclass(slots=True)
class ScraplingFetchOptions:
    mode: str = "static"
    timeout_seconds: float = 20.0
    headers: dict[str, str] = field(default_factory=dict)
    network_idle: bool = True
    development_cache: bool = False

    def to_policy_options(self) -> dict[str, object]:
        return {
            "headers": self.headers,
            "timeout": self.timeout_seconds,
            "network_idle": self.network_idle,
            "development_cache": self.development_cache,
        }


@dataclass(slots=True)
class ScrapedPage:
    url: str
    html_text: str
    status_code: int = 200
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    final_url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_html(
        cls,
        html_text: str,
        *,
        url: str,
        status_code: int = 200,
        final_url: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> "ScrapedPage":
        return cls(
            url=url,
            final_url=final_url or url,
            html_text=html_text,
            status_code=status_code,
            headers=headers or {},
        )

    @property
    def title(self) -> str | None:
        doc = html.fromstring(self.html_text)
        titles = [text.strip() for text in doc.xpath("//title/text()") if text.strip()]
        return titles[0] if titles else None

    def extract_text(self, *, css_selector: str | None = None, xpath: str | None = None) -> str:
        doc = html.fromstring(self.html_text)
        _strip_noise_nodes(doc)
        nodes: list[Any]
        if xpath:
            selected = doc.xpath(xpath)
            nodes = selected if isinstance(selected, list) else [selected]
            if not _nodes_have_text(nodes):
                nodes = _default_content_nodes(doc)
        elif css_selector:
            nodes = _select_css(doc, css_selector)
        else:
            nodes = _default_content_nodes(doc)

        parts: list[str] = []
        for node in nodes:
            if isinstance(node, str):
                parts.append(node)
            elif hasattr(node, "text_content"):
                parts.append(node.text_content())
        return _clean_text("\n".join(parts))


class ScraplingClient:
    """Safe wrapper around Scrapling's public-page fetchers.

    Scrapling is optional in the local test environment. If it is not installed,
    the client degrades to ``httpx`` for ordinary public HTTP(S) pages. The
    wrapper never imports or enables StealthyFetcher, proxy rotation, or
    Cloudflare-solving options.
    """

    def __init__(
        self,
        *,
        policy: CrawlPolicy | None = None,
        user_agent: str = "SecureHubBot/0.1 (+https://securehub.local/demo)",
    ) -> None:
        self.policy = policy or CrawlPolicy()
        self.user_agent = user_agent

    async def fetch(
        self,
        url: str,
        *,
        options: ScraplingFetchOptions | None = None,
    ) -> ScrapedPage:
        fetch_options = options or ScraplingFetchOptions()
        request = CrawlRequest(
            url=url,
            mode=fetch_options.mode,
            options=fetch_options.to_policy_options(),
            user_agent=self.user_agent,
        )
        self.policy.validate_request(request)
        if fetch_options.mode == "static":
            return await self._fetch_static(url, fetch_options)
        return await self._fetch_dynamic(url, fetch_options)

    async def _fetch_static(self, url: str, options: ScraplingFetchOptions) -> ScrapedPage:
        fetcher = _load_scrapling_fetcher("Fetcher")
        if fetcher is not None:
            page = await _run_sync_fetcher(fetcher, url, options)
            if page is not None:
                return page

        headers = {"User-Agent": self.user_agent, **options.headers}
        async with httpx.AsyncClient(
            timeout=options.timeout_seconds,
            headers=headers,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return ScrapedPage.from_html(
                response.text,
                url=url,
                status_code=response.status_code,
                final_url=str(response.url),
                headers=dict(response.headers),
            )

    async def _fetch_dynamic(self, url: str, options: ScraplingFetchOptions) -> ScrapedPage:
        fetcher = _load_scrapling_fetcher("DynamicFetcher")
        if fetcher is None:
            return await self._fetch_static(url, options)
        page = await _run_sync_fetcher(fetcher, url, options)
        if page is None:
            return await self._fetch_static(url, options)
        return page


def _load_scrapling_fetcher(name: str) -> object | None:
    try:
        module = import_module("scrapling.fetchers")
    except ImportError:
        return None
    return getattr(module, name, None)


async def _run_sync_fetcher(
    fetcher: object,
    url: str,
    options: ScraplingFetchOptions,
) -> ScrapedPage | None:
    import anyio

    def _call() -> ScrapedPage | None:
        kwargs: dict[str, object] = {
            "timeout": options.timeout_seconds,
            "network_idle": options.network_idle,
        }
        try:
            try:
                raw_page = getattr(fetcher, "get")(url, **kwargs)
            except AttributeError:
                raw_page = getattr(fetcher, "fetch")(url, **kwargs)
        except TypeError:
            try:
                raw_page = getattr(fetcher, "get")(url)
            except AttributeError:
                raw_page = getattr(fetcher, "fetch")(url)
        html_text = _coerce_html(raw_page)
        if not html_text:
            return None
        return ScrapedPage.from_html(html_text, url=url)

    return await anyio.to_thread.run_sync(_call)


def _coerce_html(raw_page: object) -> str | None:
    for attr in ("html", "html_content", "body", "content", "text"):
        value = getattr(raw_page, attr, None)
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        if isinstance(value, str):
            return value
        if callable(value):
            try:
                result = value()
            except TypeError:
                continue
            if isinstance(result, bytes):
                return result.decode("utf-8", errors="replace")
            if isinstance(result, str):
                return result
    return str(raw_page) if raw_page is not None else None


def _clean_text(text: str) -> str:
    lines = [" ".join(line.split()) for line in text.splitlines()]
    cleaned: list[str] = []
    for line in lines:
        if not line or _looks_like_page_chrome(line):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def _select_css(doc: Any, selector: str) -> list[Any]:
    selector = selector.strip()
    if not selector:
        return [doc]
    if selector.startswith("#"):
        node_id = selector[1:]
        return doc.xpath(f"//*[@id={node_id!r}]")
    if selector.startswith("."):
        class_name = selector[1:]
        return doc.xpath(
            "//*[contains(concat(' ', normalize-space(@class), ' '), "
            f"concat(' ', {class_name!r}, ' '))]"
        )
    if selector.isidentifier():
        return doc.xpath(f"//{selector}")
    raise ValueError(
        "css_selector only supports simple tag, #id, or .class selectors "
        "without the optional cssselect dependency"
    )


def _strip_noise_nodes(doc: Any) -> None:
    noisy_xpath = (
        "//script|//style|//noscript|//template|//svg|//canvas|//iframe|"
        "//nav|//header|//footer|//aside|//form|"
        "//*[contains(concat(' ', normalize-space(@class), ' '), ' nav ')]|"
        "//*[contains(concat(' ', normalize-space(@class), ' '), ' navbar ')]|"
        "//*[contains(concat(' ', normalize-space(@class), ' '), ' menu ')]|"
        "//*[contains(concat(' ', normalize-space(@class), ' '), ' sidebar ')]|"
        "//*[contains(concat(' ', normalize-space(@class), ' '), ' cookie ')]|"
        "//*[contains(concat(' ', normalize-space(@class), ' '), ' banner ')]|"
        "//*[contains(concat(' ', normalize-space(@id), ' '), ' banner ')]|"
        "//*[contains(concat(' ', normalize-space(@id), ' '), ' cookie ')]"
    )
    for node in doc.xpath(noisy_xpath):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)


def _default_content_nodes(doc: Any) -> list[Any]:
    candidates = doc.xpath(
        "//main|//article|"
        "//*[@id='main']|//*[@id='content']|//*[@id='main-content']|"
        "//*[contains(concat(' ', normalize-space(@class), ' '), ' main ')]|"
        "//*[contains(concat(' ', normalize-space(@class), ' '), ' content ')]|"
        "//*[contains(concat(' ', normalize-space(@class), ' '), ' page-content ')]|"
        "//*[contains(concat(' ', normalize-space(@class), ' '), ' post-content ')]|"
        "//*[contains(concat(' ', normalize-space(@class), ' '), ' markdown-body ')]"
    )
    if not candidates:
        body = doc.xpath("//body")
        return body[:1] if body else [doc]
    ranked = sorted(
        candidates,
        key=lambda node: len(_clean_text(node.text_content())) if hasattr(node, "text_content") else 0,
        reverse=True,
    )
    return ranked[:1]


def _nodes_have_text(nodes: list[Any]) -> bool:
    for node in nodes:
        if isinstance(node, str) and node.strip():
            return True
        if hasattr(node, "text_content") and len(_clean_text(node.text_content())) >= 80:
            return True
    return False


def _looks_like_page_chrome(line: str) -> bool:
    lowered = line.lower()
    if len(line) <= 2:
        return True
    if re.search(r"[$][.(]|function\s*\(|var\s+\w+|=>|</?[a-z]+|[{};]{2,}", line):
        return True
    return any(
        marker in lowered
        for marker in (
            "enable javascript",
            "this website uses cookies",
            "accept cookies",
            "store donate join",
            "mobile primary navigation",
            "aria-label",
            "search button",
            "toggleclass",
            "accordion",
            "sitemap",
        )
    )
