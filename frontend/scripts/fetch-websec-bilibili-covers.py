#!/usr/bin/env python3
"""Fetch WEBSEC-101 Bilibili public-page cover images and titles.

This is an intentionally small, one-shot asset refresh tool.  It requests only
the public video HTML and the cover image declared in that HTML.  It never sends
cookies, does not log in, and does not fetch video, audio, comments, danmaku, or
user data.  Existing successfully downloaded files are replaced atomically only
after a new image has been fully downloaded and validated.

Usage (from frontend/):
    python scripts/fetch-websec-bilibili-covers.py
    python scripts/fetch-websec-bilibili-covers.py --titles
"""

from __future__ import annotations

import argparse
import html
import gzip
import os
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
PAGE_TIMEOUT_SECONDS = 15
IMAGE_TIMEOUT_SECONDS = 20
MAX_PAGE_BYTES = 2 * 1024 * 1024
MAX_IMAGE_BYTES = 10 * 1024 * 1024
OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "public" / "assets" / "websec" / "bilibili"

# Do not extend this list without an explicit course-content decision.  Keeping it
# fixed makes the script repeatable and prevents it from becoming a bulk crawler.
TARGET_BVIDS = (
    "BV1PyARzDEHA",
    "BV1Zw4m1y7BX",
    "BV1FVMJ6yELZ",
    "BV1HJ4m1w7fB",
    "BV1HVMH6pE5h",
    "BV17jN96fEhG",
)

IMAGE_SUFFIXES = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "GIF": ".gif",
    "WEBP": ".webp",
    "AVIF": ".avif",
}


class PublicVideoPageParser(HTMLParser):
    """Extract public-page cover and title candidates without executing page scripts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.og_images: list[str] = []
        self.itemprop_images: list[str] = []
        self.og_titles: list[str] = []
        self.itemprop_names: list[str] = []
        self.document_title_parts: list[str] = []
        self._inside_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.casefold(): (value or "") for name, value in attrs}
        tag_name = tag.casefold()

        if tag_name == "title":
            self._inside_title = True
            return

        if tag_name == "meta":
            content = values.get("content", "")
            if values.get("property", "").casefold() == "og:title" and content:
                self.og_titles.append(content)
            if values.get("itemprop", "").casefold() in {"name", "headline"} and content:
                self.itemprop_names.append(content)

        value = values.get("content") or values.get("href") or values.get("src")
        if not value:
            return

        if tag_name == "meta" and values.get("property", "").casefold() == "og:image":
            self.og_images.append(value)
            return

        if values.get("itemprop", "").casefold() == "image":
            self.itemprop_images.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "title":
            self._inside_title = False

    def handle_data(self, data: str) -> None:
        if self._inside_title:
            self.document_title_parts.append(data)


@dataclass(frozen=True)
class FetchResult:
    status: int
    content_type: str
    body: bytes


def read_bounded(response: object, max_bytes: int) -> bytes:
    """Read a response in chunks while refusing unexpectedly large payloads."""

    reader = response  # Keeps urllib's Response type out of this stdlib-only script's public surface.
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = reader.read(64 * 1024)  # type: ignore[attr-defined]
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ValueError(f"响应超过 {max_bytes // (1024 * 1024)} MiB 限制")
        chunks.append(chunk)
    return b"".join(chunks)


def fetch(url: str, *, referer: str, accept: str, timeout: int, max_bytes: int) -> FetchResult:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": referer,
            "Accept": accept,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
            # urllib does not transparently decode compressed responses.  Request
            # only gzip, which is available in the Python standard library.
            "Accept-Encoding": "gzip",
            "Cache-Control": "no-cache",
        },
    )
    with urlopen(request, timeout=timeout) as response:  # nosec B310: fixed HTTPS sources, no user input
        status = int(response.getcode())
        content_type = response.headers.get_content_type()
        body = read_bounded(response, max_bytes)
        if response.headers.get("Content-Encoding", "").casefold() == "gzip":
            body = gzip.decompress(body)
            if len(body) > max_bytes:
                raise ValueError(f"解压后的响应超过 {max_bytes // (1024 * 1024)} MiB 限制")
        return FetchResult(status=status, content_type=content_type, body=body)


def normalize_cover_url(raw_url: str) -> str | None:
    """Normalize Bilibili's protocol-relative image URL and strip transform suffixes."""

    value = html.unescape(raw_url).strip()
    if not value:
        return None
    if value.startswith("//"):
        value = f"https:{value}"

    try:
        parts = urlsplit(value)
    except ValueError:
        return None

    host = (parts.hostname or "").casefold()
    if parts.scheme not in {"http", "https"} or not host.endswith((".hdslb.com", ".biliimg.com")):
        return None

    # Bilibili often appends `@320w_200h...` to the image path.  The original
    # file is before the suffix, so retaining query/fragment information is neither
    # needed nor desirable for a local static asset.
    path = parts.path.split("@", 1)[0]
    if not path:
        return None
    return urlunsplit(("https", parts.netloc, path, "", ""))


def parse_public_video_page(page_body: bytes) -> PublicVideoPageParser:
    parser = PublicVideoPageParser()
    parser.feed(page_body.decode("utf-8", errors="replace"))
    parser.close()
    return parser


def find_cover_url(page_body: bytes) -> str | None:
    parser = parse_public_video_page(page_body)
    for candidate in (*parser.og_images, *parser.itemprop_images):
        normalized = normalize_cover_url(candidate)
        if normalized:
            return normalized
    return None


