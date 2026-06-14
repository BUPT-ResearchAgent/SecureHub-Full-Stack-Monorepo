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

from app.repositories.knowledge.document_assets import DocumentAssetRepository
from app.repositories.knowledge.documents import DocumentRepository
from app.services.knowledge.chunking_service import ChunkingService


@dataclass(slots=True)
class IngestionRequest:
    domain: str
    source_type: str
    title: str
    url: str | None = None
    raw_text: str | None = None
    metadata: dict[str, Any] | None = None
    assets: list[dict[str, Any]] | None = None  # [{asset_type, object_key, mime_type, ...}]


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

        content_hash = (
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
