# Status: real

"""Recoverable chunk embedding job."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import logging
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.knowledge.chunk import Chunk
from app.db.session import get_sessionmaker
from app.llm.embeddings.errors import EmbeddingError
from app.llm.embeddings.service import EmbeddingService

logger = logging.getLogger(__name__)


EMBEDDING_METADATA_KEYS = {
    "embedding_profile",
    "embedding_provider",
    "embedding_model",
    "embedding_dim",
    "embedding_output_type",
    "embedding_generated_at",
    "embedding_error_type",
    "embedding_error_message",
    "embedding_request_id",
    "embedding_retry_count",
}

STALE_PROCESSING_MINUTES = 30


class EmbedChunksResult(BaseModel):
    embedded_chunk_ids: list[UUID]
    skipped_chunk_ids: list[UUID]
    failed_chunk_ids: list[UUID] = []


class EmbedAllChunksResult(BaseModel):
    embedded: int = 0
    skipped: int = 0
    failed: int = 0
    batches: int = 0


async def embed_chunks(chunk_ids: list[UUID]) -> EmbedChunksResult:
    """Embed explicit chunks by id using the configured provider."""

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        stmt = select(Chunk).where(Chunk.id.in_(chunk_ids)).order_by(Chunk.created_at, Chunk.id)
        rows = (await session.execute(stmt)).scalars().all()
        result = await _embed_batch(session, rows, EmbeddingService(), retry_count=0)
        await session.commit()
    found_ids = {row.id for row in rows}
    return EmbedChunksResult(
        embedded_chunk_ids=result.embedded_chunk_ids,
        skipped_chunk_ids=[chunk_id for chunk_id in chunk_ids if chunk_id not in found_ids]
        + result.skipped_chunk_ids,
        failed_chunk_ids=result.failed_chunk_ids,
    )


async def embed_pending_chunks(
    *,
    domain: str | None = None,
    batch_size: int | None = None,
    limit: int | None = None,
    retry_failed: bool = False,
    recover_processing: bool = True,
    dry_run: bool = False,
) -> EmbedAllChunksResult:
    settings = get_settings()
    effective_batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE
    if not 1 <= effective_batch_size <= 10:
        raise ValueError("batch_size must be in 1..10")

    service: EmbeddingService | None = None
    totals = EmbedAllChunksResult()
    processed = 0
    try:
        while True:
            async with get_sessionmaker()() as session:
                rows = await _select_next_batch(
                    session,
                    domain=domain,
                    batch_size=effective_batch_size,
                    retry_failed=retry_failed,
                    recover_processing=recover_processing,
                    remaining=None if limit is None else max(limit - processed, 0),
                )
                if not rows:
                    break
                if dry_run:
                    totals.skipped += len(rows)
                    break
                for row in rows:
                    row.embedding_status = "processing"
                    row.metadata_ = _clear_embedding_metadata(row.metadata_ or {})
                await session.commit()

                if service is None:
                    service = EmbeddingService()
                result = await _embed_batch(session, rows, service, retry_count=0)
                await session.commit()

            totals.embedded += len(result.embedded_chunk_ids)
            totals.failed += len(result.failed_chunk_ids)
            totals.skipped += len(result.skipped_chunk_ids)
            totals.batches += 1
            processed += len(rows)
            logger.info(
                "embed job batch done embedded=%s failed=%s total_processed=%s profile=%s",
                totals.embedded,
                totals.failed,
                processed,
                settings.EMBEDDING_PROFILE,
            )
            if limit is not None and processed >= limit:
                break
    finally:
        if service is not None:
            await service.aclose()
    return totals


async def _select_next_batch(
    session: AsyncSession,
    *,
    domain: str | None,
    batch_size: int,
    retry_failed: bool,
    recover_processing: bool,
    remaining: int | None,
) -> list[Chunk]:
    if remaining is not None and remaining <= 0:
        return []
    statuses = ["pending"]
    if retry_failed:
        statuses.append("failed")
    if recover_processing:
        statuses.append("processing")
    stmt = (
        select(Chunk)
        .where(Chunk.embedding_status.in_(statuses))
        .order_by(Chunk.created_at, Chunk.id)
        .limit(min(batch_size, remaining) if remaining is not None else batch_size)
    )
    if domain:
        stmt = stmt.where(Chunk.domain == domain)
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows)


async def _embed_batch(
    session: AsyncSession,
    chunks: list[Chunk],
    service: EmbeddingService,
    *,
    retry_count: int,
) -> EmbedChunksResult:
    settings = get_settings()
    target_profile = settings.EMBEDDING_PROFILE
    to_embed: list[Chunk] = []
    skipped: list[UUID] = []
    for chunk in chunks:
        if (
            chunk.embedding_status == "ready"
            and chunk.embedding is not None
            and (chunk.metadata_ or {}).get("embedding_profile") == target_profile
        ):
            skipped.append(chunk.id)
        else:
            to_embed.append(chunk)
    if not to_embed:
        return EmbedChunksResult(embedded_chunk_ids=[], skipped_chunk_ids=skipped)

    try:
        result = await service.embed_documents([chunk.chunk_text for chunk in to_embed])
    except EmbeddingError as exc:
        failed_ids: list[UUID] = []
        for chunk in to_embed:
            chunk.embedding = None
            chunk.embedding_status = "failed"
            chunk.metadata_ = _failure_metadata(chunk.metadata_ or {}, exc, retry_count=retry_count)
            failed_ids.append(chunk.id)
        await session.flush()
        return EmbedChunksResult(
            embedded_chunk_ids=[],
            skipped_chunk_ids=skipped,
            failed_chunk_ids=failed_ids,
        )

    now = datetime.now(UTC).isoformat()
    embedded_ids: list[UUID] = []
    for chunk, vector in zip(to_embed, result.vectors, strict=True):
        chunk.embedding = vector
        chunk.embedding_status = "ready"
        metadata = _clear_embedding_metadata(chunk.metadata_ or {})
        metadata.update(
            {
                "embedding_profile": result.profile,
                "embedding_provider": result.provider,
                "embedding_model": result.model,
                "embedding_dim": result.dimension,
                "embedding_output_type": result.output_type,
                "embedding_generated_at": now,
            }
        )
        if result.request_id:
            metadata["embedding_request_id"] = result.request_id[:128]
        chunk.metadata_ = metadata
        embedded_ids.append(chunk.id)
    await session.flush()
    return EmbedChunksResult(
        embedded_chunk_ids=embedded_ids,
        skipped_chunk_ids=skipped,
        failed_chunk_ids=[],
    )


def _clear_embedding_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in dict(metadata).items() if key not in EMBEDDING_METADATA_KEYS}


def _failure_metadata(
    metadata: dict[str, Any],
    exc: Exception,
    *,
    retry_count: int,
) -> dict[str, Any]:
    cleaned = _clear_embedding_metadata(metadata)
    message = str(exc)
    cleaned.update(
        {
            "embedding_error_type": exc.__class__.__name__,
            "embedding_error_message": message[:300],
            "embedding_retry_count": retry_count,
        }
    )
    return cleaned


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Embed pending chunks with the configured provider.")
    parser.add_argument("--domain", default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument(
        "--no-recover-processing",
        action="store_true",
        help="Do not reclaim rows stuck in processing from a previous interrupted run.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args()
    result = await embed_pending_chunks(
        domain=args.domain,
        batch_size=args.batch_size,
        limit=args.limit,
        retry_failed=args.retry_failed,
        recover_processing=not args.no_recover_processing,
        dry_run=args.dry_run,
    )
    print(
        "[embed_chunks] "
        f"embedded={result.embedded} skipped={result.skipped} "
        f"failed={result.failed} batches={result.batches}"
    )


if __name__ == "__main__":
    asyncio.run(main())
