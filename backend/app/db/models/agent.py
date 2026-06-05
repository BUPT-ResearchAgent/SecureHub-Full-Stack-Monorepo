# Status: [planned]

from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class Agent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    role_description: Mapped[str] = mapped_column(Text, nullable=False)
    capability_vector: Mapped[list[float]] = mapped_column(Vector(64), nullable=False)
    tools: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
