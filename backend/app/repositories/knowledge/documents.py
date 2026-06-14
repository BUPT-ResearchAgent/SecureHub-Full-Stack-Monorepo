# Status: real

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.db.models.knowledge.document import Document
from app.repositories.base import UUIDPKRepository


class DocumentRepository(UUIDPKRepository[Document]):
    """P0 methods per task brief §5.2."""

    model = Document

    async def get_by_domain_url(self, domain: str, url: str) -> Document | None:
        result = await self.session.execute(
            select(Document).where(Document.domain == domain, Document.url == url)
        )
        return result.scalar_one_or_none()

    async def list_by_domain(
        self,
        domain: str,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Document]:
        stmt = select(Document).where(Document.domain == domain)
        if status is not None:
            stmt = stmt.where(Document.status == status)
        stmt = (
            stmt.order_by(Document.fetched_at.desc().nulls_last())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(
        self,
        *,
        document_id: UUID,
        domain: str,
        source_type: str,
        title: str,
        url: str | None = None,
        content_hash: str | None = None,
        raw_text: str | None = None,
        metadata: dict[str, Any] | None = None,
        trust_score: float = 0.5,
        status: str = "pending",
        fetched_at: datetime | None = None,
    ) -> Document:
        row = Document(
            id=document_id,
            domain=domain,
            source_type=source_type,
            title=title,
            url=url,
            content_hash=content_hash,
            raw_text=raw_text,
            metadata_=metadata or {},
            trust_score=trust_score,
            status=status,
            fetched_at=fetched_at,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def update_status(self, document_id: UUID, status: str) -> Document | None:
        row = await self.get_by_id(document_id)
        if row is None:
            return None
        row.status = status
        await self.session.flush()
        return row
