# Status: [planned]

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class AgentSkill(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_skills"
    __table_args__ = (
        UniqueConstraint("agent_id", "skill_name", "version", name="uq_agent_skills_agent_skill_version"),
    )

    agent_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    applicable_domains: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    required_tools: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
