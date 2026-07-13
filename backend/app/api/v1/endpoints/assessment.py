# Status: real

"""Assessment HTTP adapter for the atomic ``assessment_update_v2`` root."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.v1.endpoints.workflow_adapter import (
    accepted_root_response,
    completed_root_response,
    require_successful_terminal,
    start_product_workflow,
    wait_for_terminal,
    workflow_service,
)
from app.deps import CurrentUserDep
from app.schemas.agent_control import WorkflowRunStartResponse
from app.schemas.assessment import AssessmentRunRequest, AssessmentRunResponse
from app.services.workflow_application_service import WorkflowApplicationService


router = APIRouter()


def _service(request: Request) -> WorkflowApplicationService:
    return workflow_service(request)


def _first_present(source: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = source.get(key)
        if value is not None:
            return value
    return None


def _assessment_response(result: dict[str, Any]) -> AssessmentRunResponse:
    nested = result.get("assessment")
    source = nested if isinstance(nested, dict) else result
    raw_score = _first_present(source, "score", "overall_score", "quality_score")
    if raw_score is None and source is not result:
        raw_score = _first_present(result, "score", "overall_score", "quality_score")
    try:
        score = float(raw_score)
    except (TypeError, ValueError) as exc:
        raise ValueError("workflow output does not contain a numeric assessment score") from exc

    feedback = _first_present(source, "feedback", "next_recommendation", "content")
    if feedback is None and source is not result:
        feedback = _first_present(result, "feedback", "next_recommendation", "content")
    if not isinstance(feedback, str) or not feedback.strip():
        raise ValueError("workflow output does not contain assessment feedback")

    updated_capabilities = source.get("updated_capabilities")
    if updated_capabilities is None and source is not result:
        updated_capabilities = result.get("updated_capabilities")
    if not isinstance(updated_capabilities, list):
        deltas = _first_present(source, "capability_delta", "delta")
        if not isinstance(deltas, dict) and source is not result:
            deltas = _first_present(result, "capability_delta", "delta")
        if isinstance(deltas, dict):
            updated_capabilities = []
            for dimension, delta in deltas.items():
                if not isinstance(delta, int | float):
                    continue
                updated_capabilities.append(
                    {
                        "dimension": str(dimension),
                        "score": min(1.0, max(0.0, 0.5 + float(delta))),
                        "confidence": 0.7,
                        "evidence_count": 0,
                    }
                )
        else:
            updated_capabilities = []

    return AssessmentRunResponse(
        score=score,
        feedback=feedback,
        updated_capabilities=updated_capabilities,
        assessment_audit=(
            result.get("assessment_audit")
            if isinstance(result.get("assessment_audit"), dict)
            else None
        ),
    )


@router.post(
    "/assessment/run",
    response_model=AssessmentRunResponse | WorkflowRunStartResponse,
    responses={202: {"model": WorkflowRunStartResponse, "description": "Durable workflow remains in progress."}},
)
async def assessment_run(
    payload: AssessmentRunRequest,
    request: Request,
    current_user_id: CurrentUserDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> AssessmentRunResponse | JSONResponse:
    service = _service(request)
    start = await start_product_workflow(
        service,
        workflow="assessment_update_v2",
        actor_user_id=current_user_id,
        course_id=payload.course_id,
        input_payload={
            "answers": payload.answers,
            "quiz_artifact_id": payload.quiz_artifact_id,
            "domain": "course_websec",
        },
        mode=payload.mode,
        provider=payload.provider,
        model=payload.model,
        idempotency_key=idempotency_key,
    )
    terminal = await wait_for_terminal(service, start.run_id, actor_user_id=current_user_id)
    if terminal is None:
        return accepted_root_response(start)
    try:
        completed = _assessment_response(require_successful_terminal(terminal))
        return completed_root_response(start, completed.model_dump(mode="json"))
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "WORKFLOW_OUTPUT_INVALID", "message": str(exc)},
        ) from exc
