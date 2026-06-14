# Status: [planned]

from typing import Any

from sqlalchemy import BigInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StorageObject(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Provider-agnostic file handle. P0 uses ``provider='local'``; P1/P2 can
    switch to MinIO / S3 / OSS / COS / R2 without touching business code,
    because callers only hold ``object_key``.
    """

    __tablename__ = "storage_objects"

    provider: Mapped[str] = mapped_column(String(32), default="local", nullable=False)
    bucket: Mapped[str | None] = mapped_column(String(128))
    object_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    content_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), default="ready", index=True, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
