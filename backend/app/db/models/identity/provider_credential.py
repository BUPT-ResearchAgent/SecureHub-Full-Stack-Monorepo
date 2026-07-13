# Status: real

"""Encrypted, user-owned credentials for supported chat providers."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProviderCredential(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One encrypted API credential owned by one user.

    ``encrypted_key`` is the only database field that can recover a key. It is
    AES-GCM ciphertext and is intentionally omitted from every response DTO.
    """

    __tablename__ = "provider_credentials"
    __table_args__ = (
        CheckConstraint("provider IN ('deepseek', 'xfyun')", name="ck_provider_credentials_provider"),
        CheckConstraint(
            "verification_status IN ('unverified', 'verified', 'invalid', 'error')",
            name="ck_provider_credentials_verification_status",
        ),
        UniqueConstraint("user_id", "provider", "name", name="uq_provider_credentials_user_provider_name"),
        Index(
            "uq_provider_credentials_active_user_provider",
            "user_id",
            "provider",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active = 1"),
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    key_fingerprint: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    verification_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="unverified", server_default="unverified"
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
