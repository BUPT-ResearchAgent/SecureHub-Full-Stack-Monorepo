# Status: real

"""Import public web pages into SecureHub data-layer v2.

Examples:
    cd backend
    uv run python ../scripts/crawl/scrapling_public_import.py --preset websec-core

    uv run python ../scripts/crawl/scrapling_public_import.py --url \
        https://portswigger.net/web-security/sql-injection \
        --platform portswigger --title "PortSwigger SQL injection"

    uv run python ../scripts/crawl/scrapling_public_import.py --source-file \
        ../data/raw/websec_sources.jsonl

Source-file rows may be JSON/JSONL/CSV with these optional fields:
url,title,platform,author,published_at,license,rights_note,source_type,reliability
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import get_sessionmaker  # noqa: E402
from app.knowledge.loaders.generic_web_loader import WebSourceSpec, generic_web_import  # noqa: E402


WEBSEC_CORE_SOURCES = [
    WebSourceSpec(
        url="https://owasp.org/www-community/attacks/SQL_Injection",
        title="OWASP SQL Injection",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note="OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。",
        source_type="owasp_public",
        reliability=0.9,
    ),
    WebSourceSpec(
        url="https://owasp.org/www-community/attacks/xss/",
        title="OWASP Cross Site Scripting",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note="OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。",
        source_type="owasp_public",
        reliability=0.9,
    ),
    WebSourceSpec(
        url="https://owasp.org/www-community/attacks/csrf",
        title="OWASP Cross-Site Request Forgery",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note="OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。",
        source_type="owasp_public",
        reliability=0.9,
    ),
    WebSourceSpec(
        url="https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload",
        title="OWASP Unrestricted File Upload",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note="OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。",
        source_type="owasp_public",
        reliability=0.9,
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/sql-injection",
        title="PortSwigger SQL injection",
        platform="portswigger",
        author="PortSwigger Web Security Academy",
        license="public learning reference",
        rights_note="PortSwigger Web Security Academy 公开学习资料；仅摘要引用并保留来源链接。",
        source_type="portswigger_public",
        reliability=0.9,
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/cross-site-scripting",
        title="PortSwigger Cross-site scripting",
        platform="portswigger",
        author="PortSwigger Web Security Academy",
        license="public learning reference",
        rights_note="PortSwigger Web Security Academy 公开学习资料；仅摘要引用并保留来源链接。",
        source_type="portswigger_public",
        reliability=0.9,
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/csrf",
        title="PortSwigger CSRF",
        platform="portswigger",
        author="PortSwigger Web Security Academy",
        license="public learning reference",
        rights_note="PortSwigger Web Security Academy 公开学习资料；仅摘要引用并保留来源链接。",
        source_type="portswigger_public",
        reliability=0.9,
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/file-upload",
        title="PortSwigger File upload vulnerabilities",
        platform="portswigger",
        author="PortSwigger Web Security Academy",
        license="public learning reference",
        rights_note="PortSwigger Web Security Academy 公开学习资料；仅摘要引用并保留来源链接。",
        source_type="portswigger_public",
        reliability=0.9,
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/ssrf",
        title="PortSwigger SSRF",
        platform="portswigger",
        author="PortSwigger Web Security Academy",
        license="public learning reference",
        rights_note="PortSwigger Web Security Academy 公开学习资料；仅摘要引用并保留来源链接。",
        source_type="portswigger_public",
        reliability=0.9,
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/access-control",
        title="PortSwigger Access control vulnerabilities",
        platform="portswigger",
        author="PortSwigger Web Security Academy",
        license="public learning reference",
        rights_note="PortSwigger Web Security Academy 公开学习资料；仅摘要引用并保留来源链接。",
        source_type="portswigger_public",
        reliability=0.9,
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import public web pages into SecureHub.")
    parser.add_argument("--preset", choices=["websec-core"], default=None)
    parser.add_argument("--source-file", type=Path, default=None)
    parser.add_argument("--url", action="append", default=[])
    parser.add_argument("--title", default=None)
    parser.add_argument("--platform", default=None)
    parser.add_argument("--author", default=None)
    parser.add_argument("--license", default="unknown")
    parser.add_argument("--rights-note", default=None)
    parser.add_argument("--domain", default="course_websec")
    parser.add_argument("--storage-prefix", default="course_websec/scrapling_public")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    sources = build_sources(args)
    if not sources:
        raise SystemExit("No sources provided. Use --preset, --source-file, or --url.")

    sessionmaker = get_sessionmaker()
    imported = []
    failed = []
    async with sessionmaker() as session:
        for source in sources:
            try:
                result = await generic_web_import(
                    [source],
                    session=session,
                    domain=args.domain,
                    storage_prefix=f"{args.storage_prefix}/{source.platform or 'web'}",
                )
                await session.commit()
                imported.append(
                    {
                        "url": source.url,
                        "documents": len(result.document_ids),
                        "chunks": result.chunk_count,
                        "assets": result.asset_count,
                    }
                )
                print(
                    "[scrapling_public_import] ok "
                    f"url={source.url} documents={len(result.document_ids)} "
                    f"chunks={result.chunk_count} assets={result.asset_count}"
                )
            except Exception as exc:  # noqa: BLE001 - importer must keep batch diagnostics.
                await session.rollback()
                failed.append({"url": source.url, "error": str(exc)})
                print(f"[scrapling_public_import] failed url={source.url} error={exc}")

    print(
        "[scrapling_public_import] summary "
        f"imported={len(imported)} failed={len(failed)} domain={args.domain}"
    )
    if failed:
        print(json.dumps({"failed": failed}, ensure_ascii=False, indent=2))


def build_sources(args: argparse.Namespace) -> list[WebSourceSpec]:
    sources: list[WebSourceSpec] = []
    if args.preset == "websec-core":
        sources.extend(WEBSEC_CORE_SOURCES)
    if args.source_file is not None:
        sources.extend(load_source_file(args.source_file))
    for url in args.url:
        sources.append(
            WebSourceSpec(
                url=url,
                title=args.title,
                platform=args.platform,
                author=args.author,
                license=args.license,
                rights_note=args.rights_note
                or "公开网页资料；仅用于课程知识库演示，保留链接与来源。",
            )
        )
    return sources


def load_source_file(path: Path) -> list[WebSourceSpec]:
    rows = read_rows(path)
    return [row_to_source(row) for row in rows if row.get("url")]


def read_rows(path: Path) -> list[dict[str, Any]]:
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
            for key in ("items", "sources", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [dict(item) for item in value if isinstance(item, dict)]
            return [payload]
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            return [dict(row) for row in csv.DictReader(fh)]
    raise ValueError(f"unsupported source file type: {path}")


def row_to_source(row: dict[str, Any]) -> WebSourceSpec:
    reliability = row.get("reliability")
    return WebSourceSpec(
        url=str(row["url"]),
        title=_optional_str(row.get("title")),
        platform=_optional_str(row.get("platform")),
        author=_optional_str(row.get("author")),
        published_at=_optional_str(row.get("published_at")),
        license=str(row.get("license") or "unknown"),
        rights_note=_optional_str(row.get("rights_note"))
        or "公开网页资料；仅用于课程知识库演示，保留链接与来源。",
        source_type=str(row.get("source_type") or "scrapling_public"),
        reliability=float(reliability) if reliability not in (None, "") else 0.75,
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


if __name__ == "__main__":
    asyncio.run(main())
