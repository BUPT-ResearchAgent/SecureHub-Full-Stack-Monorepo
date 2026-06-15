# Status: real

"""Tutor endpoint：智能辅导意图识别 + 多 agent 路由（按 §7.1 + A3 加分项 P1-1）。"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.career_planner.skills.route_tutor_question import (
    RouteTutorQuestion,
    RouteTutorQuestionInput,
)
from app.runtime.harness import HarnessContext

router = APIRouter()


class TutorAskRequest(BaseModel):
    user_id: str = "demo"
    question: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)


class TutorAskResponse(BaseModel):
    task_id: str
    status: str = "ok"
    routing: dict[str, Any]


@router.post("/tutor/ask", response_model=TutorAskResponse)
async def tutor_ask(payload: TutorAskRequest) -> TutorAskResponse:
    ctx = HarnessContext(user_id=payload.user_id, workflow_name="tutor_routing")
    skill = RouteTutorQuestion()
    inp = RouteTutorQuestionInput(
        user_id=payload.user_id,
        query=payload.question,
        question=payload.question,
    )
    out = await skill.run(inp, ctx)
    return TutorAskResponse(task_id=str(uuid4()), routing=out.model_dump())
