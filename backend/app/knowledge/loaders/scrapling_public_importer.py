# Status: real

"""CLI-friendly public web importer for SecureHub's unified knowledge layer.

The module lives under ``backend/app`` so it can be executed in the backend
Docker container with ``python -m app.knowledge.loaders.scrapling_public_importer``.
The repository-level script in ``scripts/crawl`` is kept as a convenience
wrapper for host-side runs.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from sqlalchemy import delete, select

from app.db.models.knowledge.document import Document
from app.db.models.knowledge.document_asset import DocumentAsset
from app.db.models.storage.storage_object import StorageObject
from app.db.session import get_sessionmaker
from app.knowledge.loaders.generic_web_loader import WebSourceSpec, generic_web_import
from app.knowledge.loaders.owasp_loader import OWASP_CONTENT_XPATH
from app.knowledge.loaders.portswigger_loader import PORTSWIGGER_CONTENT_XPATH


OWASP_RIGHTS_NOTE = (
    "OWASP public community documentation; keep source URL and cite under "
    "the documented license."
)
PORTSWIGGER_RIGHTS_NOTE = (
    "PortSwigger Web Security Academy public learning material; keep source "
    "URL and use short excerpts for course demonstration."
)
PUBLIC_WEB_RIGHTS_NOTE = (
    "Public web learning material for SecureHub course demo; keep source URL, "
    "author, fetched time, and rights note."
)


WEBSEC_CORE_SOURCES: list[WebSourceSpec] = [
    WebSourceSpec(
        url="https://owasp.org/www-community/attacks/SQL_Injection",
        title="OWASP SQL Injection",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note=OWASP_RIGHTS_NOTE,
        source_type="owasp_public",
        reliability=0.9,
        xpath=OWASP_CONTENT_XPATH,
    ),
    WebSourceSpec(
        url="https://owasp.org/www-community/attacks/xss/",
        title="OWASP Cross Site Scripting",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note=OWASP_RIGHTS_NOTE,
        source_type="owasp_public",
        reliability=0.9,
        xpath=OWASP_CONTENT_XPATH,
    ),
    WebSourceSpec(
        url="https://owasp.org/www-community/attacks/csrf",
        title="OWASP Cross-Site Request Forgery",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note=OWASP_RIGHTS_NOTE,
        source_type="owasp_public",
        reliability=0.9,
        xpath=OWASP_CONTENT_XPATH,
    ),
    WebSourceSpec(
        url="https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload",
        title="OWASP Unrestricted File Upload",
        platform="owasp",
        author="OWASP",
        license="CC BY-SA 4.0",
        rights_note=OWASP_RIGHTS_NOTE,
        source_type="owasp_public",
        reliability=0.9,
        xpath=OWASP_CONTENT_XPATH,
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/sql-injection",
        title="PortSwigger SQL injection",
        platform="portswigger",
        author="PortSwigger Web Security Academy",
        license="public learning reference",
        rights_note=PORTSWIGGER_RIGHTS_NOTE,
        source_type="portswigger_public",
        reliability=0.9,
        xpath=PORTSWIGGER_CONTENT_XPATH,
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/cross-site-scripting",
        title="PortSwigger Cross-site scripting",
        platform="portswigger",
        author="PortSwigger Web Security Academy",
        license="public learning reference",
        rights_note=PORTSWIGGER_RIGHTS_NOTE,
        source_type="portswigger_public",
        reliability=0.9,
        xpath=PORTSWIGGER_CONTENT_XPATH,
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/csrf",
        title="PortSwigger CSRF",
        platform="portswigger",
        author="PortSwigger Web Security Academy",
        license="public learning reference",
        rights_note=PORTSWIGGER_RIGHTS_NOTE,
        source_type="portswigger_public",
        reliability=0.9,
        xpath=PORTSWIGGER_CONTENT_XPATH,
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/file-upload",
        title="PortSwigger File upload vulnerabilities",
        platform="portswigger",
        author="PortSwigger Web Security Academy",
        license="public learning reference",
        rights_note=PORTSWIGGER_RIGHTS_NOTE,
        source_type="portswigger_public",
        reliability=0.9,
        xpath=PORTSWIGGER_CONTENT_XPATH,
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/ssrf",
        title="PortSwigger SSRF",
        platform="portswigger",
        author="PortSwigger Web Security Academy",
        license="public learning reference",
        rights_note=PORTSWIGGER_RIGHTS_NOTE,
        source_type="portswigger_public",
        reliability=0.9,
        xpath=PORTSWIGGER_CONTENT_XPATH,
    ),
    WebSourceSpec(
        url="https://portswigger.net/web-security/access-control",
        title="PortSwigger Access control vulnerabilities",
        platform="portswigger",
        author="PortSwigger Web Security Academy",
        license="public learning reference",
        rights_note=PORTSWIGGER_RIGHTS_NOTE,
        source_type="portswigger_public",
        reliability=0.9,
        xpath=PORTSWIGGER_CONTENT_XPATH,
    ),
]


@dataclass(slots=True)
class PublicWebImportOptions:
    sources: list[WebSourceSpec]
    domain: str = "course_websec"
    storage_prefix: str = "course_websec/scrapling_public"
    replace_existing: bool = False
    dry_run: bool = False


@dataclass(slots=True)
class ImportedSource:
    url: str
    document_count: int
    chunk_count: int
    asset_count: int


@dataclass(slots=True)
class FailedSource:
    url: str
    error: str


@dataclass(slots=True)
class PublicWebImportSummary:
    domain: str
    requested_count: int
    deleted_documents: int = 0
    deleted_storage_objects: int = 0
    imported: list[ImportedSource] = field(default_factory=list)
    failed: list[FailedSource] = field(default_factory=list)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import public web pages into SecureHub data-layer v2."
    )
    parser.add_argument("--preset", choices=["websec-core"], default=None)
    parser.add_argument("--source-file", type=Path, default=None)
    parser.add_argument("--url", action="append", default=[])
    parser.add_argument("--title", default=None)
    parser.add_argument("--platform", default=None)
    parser.add_argument("--author", default=None)
    parser.add_argument("--published-at", default=None)
    parser.add_argument("--license", default="unknown")
    parser.add_argument("--rights-note", default=None)
    parser.add_argument("--source-type", default="scrapling_public")
    parser.add_argument("--reliability", type=float, default=0.75)
    parser.add_argument("--css-selector", default=None)
    parser.add_argument("--xpath", default=None)
    parser.add_argument("--domain", default="course_websec")
    parser.add_argument("--storage-prefix", default="course_websec/scrapling_public")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Import only the first N sources. Useful for smoke checks.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing documents/assets/storage for the selected URLs before import.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List resolved sources without touching the database or network.",
    )
    return parser


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
                published_at=args.published_at,
                license=args.license,
                rights_note=args.rights_note or PUBLIC_WEB_RIGHTS_NOTE,
                source_type=args.source_type,
                reliability=args.reliability,
                css_selector=args.css_selector,
                xpath=args.xpath,
            )
        )
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("--limit must be a positive integer")
        sources = sources[: args.limit]
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
        rights_note=_optional_str(row.get("rights_note")) or PUBLIC_WEB_RIGHTS_NOTE,
        source_type=str(row.get("source_type") or "scrapling_public"),
        asset_type=str(row.get("asset_type") or "web_article"),
        reliability=float(reliability) if reliability not in (None, "") else 0.75,
        css_selector=_optional_str(row.get("css_selector")),
        xpath=_optional_str(row.get("xpath")),
        metadata=_metadata_from_row(row),
    )


async def run_import(options: PublicWebImportOptions) -> PublicWebImportSummary:
    if not options.sources:
        raise ValueError("No sources provided. Use --preset, --source-file, or --url.")

    summary = PublicWebImportSummary(
        domain=options.domain,
        requested_count=len(options.sources),
    )
    if options.dry_run:
        return summary

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        if options.replace_existing:
            deleted_documents, deleted_storage_objects = await _delete_existing_sources(
                session,
                sources=options.sources,
                domain=options.domain,
            )
            summary.deleted_documents = deleted_documents
            summary.deleted_storage_objects = deleted_storage_objects
            await session.commit()

        for source in options.sources:
            try:
                result = await generic_web_import(
                    [source],
                    session=session,
                    domain=options.domain,
                    storage_prefix=(
                        f"{options.storage_prefix}/{source.platform or 'web'}"
                    ),
                )
                await session.commit()
                summary.imported.append(
                    ImportedSource(
                        url=source.url,
                        document_count=len(result.document_ids),
                        chunk_count=result.chunk_count,
                        asset_count=result.asset_count,
                    )
                )
            except Exception as exc:  # noqa: BLE001 - keep batch diagnostics.
                await session.rollback()
                summary.failed.append(FailedSource(url=source.url, error=str(exc)))

    return summary


async def _delete_existing_sources(
    session,
    *,
    sources: Sequence[WebSourceSpec],
    domain: str,
) -> tuple[int, int]:
    urls = [source.url for source in sources]
    if not urls:
        return 0, 0

    document_ids = (
        await session.execute(
            select(Document.id).where(Document.domain == domain, Document.url.in_(urls))
        )
    ).scalars().all()
    if not document_ids:
        return 0, 0

    object_keys = (
        await session.execute(
            select(DocumentAsset.object_key).where(
                DocumentAsset.document_id.in_(document_ids)
            )
        )
    ).scalars().all()

    await session.execute(delete(Document).where(Document.id.in_(document_ids)))
    deleted_storage = 0
    if object_keys:
        result = await session.execute(
            delete(StorageObject).where(StorageObject.object_key.in_(object_keys))
        )
        deleted_storage = int(result.rowcount or 0)
    return len(document_ids), deleted_storage


def format_summary(summary: PublicWebImportSummary) -> str:
    payload = {
        "domain": summary.domain,
        "requested": summary.requested_count,
        "deleted_documents": summary.deleted_documents,
        "deleted_storage_objects": summary.deleted_storage_objects,
        "imported": [
            {
                "url": item.url,
                "documents": item.document_count,
                "chunks": item.chunk_count,
                "assets": item.asset_count,
            }
            for item in summary.imported
        ],
        "failed": [
            {"url": item.url, "error": item.error}
            for item in summary.failed
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


async def main_async(argv: Sequence[str] | None = None) -> PublicWebImportSummary:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    sources = build_sources(args)
    if not sources:
        raise SystemExit("No sources provided. Use --preset, --source-file, or --url.")

    if args.dry_run:
        for source in sources:
            print(
                "[scrapling_public_import] dry-run "
                f"platform={source.platform or 'web'} title={source.title or ''} "
                f"url={source.url}"
            )

    summary = await run_import(
        PublicWebImportOptions(
            sources=sources,
            domain=args.domain,
            storage_prefix=args.storage_prefix,
            replace_existing=args.replace,
            dry_run=args.dry_run,
        )
    )
    print("[scrapling_public_import] summary")
    print(format_summary(summary))
    return summary


def main(argv: Sequence[str] | None = None) -> None:
    asyncio.run(main_async(argv))


def _metadata_from_row(row: dict[str, Any]) -> dict[str, Any] | None:
    metadata = row.get("metadata")
    if isinstance(metadata, dict):
        return dict(metadata)
    if isinstance(metadata, str) and metadata.strip():
        try:
            value = json.loads(metadata)
        except json.JSONDecodeError:
            return {"source_metadata": metadata}
        if isinstance(value, dict):
            return value
    return None


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


if __name__ == "__main__":
    main()
