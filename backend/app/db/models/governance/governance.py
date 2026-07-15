# Status: real

"""RBAC and administrator governance overlays for existing product records."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RoleDefinition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A versioned, server-side role definition; browser roles are not trusted."""

    __tablename__ = "role_definitions"
    __table_args__ = (
        CheckConstraint("status IN ('active','retired')", name="ck_role_definitions_status"),
        UniqueConstraint("code", "version_no", name="uq_role_definitions_code_version"),
        Index(
            "uq_role_definitions_active_code",
            "code",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    permission_codes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")
    description: Mapped[str] = mapped_column(Text, nullable=False)


class UserRoleGrant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An auditable grant to an existing user; it never mirrors user fields."""

    __tablename__ = "user_role_grants"
    __table_args__ = (
        CheckConstraint("status IN ('active','revoked')", name="ck_user_role_grants_status"),
        Index(
            "uq_user_role_grants_active",
            "user_id",
            "role_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    role_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("role_definitions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    granted_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    revoked_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoke_reason: Mapped[str | None] = mapped_column(Text)


class CourseResourceGovernance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Administrator governance overlay for a T3 course asset lifecycle row."""

    __tablename__ = "course_resource_governance"
    __table_args__ = (
        CheckConstraint(
            "state IN ('active','restricted','withdrawn')",
            name="ck_course_resource_governance_state",
        ),
        UniqueConstraint("asset_id", name="uq_course_resource_governance_asset"),
    )

    asset_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("course_asset_governance.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")
    changed_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class KpiDefinition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Versioned query semantics, never a table of static dashboard counts."""

    __tablename__ = "kpi_definitions"
    __table_args__ = (
        CheckConstraint("status IN ('active','retired')", name="ck_kpi_definitions_status"),
        UniqueConstraint("code", "version_no", name="uq_kpi_definitions_code_version"),
        Index(
            "uq_kpi_definitions_active_code",
            "code",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    query_key: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_relations: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")
