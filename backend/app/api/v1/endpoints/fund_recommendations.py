# Status: real

"""Authenticated product adapter for the independent fund recommendation root."""

from __future__ import annotations

from fastapi import APIRouter, Header, Request, status
from fastapi.responses import JSONResponse

from app.api.v1.endpoints.workflow_adapter import accepted_root_response, start_product_workflow, workflow_service
from app.deps import CurrentUserDep, SessionDep
from app.schemas.fund_recommendation import FundRecommendationRequest
from app.services.fund_recommendation_service import FundRecommendationService
from app.services.workflow_application_service import WorkflowApplicationService


router = APIRouter()


def _workflow_service(request: Request) -> WorkflowApplicationService:
    return workflow_service(request)


@router.post(
    "/research/fund-recommendations",
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_fund_recommendation(
    payload: FundRecommendationRequest,
    request: Request,
    session: SessionDep,
    current_user_id: CurrentUserDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JSONResponse:
    # The browser owns only its request/topic/course-KP hand-off. The profile
    # snapshot and root owner are resolved server-side from CurrentUserDep.
    root_input = await FundRecommendationService(session).prepare_root_input(
        user_id=current_user_id,
        request=payload,
    )
    start = await start_product_workflow(
        _workflow_service(request),
        workflow="fund_recommendation_v1",
        actor_user_id=current_user_id,
        input_payload=root_input,
        # A course hand-off is context only. It never attaches the new fund
        # root to, or reuses, a course workflow root.
        course_id=None,
        mode=payload.mode,
        provider=payload.provider,
        model=payload.model,
        idempotency_key=idempotency_key,
    )
    return accepted_root_response(start)


__all__ = ["router"]
