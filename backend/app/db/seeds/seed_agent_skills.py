# Status: real

"""Idempotent seed for the core §8.3 agent_skills catalogue."""

import asyncio
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seeds._constants import CORE_SKILLS, agent_id, skill_id
from app.db.session import get_sessionmaker


async def _upsert(
    session: AsyncSession, agent_name: str, skill_name: str
) -> None:
    aid = str(agent_id(agent_name))
    sid = str(skill_id(agent_name, skill_name))
    existing = await session.execute(
        text(
            "SELECT id FROM agent_skills "
            "WHERE agent_id = :aid AND skill_name = :sn AND version = :v"
        ),
        {"aid": aid, "sn": skill_name, "v": 1},
    )
    if existing.first():
        await session.execute(
            text(
                "UPDATE agent_skills SET enabled = :en WHERE agent_id = :aid "
                "AND skill_name = :sn AND version = :v"
            ),
            {"en": True, "aid": aid, "sn": skill_name, "v": 1},
        )
        return

    bind = await session.connection()
    is_pg = bind.dialect.name == "postgresql"
    payload: dict[str, Any] = {
        "id": sid,
        "aid": aid,
        "sn": skill_name,
        "pt": "TODO",
        "v": 1,
        "en": True,
    }
    if is_pg:
        payload["ad"] = ["course_websec"]
        payload["rt"] = ["rag.retrieve", "llm.xfyun"]
        await session.execute(
            text(
                "INSERT INTO agent_skills (id, agent_id, skill_name, prompt_template, "
                "applicable_domains, required_tools, output_schema, version, enabled) "
                "VALUES (:id, :aid, :sn, :pt, :ad, :rt, CAST('{}' AS jsonb), :v, :en)"
            ),
            payload,
        )
    else:
        payload["ad"] = json.dumps(["course_websec"])
        payload["rt"] = json.dumps(["rag.retrieve", "llm.xfyun"])
        await session.execute(
            text(
                "INSERT INTO agent_skills (id, agent_id, skill_name, prompt_template, "
                "applicable_domains, required_tools, output_schema, version, enabled) "
                "VALUES (:id, :aid, :sn, :pt, :ad, :rt, '{}', :v, :en)"
            ),
            payload,
        )


async def run(session: AsyncSession | None = None) -> int:
    total = sum(len(v) for v in CORE_SKILLS.values())
    if session is not None:
        for agent_name, skill_names in CORE_SKILLS.items():
            for skill_name in skill_names:
                await _upsert(session, agent_name, skill_name)
        return total

    sm = get_sessionmaker()
    async with sm() as own_session:
        for agent_name, skill_names in CORE_SKILLS.items():
            for skill_name in skill_names:
                await _upsert(own_session, agent_name, skill_name)
        await own_session.commit()
    return total


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(run())