def normalize_video_title(raw_title: str) -> str | None:
    """Remove markup/entities and Bilibili's document-title suffix only."""

    value = re.sub(r"\s+", " ", html.unescape(raw_title)).strip()
    value = re.sub(
        r"\s*[-_|｜—–]\s*(?:哔哩哔哩|bilibili)(?:_bilibili)?\s*$",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()
    return value or None


def find_video_title(page_body: bytes) -> str | None:
    """Use the public HTML title precedence: og:title, itemprop=name, then <title>."""

    parser = parse_public_video_page(page_body)
    document_title = "".join(parser.document_title_parts)
    for candidate in (*parser.og_titles, *parser.itemprop_names, document_title):
        title = normalize_video_title(candidate)
        if title:
            return title
    return None


def identify_image(body: bytes) -> str | None:
    """Reject accidental HTML/error payloads even if a server labels them as images."""

    if body.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if body.startswith((b"GIF87a", b"GIF89a")):
        return "GIF"
    if body.startswith(b"RIFF") and body[8:12] == b"WEBP":
        return "WEBP"
    if len(body) >= 12 and body[4:8] == b"ftyp" and body[8:12] in {b"avif", b"avis"}:
        return "AVIF"
    return None


def write_atomically(destination: Path, body: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        temporary.write_bytes(body)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)


def remove_stale_variant(bvid: str, current_destination: Path) -> None:
    """Keep one stable local cover per target without touching any other assets."""

    for suffix in IMAGE_SUFFIXES.values():
        candidate = OUTPUT_DIRECTORY / f"{bvid}{suffix}"
        if candidate != current_destination and candidate.exists():
            candidate.unlink()


def fetch_cover(bvid: str) -> tuple[bool, str]:
    page_url = f"https://www.bilibili.com/video/{bvid}/"
    try:
        page = fetch(
            page_url,
            referer="https://www.bilibili.com/",
            accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            timeout=PAGE_TIMEOUT_SECONDS,
            max_bytes=MAX_PAGE_BYTES,
        )
        if page.status != 200:
            return False, f"视频页面返回 HTTP {page.status}"

        cover_url = find_cover_url(page.body)
        if not cover_url:
            return False, "未在公开页面中找到 og:image 或 itemprop=image"

        image = fetch(
            cover_url,
            referer=page_url,
            accept="image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            timeout=IMAGE_TIMEOUT_SECONDS,
            max_bytes=MAX_IMAGE_BYTES,
        )
        if image.status != 200:
            return False, f"封面返回 HTTP {image.status}"
        image_kind = identify_image(image.body)
        if image_kind is None:
            return False, f"封面不是可识别的图片（Content-Type: {image.content_type or '未知'}）"

        destination = OUTPUT_DIRECTORY / f"{bvid}{IMAGE_SUFFIXES[image_kind]}"
        write_atomically(destination, image.body)
        remove_stale_variant(bvid, destination)
        relative_path = destination.relative_to(OUTPUT_DIRECTORY.parents[3]).as_posix()
        return True, f"{relative_path} · {len(image.body):,} B · {image.content_type or image_kind}"
    except HTTPError as error:
        return False, f"HTTP {error.code}（未替换已有本地封面）"
    except URLError as error:
        return False, f"网络错误：{error.reason}（未替换已有本地封面）"
    except TimeoutError:
        return False, "请求超时（未替换已有本地封面）"
    except ValueError as error:
        return False, f"{error}（未替换已有本地封面）"
    except OSError as error:
        return False, f"写入失败：{error}（未替换已有本地封面）"


def fetch_title(bvid: str) -> tuple[bool, str]:
    """Fetch only one public HTML page for a stable course-title refresh."""

    page_url = f"https://www.bilibili.com/video/{bvid}/"
    try:
        page = fetch(
            page_url,
            referer="https://www.bilibili.com/",
            accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            timeout=PAGE_TIMEOUT_SECONDS,
            max_bytes=MAX_PAGE_BYTES,
        )
        if page.status != 200:
            return False, f"视频页面返回 HTTP {page.status}"
        title = find_video_title(page.body)
        if not title:
            return False, "未在公开页面中找到 og:title、itemprop=name 或 <title>"
        return True, title
    except HTTPError as error:
        return False, f"HTTP {error.code}"
    except URLError as error:
        return False, f"网络错误：{error.reason}"
    except TimeoutError:
        return False, "请求超时"
    except ValueError as error:
        return False, str(error)


def main(bvids: Iterable[str] = TARGET_BVIDS, *, titles_only: bool = False) -> int:
    if titles_only:
        print("仅抓取公开视频 HTML 中的标题；不发送 Cookie，也不下载封面、视频、音频、弹幕、评论或用户数据。")
        successful = 0
        failed = 0
        for bvid in bvids:
            ok, detail = fetch_title(bvid)
            if ok:
                successful += 1
                print(f"[标题] {bvid}: {detail}")
            else:
                failed += 1
                print(f"[失败] {bvid}: {detail}", file=sys.stderr)
        print(f"完成：成功 {successful}，失败 {failed}。")
        return 0 if failed == 0 else 1

    print("仅抓取公开页面声明的封面；不发送 Cookie，不下载视频、音频、弹幕、评论或用户数据。")
    successful = 0
    failed = 0
    for bvid in bvids:
        ok, detail = fetch_cover(bvid)
        if ok:
            successful += 1
            print(f"[成功] {bvid}: {detail}")
        else:
            failed += 1
            print(f"[失败] {bvid}: {detail}", file=sys.stderr)

    print(f"完成：成功 {successful}，失败 {failed}。")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser(description="刷新 WEBSEC-101 Bilibili 公开页面元数据。")
    argument_parser.add_argument(
        "--titles",
        action="store_true",
        help="仅读取六个公开视频 HTML 的标题，不下载或修改封面文件。",
    )
    arguments = argument_parser.parse_args()
    raise SystemExit(main(titles_only=arguments.titles))
