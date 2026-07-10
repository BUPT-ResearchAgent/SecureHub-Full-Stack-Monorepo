# Status: real

"""Download remote Markdown images and rewrite links to local files.

Examples:
    python scripts/localize_markdown_images.py \
        data/processed/mineru/MinerU_markdown_Web安全基础教程.md

    python scripts/localize_markdown_images.py --in-place \
        --host cdn-mineru.openxlab.org.cn

By default this writes:
    data/processed/mineru/MinerU_markdown_Web安全基础教程.local.md
    data/processed/mineru/MinerU_markdown_Web安全基础教程_assets/
    data/processed/mineru/MinerU_markdown_Web安全基础教程_assets/manifest.json

When no Markdown path is passed, the script scans:
    data/storage/course_websec/mineru/**/full.md
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
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MINERU_ROOT = REPO_ROOT / "data" / "storage" / "course_websec" / "mineru"


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
    parser.add_argument(
        "markdown",
        type=Path,
        nargs="*",
        help=(
            "Markdown file(s) to process. If omitted, scan "
            "data/storage/course_websec/mineru/**/full.md."
        ),
    )
    parser.add_argument(
        "--mineru-root",
        type=Path,
        default=DEFAULT_MINERU_ROOT,
        help="Root directory to scan when no Markdown file is passed.",
    )
    parser.add_argument(
        "--pattern",
        default="**/full.md",
        help="Glob pattern under --mineru-root when scanning automatically.",
    )
    parser.add_argument(
        "--host",
        action="append",
        default=[],
        help=(
            "Only localize image URLs from this host. Can be passed multiple "
            "times. By default all remote Markdown image URLs are localized."
        ),
    )
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
        help=(
            "Directory for downloaded images. Only valid for one Markdown file. "
            "Defaults to <stem>_assets for explicit single-file mode, or assets/ "
            "next to each full.md in automatic scan mode."
        ),
    )
    parser.add_argument(
        "--assets-name",
        default="assets",
        help="Assets directory name used in automatic scan mode.",
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
    markdown_paths = _resolve_markdown_paths(args)
    if not markdown_paths:
        raise SystemExit(
            f"No Markdown files found. Scanned: {args.mineru_root.resolve()} / {args.pattern}"
        )
    if args.in_place and args.output is not None:
        raise SystemExit("--output cannot be used with --in-place")
    if len(markdown_paths) > 1 and args.output is not None:
        raise SystemExit("--output can only be used with one Markdown file")
    if len(markdown_paths) > 1 and args.assets_dir is not None:
        raise SystemExit("--assets-dir can only be used with one Markdown file")

    auto_scan = len(args.markdown) == 0
    total = {"files": len(markdown_paths), "images": 0, "downloaded": 0, "failed": 0}
    for markdown_path in markdown_paths:
        result = _process_markdown(
            markdown_path,
            args=args,
            auto_scan=auto_scan,
        )
        total["images"] += result["images"]
        total["downloaded"] += result["downloaded"]
        total["failed"] += result["failed"]

    print(
        "[localize_markdown_images] batch done "
        f"files={total['files']} images={total['images']} "
        f"downloaded={total['downloaded']} failed={total['failed']}"
    )
    if total["failed"]:
        raise SystemExit(1)


def _resolve_markdown_paths(args: argparse.Namespace) -> list[Path]:
    if args.markdown:
        paths = [path.resolve() for path in args.markdown]
        missing = [path for path in paths if not path.exists()]
        if missing:
            raise SystemExit("Markdown not found: " + ", ".join(str(path) for path in missing))
        return paths

    mineru_root = args.mineru_root.resolve()
    if not mineru_root.exists():
        raise SystemExit(f"MinerU root not found: {mineru_root}")
    return sorted(path.resolve() for path in mineru_root.glob(args.pattern) if path.is_file())


def _process_markdown(
    markdown_path: Path,
    *,
    args: argparse.Namespace,
    auto_scan: bool,
) -> dict[str, int]:
    output_path = (
        markdown_path
        if args.in_place
        else (args.output.resolve() if args.output else markdown_path.with_name(f"{markdown_path.stem}.local{markdown_path.suffix}"))
    )
    assets_dir = (
        args.assets_dir.resolve()
        if args.assets_dir
        else (
            (markdown_path.parent / args.assets_name).resolve()
            if auto_scan
            else markdown_path.with_name(f"{markdown_path.stem}_assets").resolve()
        )
    )

    markdown = markdown_path.read_text(encoding="utf-8")
    hosts = set(args.host)
    urls = list(
        dict.fromkeys(
            url
            for url in (match.group("url") for match in MARKDOWN_IMAGE_RE.finditer(markdown))
            if not hosts or urlsplit(url).hostname in hosts
        )
    )
    print(
        "[localize_markdown_images] "
        f"markdown={markdown_path} remote_images={len(urls)} "
        f"output={output_path} assets_dir={assets_dir}"
    )
    if args.dry_run:
        return {"images": len(urls), "downloaded": 0, "failed": 0}

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
        lambda match: _rewrite_image_link(match, mapping, output_path),
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
                "host_filter": sorted(hosts),
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
    return {
        "images": len(urls),
        "downloaded": len(mapping) - len(failures),
        "failed": len(failures),
    }


def _rewrite_image_link(match: re.Match[str], mapping: dict[str, DownloadedImage], output_path: Path) -> str:
    url = match.group("url")
    item = mapping.get(url)
    if item is None or item.status == "failed":
        return match.group(0)
    return f"{match.group(1)}{_relative_posix(output_path, Path(item.local_path))}{match.group(3)}"


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
