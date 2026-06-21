# Status: real

"""Download remote Markdown images and rewrite links to local files.

Example:
    python scripts/localize_markdown_images.py \
        data/processed/mineru/MinerU_markdown_Web安全基础教程.md

By default this writes:
    data/processed/mineru/MinerU_markdown_Web安全基础教程.local.md
    data/processed/mineru/MinerU_markdown_Web安全基础教程_assets/
    data/processed/mineru/MinerU_markdown_Web安全基础教程_assets/manifest.json
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import mimetypes
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen


MARKDOWN_IMAGE_RE = re.compile(r"(!\[[^\]]*\]\()(?P<url>https?://[^)\s]+)(\))")


@dataclass(slots=True)
class DownloadedImage:
    url: str
    local_path: str
    size_bytes: int
    content_hash: str
    status: str
    error: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download remote images referenced by a Markdown file."
    )
    parser.add_argument("markdown", type=Path, help="Markdown file to process.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output Markdown path. Defaults to <stem>.local.md next to input.",
    )
    parser.add_argument(
        "--assets-dir",
        type=Path,
        default=None,
        help="Directory for downloaded images. Defaults to <stem>_assets next to input.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Rewrite the input Markdown file instead of writing <stem>.local.md.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-download files even when the local target already exists.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Per-image download timeout in seconds.",
    )
    parser.add_argument(
        "--downloader",
        choices=("auto", "curl", "python"),
        default="auto",
        help="Download backend. Defaults to curl when available, then Python urllib.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.05,
        help="Delay between downloads in seconds.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print counts and target paths; do not download or write files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    markdown_path = args.markdown.resolve()
    if not markdown_path.exists():
        raise SystemExit(f"Markdown not found: {markdown_path}")
    if args.in_place and args.output is not None:
        raise SystemExit("--output cannot be used with --in-place")

    output_path = (
        markdown_path
        if args.in_place
        else (args.output.resolve() if args.output else markdown_path.with_name(f"{markdown_path.stem}.local{markdown_path.suffix}"))
    )
    assets_dir = (
        args.assets_dir.resolve()
        if args.assets_dir
        else markdown_path.with_name(f"{markdown_path.stem}_assets").resolve()
    )

    markdown = markdown_path.read_text(encoding="utf-8")
    urls = list(dict.fromkeys(match.group("url") for match in MARKDOWN_IMAGE_RE.finditer(markdown)))
    print(
        "[localize_markdown_images] "
        f"markdown={markdown_path} remote_images={len(urls)} "
        f"output={output_path} assets_dir={assets_dir}"
    )
    if args.dry_run:
        return

    assets_dir.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, DownloadedImage] = {}
    for index, url in enumerate(urls, start=1):
        local_path = assets_dir / _filename_for_url(url, index)
        mapping[url] = _download_image(
            url,
            local_path=local_path,
            timeout=args.timeout,
            overwrite=args.overwrite,
            downloader=args.downloader,
        )
        status = mapping[url].status
        print(f"[{index}/{len(urls)}] {status}: {url} -> {local_path.name}")
        if args.sleep > 0 and index < len(urls):
            time.sleep(args.sleep)

    rewritten = MARKDOWN_IMAGE_RE.sub(
        lambda match: f"{match.group(1)}{_relative_posix(output_path, Path(mapping[match.group('url')].local_path))}{match.group(3)}",
        markdown,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rewritten, encoding="utf-8", newline="\n")

    manifest_path = assets_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "source_markdown": str(markdown_path),
                "output_markdown": str(output_path),
                "asset_count": len(mapping),
                "items": [asdict(item) for item in mapping.values()],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
        newline="\n",
    )

    failures = [item for item in mapping.values() if item.status == "failed"]
    print(
        "[localize_markdown_images] done "
        f"downloaded={len(mapping) - len(failures)} failed={len(failures)} "
        f"manifest={manifest_path}"
    )
    if failures:
        raise SystemExit(1)


def _download_image(
    url: str,
    *,
    local_path: Path,
    timeout: float,
    overwrite: bool,
    downloader: str,
) -> DownloadedImage:
    if local_path.exists() and not overwrite:
        content = local_path.read_bytes()
        return DownloadedImage(
            url=url,
            local_path=str(local_path),
            size_bytes=len(content),
            content_hash=sha256(content).hexdigest(),
            status="exists",
        )

    if downloader in {"auto", "curl"} and shutil.which("curl.exe"):
        result = _download_with_curl(url, local_path=local_path, timeout=timeout)
        if result.status != "failed" or downloader == "curl":
            return result

    request = Request(url, headers={"User-Agent": "SecureHub-MinerU-Asset-Localizer/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            content = response.read()
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return DownloadedImage(
            url=url,
            local_path=str(local_path),
            size_bytes=0,
            content_hash="",
            status="failed",
            error=str(exc),
        )

    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(content)
    return DownloadedImage(
        url=url,
        local_path=str(local_path),
        size_bytes=len(content),
        content_hash=sha256(content).hexdigest(),
        status="downloaded",
    )


def _download_with_curl(url: str, *, local_path: Path, timeout: float) -> DownloadedImage:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = local_path.with_name(f"{local_path.name}.part")
    if tmp_path.exists():
        tmp_path.unlink()

    command = [
        "curl.exe",
        "--fail",
        "--location",
        "--silent",
        "--show-error",
        "--max-time",
        str(timeout),
        "--retry",
        "2",
        "--retry-delay",
        "1",
        "--output",
        str(tmp_path),
        url,
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        if tmp_path.exists():
            tmp_path.unlink()
        error = (completed.stderr or completed.stdout or "").strip()
        return DownloadedImage(
            url=url,
            local_path=str(local_path),
            size_bytes=0,
            content_hash="",
            status="failed",
            error=f"curl exit {completed.returncode}: {error}",
        )

    tmp_path.replace(local_path)
    content = local_path.read_bytes()
    return DownloadedImage(
        url=url,
        local_path=str(local_path),
        size_bytes=len(content),
        content_hash=sha256(content).hexdigest(),
        status="downloaded",
    )


def _filename_for_url(url: str, index: int) -> str:
    parsed = urlsplit(url)
    original = Path(unquote(parsed.path)).name
    suffix = Path(original).suffix.lower()
    if not suffix:
        content_type = mimetypes.guess_type(url)[0]
        suffix = mimetypes.guess_extension(content_type or "") or ".bin"
    digest = sha256(url.encode("utf-8")).hexdigest()[:12]
    return f"image_{index:04d}_{digest}{suffix}"


def _relative_posix(from_file: Path, to_file: Path) -> str:
    return Path(os.path.relpath(to_file.resolve(), from_file.resolve().parent)).as_posix()


if __name__ == "__main__":
    main()
