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
from app.knowledge.loaders.github_docs_loader import (
    DEFAULT_GITHUB_WEBSEC_SOURCES,
    GitHubDocsSource,
    _topic_from_path,
)
from app.knowledge.loaders.owasp_loader import DEFAULT_OWASP_WEBSEC_SOURCES
from app.knowledge.loaders.portswigger_loader import DEFAULT_PORTSWIGGER_WEBSEC_SOURCES
from app.services.knowledge.crawling.crawler_policy import CrawlPolicy, CrawlRequest
from app.services.knowledge.crawling.scrapling_client import ScraplingClient


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


def _github_sources_to_specs(sources: list[GitHubDocsSource]) -> list[WebSourceSpec]:
    specs: list[WebSourceSpec] = []
    for source in sources:
        specs.append(
            WebSourceSpec(
                url=source.url,
                title=source.title or f"{source.owner}/{source.repo} {source.path}",
                platform="github",
                author="OWASP CheatSheetSeries Contributors",
                license="CC BY-SA 4.0",
                rights_note=(
                    "OWASP CheatSheetSeries 官方仓库；按 CC BY-SA 4.0 署名引用；"
                    "raw markdown 直取"
                ),
                source_type="github_docs",
                reliability=0.95,
                html_text=source.html_text,
                metadata={
                    "repo": f"{source.owner}/{source.repo}",
                    "ref": source.ref,
                    "path": source.path,
                    "topic": _topic_from_path(source.path),
                },
            )
        )
    return specs


PLATFORM_SOURCES: dict[str, list[WebSourceSpec]] = {
    "owasp": DEFAULT_OWASP_WEBSEC_SOURCES,
    "portswigger": DEFAULT_PORTSWIGGER_WEBSEC_SOURCES,
    "github": _github_sources_to_specs(DEFAULT_GITHUB_WEBSEC_SOURCES),
}

WEBSEC_CORE_SOURCES: list[WebSourceSpec] = [
    source
    for platform in ("owasp", "portswigger", "github")
    for source in PLATFORM_SOURCES[platform]
]


@dataclass(slots=True)
class PublicWebImportOptions:
    sources: list[WebSourceSpec]
    domain: str = "course_websec"
    storage_prefix: str = "course_websec"
    replace_existing: bool = False
    dry_run: bool = False


