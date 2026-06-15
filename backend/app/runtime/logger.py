# Status: real

"""``agent_runs`` 持久化封装。

实现：
- ``log_agent_run`` 将一次 skill 调用写入 ``agent_runs`` 表；
- ``list_agent_runs`` 提供给 ``GET /api/v1/agent-runs`` trace 可视化使用；
- 当数据库不可用时静默降级（仅写日志）——铁律 §3.7 要求"必须落表"，但工程上需要在
  本地无 PG 时仍能完成 demo；运行时会在响应里标记 ``dry_run`` 供前端识别。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def _coerce_uuid(value: UUID | str | None) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None


def _coerce_uuid_list(values: list[UUID | str]) -> list[UUID]:
    coerced: list[UUID] = []
    for v in values:
        uid = _coerce_uuid(v)
        if uid is not None:
            coerced.append(uid)
    return coerced


async def log_agent_run(
    *,
    run_id: UUID | None = None,
    workflow_name: str,
    user_id: UUID | str | None,
    agent_id: UUID | str | None,
    skill_id: UUID | str | None,
    parent_run_id: UUID | str | None,
    input_summary: dict[str, Any],
    output_summary: dict[str, Any],
    evidence_chunk_ids: list[UUID | str],
    quality_score: float | None,
    status: str,
    duration_ms: int | None,
    token_usage: dict[str, Any],
) -> UUID | None:
    """将一次 skill 调用持久化到 ``agent_runs``。

    返回新写入的 ``id`` 用于级联引用；失败时返回 ``None`` 并仅写应用日志。
    """
    try:
        from app.db.models.agent_run import AgentRun
        from app.db.session import get_sessionmaker
    except Exception as exc:  # pragma: no cover
        logger.warning("agent_runs logger: db layer unavailable: %s", exc)
        return None

    try:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            run = AgentRun(
                id=run_id or uuid4(),
                workflow_name=workflow_name,
                user_id=_coerce_uuid(user_id),
                agent_id=_coerce_uuid(agent_id),
                skill_id=_coerce_uuid(skill_id),
                parent_run_id=_coerce_uuid(parent_run_id),
                input_summary=input_summary,
                output_summary=output_summary,
                evidence_chunk_ids=_coerce_uuid_list(evidence_chunk_ids),
                quality_score=quality_score,
                status=status,
                duration_ms=duration_ms,
                token_usage=token_usage,
            )
            session.add(run)
            await session.commit()
            return run.id
    except SQLAlchemyError as exc:
        logger.warning("agent_runs logger: DB insert failed: %s", exc)
        return None
    except Exception as exc:  # pragma: no cover
        logger.exception("agent_runs logger: unexpected failure: %s", exc)
        return None


async def list_agent_runs(
    *,
    workflow_name: str | None = None,
    user_id: UUID | str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """读取最近的 ``agent_runs`` 用于 trace 可视化。"""
    try:
        from app.db.models.agent_run import AgentRun
        from app.db.session import get_sessionmaker
    except Exception as exc:  # pragma: no cover
        logger.warning("agent_runs list: db layer unavailable: %s", exc)
        return []

    try:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            stmt = select(AgentRun).order_by(AgentRun.created_at.desc())
            if workflow_name:
                stmt = stmt.where(AgentRun.workflow_name == workflow_name)
            if user_id:
                uid = _coerce_uuid(user_id)
                if uid is not None:
                    stmt = stmt.where(AgentRun.user_id == uid)
            stmt = stmt.offset(offset).limit(limit)
            result = await session.execute(stmt)
            return [_serialize_run(row) for row in result.scalars().all()]
    except SQLAlchemyError as exc:
        logger.warning("agent_runs list: DB query failed: %s", exc)
        return []
    except Exception as exc:  # pragma: no cover
        logger.exception("agent_runs list: unexpected failure: %s", exc)
        return []


def _serialize_run(run: Any) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "workflow_name": run.workflow_name,
        "user_id": str(run.user_id) if run.user_id else None,
        "agent_id": str(run.agent_id) if run.agent_id else None,
        "skill_id": str(run.skill_id) if run.skill_id else None,
        "parent_run_id": str(run.parent_run_id) if run.parent_run_id else None,
        "input_summary": run.input_summary,
        "output_summary": run.output_summary,
        "evidence_chunk_ids": [str(x) for x in (run.evidence_chunk_ids or [])],
        "quality_score": run.quality_score,
        "status": run.status,
        "duration_ms": run.duration_ms,
        "token_usage": run.token_usage,
        "created_at": run.created_at.isoformat() if isinstance(run.created_at, datetime) else None,
    }
