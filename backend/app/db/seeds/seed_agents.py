# Status: real

"""Idempotent seed for the canonical 9-agent catalogue.

Mirrors the agents row content of ``20260611_0960_seed_agents_skills`` so
``python -m app.db.seeds.seed_agents`` re-asserts the same dataset on top of
an arbitrary database.
"""

import asyncio
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seeds._constants import AGENTS, agent_id
from app.db.session import get_sessionmaker


def _empty_vector_literal(dim: int = 64) -> str:
    return "[" + ",".join(["0"] * dim) + "]"


async def _upsert(session: AsyncSession, name: str, description: str, risk: str) -> None:
    existing = await session.execute(
        text("SELECT id FROM agents WHERE name = :name"), {"name": name}
    )
    if existing.first():
        await session.execute(
            text(
                "UPDATE agents SET role_description = :rd, risk_level = :rl, "
                "enabled = :en WHERE name = :name"
            ),
            {"rd": description, "rl": risk, "en": True, "name": name},
        )
        return

    bind = await session.connection()
    is_pg = bind.dialect.name == "postgresql"
    vector_literal = _empty_vector_literal()
    payload: dict[str, Any] = {
        "id": str(agent_id(name)),
        "name": name,
        "rd": description,
        "cv": vector_literal,
        "rl": risk,
        "en": True,
    }
    if is_pg:
        payload["tools"] = ["rag.retrieve", "llm.xfyun"]
        await session.execute(
            text(
                "INSERT INTO agents (id, name, role_description, capability_vector, "
                "tools, input_schema, output_schema, risk_level, enabled) "
                "VALUES (:id, :name, :rd, CAST(:cv AS vector), :tools, "
                "CAST('{}' AS jsonb), CAST('{}' AS jsonb), :rl, :en)"
            ),
            payload,
        )
    else:
        import json

        payload["tools"] = json.dumps(["rag.retrieve", "llm.xfyun"])
        await session.execute(
            text(
                "INSERT INTO agents (id, name, role_description, capability_vector, "
                "tools, input_schema, output_schema, risk_level, enabled) "
                "VALUES (:id, :name, :rd, :cv, :tools, '{}', '{}', :rl, :en)"
            ),
            payload,
        )


async def run(session: AsyncSession | None = None) -> int:
    """Insert / refresh the 9 canonical agents. Returns the row count seen."""
    if session is not None:
        for name, description, risk in AGENTS:
            await _upsert(session, name, description, risk)
        return len(AGENTS)

    sm = get_sessionmaker()
    async with sm() as own_session:
        for name, description, risk in AGENTS:
            await _upsert(own_session, name, description, risk)
        await own_session.commit()
    return len(AGENTS)


if __name__ == "__main__":  # pragma: no cover — CLI entry
    asyncio.run(run())
