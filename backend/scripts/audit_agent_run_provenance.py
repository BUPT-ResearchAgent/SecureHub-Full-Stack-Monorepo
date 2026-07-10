# Status: real

"""Read-only provenance audit for the controlled real workflow query.

The audit intentionally reports identifiers and source metadata only.  It does
not print chunk text, document bodies, prompts, user data, or credentials.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any
from uuid import UUID

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select

from app.core.config import get_settings
from app.db.models.knowledge.chunk import Chunk
from app.db.models.knowledge.document import Document
from app.db.session import get_sessionmaker
from app.rag.retriever import retrieve


SOURCE_KEYS = ("source", "source_url", "url")


def _source_from_metadata(metadata: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    for key in SOURCE_KEYS:
        value = metadata.get(key)
        if value:
            return str(value), "chunk_metadata", key
    return None, None, None


def _document_source(
    document: Document | None,
) -> tuple[str | None, str | None, str | None]:
    if document is None:
        return None, None, None
    metadata = dict(document.metadata_ or {})
    for key in SOURCE_KEYS:
        value = metadata.get(key)
        if value:
            return str(value), "document_metadata", key
    if document.url:
        return str(document.url), "document.url", "url"
    return None, None, None


async def audit_provenance(query: str = "SQL 注入", top_k: int = 8) -> dict[str, Any]:
    """Return a safe provenance summary for one real RAG query."""
    settings = get_settings()
    async with get_sessionmaker()() as session:
        ready_count = int(
            (
                await session.execute(
                    select(func.count(Chunk.id))
                    .where(Chunk.domain == "course_websec")
                    .where(Chunk.embedding_status == "ready")
                    .where(Chunk.embedding.is_not(None))
                    .where(
                        Chunk.metadata_["embedding_profile"].as_string()
                        == settings.EMBEDDING_PROFILE
                    )
                )
            ).scalar_one()
        )

    hits = await retrieve(query, domain="course_websec", top_k=top_k)
    document_ids: set[UUID] = set()
    for hit in hits:
        try:
            if hit.document_id:
                document_ids.add(UUID(str(hit.document_id)))
        except (TypeError, ValueError):
            continue

    documents: dict[str, Document] = {}
    if document_ids:
        async with get_sessionmaker()() as session:
            rows = (
                await session.execute(
                    select(Document).where(Document.id.in_(document_ids))
                )
            ).scalars().all()
            documents = {str(row.id): row for row in rows}

    selected: list[dict[str, Any]] = []
    for hit in hits:
        metadata = dict(hit.metadata or {})
        source, origin, source_field = _source_from_metadata(metadata)
        if source is None:
            source, origin, source_field = _document_source(
                documents.get(str(hit.document_id))
            )
        platform = metadata.get("platform") or "manual"
        required_fields = [
            ("chunk_id", hit.chunk_id),
            ("document_id", hit.document_id),
            ("platform", platform),
        ]
        if platform != "manual":
            required_fields.append(("source", source))
        missing_fields = [
            field
            for field, value in required_fields
            if not value
        ]
        selected.append(
            {
                "chunk_id": str(hit.chunk_id),
                "document_id": str(hit.document_id) if hit.document_id else None,
                "platform": platform,
                "source": source,
                "source_origin": origin,
                "source_field": source_field,
                "missing_fields": missing_fields,
            }
        )

    missing = [item for item in selected if item["missing_fields"]]
    return {
        "ok": ready_count >= 3 and len(selected) >= 3 and not missing,
        "embedding_profile": settings.EMBEDDING_PROFILE,
        "ready_chunk_count": ready_count,
        "selected_count": len(selected),
        "selected": selected,
        "missing_count": len(missing),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit real RAG evidence provenance")
    parser.add_argument("--query", default="SQL 注入")
    parser.add_argument("--top-k", type=int, default=8)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.top_k < 3:
        print(json.dumps({"ok": False, "error_code": "TOP_K_TOO_LOW"}))
        return 1
    try:
        result = asyncio.run(audit_provenance(args.query, args.top_k))
    except Exception:
        print(json.dumps({"ok": False, "error_code": "PROVENANCE_AUDIT_FAILED"}))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