@dataclass(slots=True)
class ImportedSource:
    url: str
    document_ids: list[str]
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
    parser.add_argument("--platform", choices=["owasp", "portswigger", "github", "all"], default=None)
    parser.add_argument("--source-platform", default=None)
    parser.add_argument("--author", default=None)
    parser.add_argument("--published-at", default=None)
    parser.add_argument("--license", default="unknown")
    parser.add_argument("--rights-note", default=None)
    parser.add_argument("--source-type", default="scrapling_public")
    parser.add_argument("--reliability", type=float, default=0.75)
    parser.add_argument("--css-selector", default=None)
    parser.add_argument("--xpath", default=None)
    parser.add_argument("--domain", default="course_websec")
    parser.add_argument("--storage-prefix", default="course_websec")
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
    if args.platform is not None:
        sources.extend(_platform_sources(args.platform))
    if args.preset == "websec-core":
        sources.extend(WEBSEC_CORE_SOURCES)
    if args.source_file is not None:
        sources.extend(load_source_file(args.source_file, candidates=sources or WEBSEC_CORE_SOURCES))
    for url in args.url:
        sources.append(
            WebSourceSpec(
                url=url,
                title=args.title,
                platform=args.source_platform,
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


def load_source_file(
    path: Path,
    *,
    candidates: list[WebSourceSpec] | None = None,
) -> list[WebSourceSpec]:
    if path.is_dir():
        return load_cache_dir(path, candidates=candidates or WEBSEC_CORE_SOURCES)
    rows = read_rows(path)
    return [row_to_source(row) for row in rows if row.get("url")]


def load_cache_dir(
    path: Path,
    *,
    candidates: list[WebSourceSpec],
) -> list[WebSourceSpec]:
    if not path.exists():
        return []
    by_stem = {_safe_url_key(source.url): source for source in candidates}
    sources: list[WebSourceSpec] = []
    files_by_stem: dict[str, list[Path]] = {}
    for file_path in sorted(path.iterdir()):
        if file_path.is_file() and file_path.suffix.lower() in {".html", ".htm", ".md"}:
            files_by_stem.setdefault(file_path.stem, []).append(file_path)

    for stem, files in sorted(files_by_stem.items()):
        file_path = next(
            (item for item in files if item.suffix.lower() in {".html", ".htm"}),
            files[0],
        )
        if file_path.suffix.lower() not in {".html", ".htm", ".md"}:
            continue
        source = by_stem.get(stem)
        text = file_path.read_text(encoding="utf-8", errors="replace")
        if source is not None:
            sources.append(_clone_source(source, html_text=text))
            continue
        sources.append(
            WebSourceSpec(
                url=file_path.resolve().as_uri(),
                title=file_path.stem.replace("_", " "),
                platform=file_path.parent.name,
                author="SecureHub cache replay",
                rights_note=PUBLIC_WEB_RIGHTS_NOTE,
                html_text=text,
                metadata={"cache_file": str(file_path)},
            )
        )
    return sources


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
    policy = CrawlPolicy(max_pages_per_run=11, download_delay_seconds=2.0)
    _validate_sources_for_dry_run(options.sources, policy=policy)
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

        client = ScraplingClient(policy=policy)
        for source in options.sources:
            try:
                result = await generic_web_import(
                    [source],
                    session=session,
                    domain=options.domain,
                    storage_prefix=_platform_storage_prefix(
                        options.storage_prefix,
                        source.platform or "web",
                    ),
                    client=client,
                    policy=policy,
                )
                await session.commit()
                summary.imported.append(
                    ImportedSource(
                        url=source.url,
                        document_ids=[str(item) for item in result.document_ids],
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
                "document_ids": item.document_ids,
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


def _platform_sources(platform: str) -> list[WebSourceSpec]:
    if platform == "all":
        return list(WEBSEC_CORE_SOURCES)
    return list(PLATFORM_SOURCES[platform])


def _validate_sources_for_dry_run(
    sources: list[WebSourceSpec],
    *,
    policy: CrawlPolicy,
) -> None:
    batch_counts: dict[str, int] = {}
    for source in sources:
        batch_key = source.platform or "web"
        batch_counts[batch_key] = batch_counts.get(batch_key, 0) + 1
        options: dict[str, object] = {}
        if source.css_selector:
            options["css_selector"] = source.css_selector
        if source.xpath:
            options["xpath"] = source.xpath
        policy.validate_request(CrawlRequest(url=source.url, options=options))
    for count in batch_counts.values():
        policy.validate_batch_size(count)


def _platform_storage_prefix(base: str, platform: str) -> str:
    normalized = base.replace("\\", "/").rstrip("/")
    if normalized.rsplit("/", 1)[-1] == platform:
        return normalized
    return f"{normalized}/{platform}"


def _clone_source(source: WebSourceSpec, *, html_text: str) -> WebSourceSpec:
    return WebSourceSpec(
        url=source.url,
        title=source.title,
        platform=source.platform,
        author=source.author,
        published_at=source.published_at,
        license=source.license,
        rights_note=source.rights_note,
        source_type=source.source_type,
        asset_type=source.asset_type,
        reliability=source.reliability,
        css_selector=source.css_selector,
        xpath=source.xpath,
        html_text=html_text,
        metadata=source.metadata,
    )


def _safe_url_key(url: str) -> str:
    from hashlib import sha256
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = (parsed.hostname or "web").replace(".", "_")
    path = parsed.path.strip("/").replace("/", "_") or "index"
    suffix = sha256(url.encode("utf-8")).hexdigest()[:10]
    return f"{host}_{path}_{suffix}"


if __name__ == "__main__":
    main()
