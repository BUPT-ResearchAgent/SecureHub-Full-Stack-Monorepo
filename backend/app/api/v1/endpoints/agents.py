# Status: real

"""智能体相关 endpoint：

- ``GET /agents`` 返回 9 智能体 + 各自 skill 名称（manifest）
- ``GET /agent-runs`` 返回最近的运行 trace（供前端可视化面板）
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.runtime.capability_manifest import list_agents, register_agents
from app.runtime.logger import list_agent_runs

router = APIRouter()


@router.get("/agents")
async def get_agents() -> list[dict[str, Any]]:
    # ensure all 9 agents are registered when endpoint is hit standalone
    register_agents()
    return [cls.manifest() for cls in list_agents()]


@router.get("/agent-runs")
async def get_agent_runs(
    workflow: str | None = Query(default=None, description="course_learning / tutor_routing / ..."),
    user_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    return await list_agent_runs(
        workflow_name=workflow,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
