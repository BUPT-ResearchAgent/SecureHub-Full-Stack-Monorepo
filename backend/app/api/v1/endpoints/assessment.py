# Status: partial-real

"""Assessment endpoint with real-first service adapter and skill fallback."""

from __future__ import annotations

from fastapi import APIRouter

from app.agents.outcome_evaluator.skills.run_assessment import (
    RunAssessment,
    RunAssessmentInput,
)
from app.api.v1.endpoints.streaming import (
    call_json_service,
    raise_mapped_error,
    service_kwargs,
)
from app.runtime.harness import HarnessContext
from app.schemas.assessment import AssessmentRunRequest, AssessmentRunResponse

router = APIRouter()

try:
    from app.services.agent import run_assessment as real_run_assessment
except ImportError:
    real_run_assessment = None


def _assessment_response(result: object) -> AssessmentRunResponse:
    plain = result if isinstance(result, dict) else {}
    nested = plain.get("assessment") if isinstance(plain.get("assessment"), dict) else {}
    source = nested if isinstance(nested, dict) else plain

    raw_score = (
        source.get("score")
        or source.get("overall_score")
        or plain.get("score")
        or plain.get("quality_score")
        or 0.0
    )
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        score = 0.0

    feedback = source.get("feedback") or plain.get("content") or source.get("next_recommendation") or "评估已完成"
    updated_capabilities = source.get("updated_capabilities")
    if not isinstance(updated_capabilities, list):
        deltas = source.get("capability_delta")
        if isinstance(deltas, dict):
            updated_capabilities = [
                {
                    "dimension": str(dimension),
                    "score": min(1.0, max(0.0, 0.5 + float(delta))),
                    "confidence": 0.7,
                    "evidence_count": len(plain.get("evidence_chunk_ids", []) or []),
                }
                for dimension, delta in deltas.items()
                if isinstance(delta, int | float)
            ]
        else:
            updated_capabilities = []

    return AssessmentRunResponse(
        score=score,
        feedback=str(feedback),
        updated_capabilities=updated_capabilities,
    )


@router.post("/assessment/run", response_model=AssessmentRunResponse)
async def assessment_run(payload: AssessmentRunRequest) -> AssessmentRunResponse:
    if real_run_assessment is not None:
        result = await call_json_service(real_run_assessment, kwargs=service_kwargs(payload))
        return _assessment_response(result)

    try:
        ctx = HarnessContext(user_id=str(payload.user_id), workflow_name="assessment")
        out = await RunAssessment().run(
            RunAssessmentInput(
                user_id=str(payload.user_id),
                query="Run learning assessment",
                answers=payload.answers,
            ),
            ctx,
        )
        return _assessment_response(out.model_dump(mode="json"))
    except Exception as exc:  # noqa: BLE001 - normalized API boundary
        raise_mapped_error(exc)
