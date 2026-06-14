# Status: real

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser


class CrawlPolicyError(ValueError):
    """Raised when a crawl request violates SecureHub collection boundaries."""


@dataclass(slots=True)
class CrawlRequest:
    url: str
    mode: str = "static"
    options: dict[str, object] = field(default_factory=dict)
    user_agent: str = "SecureHubBot/0.1 (+https://securehub.local/demo)"


@dataclass(slots=True)
class CrawlPolicy:
    """Compliance guard for public, small-scale teaching-data collection.

    This policy intentionally exposes only the safe subset needed by P1:
    public HTTP(S) pages, optional robots checks, demo-scale batch limits, and
    no anti-bot bypass / proxy rotation / login automation knobs.
    """

    allowed_schemes: frozenset[str] = frozenset({"http", "https"})
    allowed_modes: frozenset[str] = frozenset({"static", "dynamic"})
    allowed_domains: frozenset[str] | None = None
    blocked_domains: frozenset[str] = frozenset()
    max_pages_per_run: int = 20
    download_delay_seconds: float = 1.0
    obey_robots_txt: bool = True
    allowed_option_keys: frozenset[str] = frozenset(
        {
            "headers",
            "timeout",
            "wait_until",
            "network_idle",
            "css_selector",
            "xpath",
            "development_cache",
            "impersonate",
            "user_agent",
        }
    )
    banned_option_keys: frozenset[str] = frozenset(
        {
            "anti_bot",
            "bypass",
            "captcha",
            "cookies",
            "login",
            "password",
            "proxy",
            "proxies",
            "proxy_rotation",
            "session_cookie",
            "solve_cloudflare",
            "stealth",
            "stealthy",
            "token",
            "turnstile",
        }
    )

    def validate_batch_size(self, count: int) -> None:
        if count < 0:
            raise CrawlPolicyError("crawl batch size must be non-negative")
        if count > self.max_pages_per_run:
            raise CrawlPolicyError(
                f"crawl batch exceeds demo limit: {count} > {self.max_pages_per_run}"
            )

    def validate_request(self, request: CrawlRequest) -> None:
        parsed = urlparse(request.url)
        if parsed.scheme not in self.allowed_schemes:
            raise CrawlPolicyError(f"unsupported URL scheme: {parsed.scheme or '<empty>'}")
        if not parsed.netloc:
            raise CrawlPolicyError("URL must include a public host")
        host = parsed.hostname or ""
        if self.allowed_domains is not None and host not in self.allowed_domains:
            raise CrawlPolicyError(f"host is outside the allowlist: {host}")
        if host in self.blocked_domains:
            raise CrawlPolicyError(f"host is blocked by crawl policy: {host}")
        if request.mode not in self.allowed_modes:
            raise CrawlPolicyError(f"unsupported crawl mode: {request.mode}")
        self.validate_options(request.options)

    def validate_options(self, options: dict[str, object]) -> None:
        for raw_key in options:
            key = raw_key.lower()
            if key in self.banned_option_keys:
                raise CrawlPolicyError(f"crawl option is banned: {raw_key}")
            if key not in self.allowed_option_keys:
                raise CrawlPolicyError(f"crawl option is not allowlisted: {raw_key}")
            value = options[raw_key]
            if isinstance(value, str) and _looks_like_bypass(value):
                raise CrawlPolicyError(f"crawl option value looks like bypass logic: {raw_key}")

    def ensure_robots_allowed(
        self,
        url: str,
        *,
        robots_txt: str | None = None,
        user_agent: str = "SecureHubBot",
    ) -> None:
        if not self.obey_robots_txt or robots_txt is None:
            return
        parser = RobotFileParser()
        parser.parse(robots_txt.splitlines())
        if not parser.can_fetch(user_agent, url):
            raise CrawlPolicyError(f"robots.txt disallows fetching: {url}")


def _looks_like_bypass(value: str) -> bool:
    lowered = value.lower()
    return any(
        marker in lowered
        for marker in (
            "cloudflare",
            "captcha",
            "turnstile",
            "proxy://",
            "socks5://",
            "login",
        )
    )
