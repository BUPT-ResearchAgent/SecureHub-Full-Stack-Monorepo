# Status: real

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.db.models.knowledge.document_asset import DocumentAsset
from app.repositories.base import UUIDPKRepository


class DocumentAssetRepository(UUIDPKRepository[DocumentAsset]):
    """P0 methods per task brief §5.2."""

    model = DocumentAsset

    async def list_by_document(self, document_id: UUID) -> Sequence[DocumentAsset]:
        stmt = (
            select(DocumentAsset)
            .where(DocumentAsset.document_id == document_id)
            .order_by(DocumentAsset.asset_type, DocumentAsset.created_at)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(
        self,
        *,
        asset_id: UUID,
        document_id: UUID,
        asset_type: str,
        object_key: str,
        mime_type: str | None = None,
        size_bytes: int | None = None,
        content_hash: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DocumentAsset:
        row = DocumentAsset(
            id=asset_id,
            document_id=document_id,
            asset_type=asset_type,
            object_key=object_key,
            mime_type=mime_type,
            size_bytes=size_bytes,
            content_hash=content_hash,
            metadata_=metadata or {},
        )
        self.session.add(row)
        await self.session.flush()
        return row
