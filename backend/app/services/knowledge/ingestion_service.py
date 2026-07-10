# Status: real

"""Per task brief §6.1 — IngestionService accepts a document payload
(content + URL + optional file path), writes a row to ``documents``, registers
the source assets in ``document_assets``, and hands off to ChunkingService.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge.chunk import Chunk
from app.repositories.knowledge.document_assets import DocumentAssetRepository
from app.repositories.knowledge.documents import DocumentRepository
from app.services.knowledge.chunking_service import ChunkingService


@dataclass(slots=True)
class PreChunkedItem:
    text: str
    chunk_index: int
    metadata: dict[str, Any]


@dataclass(slots=True)
class IngestionRequest:
    domain: str
    source_type: str
    title: str
    url: str | None = None
    raw_text: str | None = None
    content_hash: str | None = None
    metadata: dict[str, Any] | None = None
    assets: list[dict[str, Any]] | None = None  # [{asset_type, object_key, mime_type, ...}]
    pre_chunked: list[PreChunkedItem] | None = None


@dataclass(slots=True)
class IngestionResult:
    document_id: UUID
    chunk_count: int
    asset_count: int


class IngestionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ingest(self, request: IngestionRequest) -> IngestionResult:
        metadata = dict(request.metadata or {})
        fetched_at_value = metadata.get("fetched_at")
        fetched_at = (
            datetime.fromisoformat(fetched_at_value.replace("Z", "+00:00"))
            if isinstance(fetched_at_value, str)
            else datetime.now(UTC)
        )
        metadata.setdefault("platform", request.source_type)
        metadata.setdefault("source_url", request.url)
        metadata.setdefault("author", "SecureHub 手工整理")
        metadata.setdefault("published_at", None)
        metadata.setdefault("fetched_at", fetched_at.isoformat())
        metadata.setdefault("license", "unknown")
        metadata.setdefault("rights_note", "教学演示用途；保留原始来源，不批量转载。")

        content_hash = request.content_hash or (
            sha256(request.raw_text.encode("utf-8")).hexdigest()
            if request.raw_text
            else None
        )
        document_seed = request.url or f"{request.domain}:{request.title}:{content_hash or ''}"
        document_id = uuid5(NAMESPACE_URL, f"securehub:document:{document_seed}")

        documents = DocumentRepository(self.session)
        existing = (
            await documents.get_by_domain_url(request.domain, request.url)
            if request.url
            else await documents.get_by_id(document_id)
        )
        if existing is None:
            document = await documents.create(
                document_id=document_id,
                domain=request.domain,
                source_type=request.source_type,
                title=request.title,
                url=request.url,
                content_hash=content_hash,
                raw_text=request.raw_text,
                metadata=metadata,
                trust_score=float(metadata.get("trust_score", 0.75)),
                status="ready",
                fetched_at=fetched_at,
            )
        else:
            document = existing
            document.source_type = request.source_type
            document.title = request.title
            document.content_hash = content_hash or document.content_hash
            document.raw_text = request.raw_text or document.raw_text
            document.metadata_ = metadata
            document.status = "ready"
            document.fetched_at = fetched_at
            await self.session.flush()

        asset_repo = DocumentAssetRepository(self.session)
        existing_asset_keys = {
            (asset.asset_type, asset.object_key)
            for asset in await asset_repo.list_by_document(document.id)
        }
        asset_count = 0
        for asset in request.assets or []:
            asset_type = str(asset["asset_type"])
            object_key = str(asset["object_key"])
            if (asset_type, object_key) in existing_asset_keys:
                continue
            asset_id = uuid5(
                NAMESPACE_URL,
                f"securehub:document_asset:{document.id}:{asset_type}:{object_key}",
            )
            await asset_repo.create(
                asset_id=asset_id,
                document_id=document.id,
                asset_type=asset_type,
                object_key=object_key,
                mime_type=asset.get("mime_type"),
                size_bytes=asset.get("size_bytes"),
                content_hash=asset.get("content_hash"),
                metadata=asset.get("metadata"),
            )
            asset_count += 1

        all_assets = await asset_repo.list_by_document(document.id)
        asset_ids_by_key = {
            (asset.asset_type, asset.object_key): str(asset.id)
            for asset in all_assets
        }

        if request.pre_chunked is not None:
            chunk_ids = await self._create_pre_chunked_rows(
                document_id=document.id,
                domain=request.domain,
                items=request.pre_chunked,
                document_metadata=metadata,
                asset_ids_by_key=asset_ids_by_key,
            )
            return IngestionResult(
                document_id=document.id,
                chunk_count=len(chunk_ids),
                asset_count=asset_count,
            )

        chunk_ids = await ChunkingService(self.session).chunk_document(
            document.id,
            metadata={
                "source_url": request.url,
                "asset_type": metadata.get("asset_type", request.source_type),
                "platform": metadata.get("platform"),
                "author": metadata.get("author"),
                "published_at": metadata.get("published_at"),
                "fetched_at": metadata.get("fetched_at"),
                "rights_note": metadata.get("rights_note"),
            },
        )
        return IngestionResult(
            document_id=document.id,
            chunk_count=len(chunk_ids),
            asset_count=asset_count,
        )

    async def _create_pre_chunked_rows(
        self,
        *,
        document_id: UUID,
        domain: str,
        items: list[PreChunkedItem],
        document_metadata: dict[str, Any],
        asset_ids_by_key: dict[tuple[str, str], str],
    ) -> list[UUID]:
        from app.repositories.knowledge.chunks import ChunkRepository

        chunks = ChunkRepository(self.session)
        existing = await chunks.list_by_document(document_id)
        if existing:
            return [row.id for row in existing]

        source_metadata = {
            "source_url": document_metadata.get("source_url"),
            "asset_type": document_metadata.get("asset_type"),
            "platform": document_metadata.get("platform"),
            "author": document_metadata.get("author"),
            "published_at": document_metadata.get("published_at"),
            "fetched_at": document_metadata.get("fetched_at"),
            "rights_note": document_metadata.get("rights_note"),
            "license": document_metadata.get("license"),
            "collection_mode": document_metadata.get("collection_mode"),
        }
        source_metadata = {key: value for key, value in source_metadata.items() if value is not None}

        rows: list[Chunk] = []
        for item in sorted(items, key=lambda row: row.chunk_index):
            item_metadata = dict(source_metadata)
            item_metadata.update(item.metadata)
            object_key = item_metadata.get("asset_object_key")
            asset_type = item_metadata.get("asset_type") or "markdown_chapter"
            if "asset_id" not in item_metadata and isinstance(object_key, str):
                asset_id = asset_ids_by_key.get((str(asset_type), object_key))
                if asset_id is not None:
                    item_metadata["asset_id"] = asset_id

            chunk_id = uuid5(
                NAMESPACE_URL,
                f"securehub:chunk:{document_id}:{item.chunk_index}",
            )
            rows.append(
                Chunk(
                    id=chunk_id,
                    document_id=document_id,
                    domain=domain,
                    chunk_text=item.text,
                    chunk_index=item.chunk_index,
                    token_count=len(item.text.split()),
                    embedding=None,
                    embedding_status="pending",
                    metadata_=item_metadata | {"chunker": "chapter_window_v1"},
                )
            )

        await chunks.bulk_create(rows)
        return [row.id for row in rows]
