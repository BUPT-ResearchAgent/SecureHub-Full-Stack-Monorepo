# Status: real

"""Assessment endpoint：调用 outcome_evaluator.RunAssessment。"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.outcome_evaluator.skills.run_assessment import (
    RunAssessment,
    RunAssessmentInput,
)
from app.runtime.harness import HarnessContext

router = APIRouter()


class AssessmentRunRequest(BaseModel):
    user_id: str = "demo"
    course_id: str | None = None
    answers: list[dict[str, Any]] = Field(default_factory=list)
    query: str | None = None


class AssessmentRunResponse(BaseModel):
    task_id: str
    status: str = "ok"
    report: dict[str, Any]


@router.post("/assessment/run", response_model=AssessmentRunResponse)
async def assessment_run(payload: AssessmentRunRequest) -> AssessmentRunResponse:
    ctx = HarnessContext(user_id=payload.user_id, workflow_name="assessment")
    skill = RunAssessment()
    inp = RunAssessmentInput(
        user_id=payload.user_id,
        query=payload.query or "学习效果评估",
    )
    out = await skill.run(inp, ctx)
    return AssessmentRunResponse(task_id=str(uuid4()), report=out.model_dump())
