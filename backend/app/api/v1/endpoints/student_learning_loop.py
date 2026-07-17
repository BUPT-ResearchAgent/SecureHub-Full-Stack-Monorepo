# Status: real

"""Student-owned path replan and resource-feedback HTTP adapters.

The adapters only translate authenticated, course-scoped requests to the
durable learning-loop service.  Resource feedback always starts the existing
``resource_generate_v1`` root; it never fabricates a version in the browser
or marks a queued retry as regenerated.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.v1.endpoints.workflow_adapter import start_product_workflow, workflow_service
from app.db.models.resource.generated_resource import GeneratedResource
from app.db.seeds._constants import resolve_course_product
from app.deps import RequiredCurrentUserDep, SessionDep
from app.schemas.student_learning_loop import (
    PathReplanCandidateDTO,
    PathReplanCreateRequest,
    PathReplanDecisionRequest,
    ResourceFeedbackRequest,
    ResourceFeedbackSubmitResponse,
    ResourceRecommendationDTO,
    ResourceRecommendationDecisionRequest,
    StudentLearningLoopDTO,
)
from app.services.learning.student_learning_loop_service import (
    StudentLearningLoopError,
    StudentLearningLoopService,
)


router = APIRouter()


def _ready_course_id(course_id: str) -> UUID:
    product = resolve_course_product(course_id)
    if product is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "COURSE_NOT_FOUND", "message": "课程不存在或链接已失效。"},
        )
    if product.content_status != "ready":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "COURSE_CONTENT_NOT_READY",
                "message": product.unavailable_reason or "当前课程尚未开放真实学习闭环。",
            },
        )
    return product.id


def _raise_learning_loop_error(exc: StudentLearningLoopError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    ) from exc


def _workflow_error_detail(exc: HTTPException) -> tuple[str, str]:
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code") or "WORKFLOW_START_FAILED")
        message = str(detail.get("message") or "资源重生成请求无法启动。")
        return code, message
    return "WORKFLOW_START_FAILED", str(detail or "资源重生成请求无法启动。")


def _feedback_retry_query(resource: GeneratedResource, feedback_kinds: list[str], comment: str | None) -> str:
    labels = {
        "too_difficult": "降低不必要的理解门槛并补充前置解释",
        "too_shallow": "补充可验证的防御性推理深度",
        "missing_example": "增加安全、不可滥用的防御案例",
        "want_diagram": "补充结构化图解或关系说明",
        "want_practice": "补充可验收的防御性练习",
    }
    requested = "；".join(labels.get(kind, kind) for kind in feedback_kinds)
    suffix = f" 学生补充：{comment}" if comment else ""
    return (
        f"根据学生对《{resource.title}》的结构化学习反馈重生成同一课程资源。"
        f"保持原有知识点、Evidence、质量门和安全边界，重点调整：{requested}。{suffix}"
    )


@router.get(
    "/courses/{course_id}/learning-loop",
    response_model=StudentLearningLoopDTO,
)
async def get_student_learning_loop(
    course_id: str,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> StudentLearningLoopDTO:
    canonical_course_id = _ready_course_id(course_id)
    service = StudentLearningLoopService(session)
    try:
        result = await service.overview(actor=user, course_id=canonical_course_id)
        # Overview reconciles terminal retry facts, so persist that projection
        # before the browser displays a new version or a retained-old-version state.
        await session.commit()
        return result
    except StudentLearningLoopError as exc:
        await session.rollback()
        _raise_learning_loop_error(exc)


@router.post(
    "/courses/{course_id}/learning-loop/replan-candidates",
    response_model=PathReplanCandidateDTO,
)
async def create_student_replan_candidate(
    course_id: str,
    payload: PathReplanCreateRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> PathReplanCandidateDTO:
    canonical_course_id = _ready_course_id(course_id)
    service = StudentLearningLoopService(session)
    try:
        candidate = await service.create_candidate(
            actor=user,
            course_id=canonical_course_id,
            trigger_event_id=payload.trigger_event_id,
            assessment_workflow_run_id=payload.assessment_workflow_run_id,
        )
        await session.commit()
        return candidate
    except StudentLearningLoopError as exc:
        await session.rollback()
        _raise_learning_loop_error(exc)


@router.post(
    "/courses/{course_id}/learning-loop/replan-candidates/{candidate_id}/decision",
    response_model=PathReplanCandidateDTO,
)
async def decide_student_replan_candidate(
    course_id: str,
    candidate_id: UUID,
    payload: PathReplanDecisionRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> PathReplanCandidateDTO:
    canonical_course_id = _ready_course_id(course_id)
    service = StudentLearningLoopService(session)
    try:
        candidate = await service.decide_candidate(
            actor=user,
            course_id=canonical_course_id,
            candidate_id=candidate_id,
            decision=payload.decision,
            reason=payload.reason,
        )
        await session.commit()
        return candidate
    except StudentLearningLoopError as exc:
        await session.rollback()
        _raise_learning_loop_error(exc)


@router.post(
    "/courses/{course_id}/learning-loop/recommendations/{recommendation_id}/decision",
    response_model=ResourceRecommendationDTO,
)
async def decide_student_resource_recommendation(
    course_id: str,
    recommendation_id: UUID,
    payload: ResourceRecommendationDecisionRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> ResourceRecommendationDTO:
    canonical_course_id = _ready_course_id(course_id)
    service = StudentLearningLoopService(session)
    try:
        recommendation = await service.decide_recommendation(
            actor=user,
            course_id=canonical_course_id,
            recommendation_id=recommendation_id,
            decision=payload.decision,
            reason=payload.reason,
        )
        await session.commit()
        return recommendation
    except StudentLearningLoopError as exc:
        await session.rollback()
        _raise_learning_loop_error(exc)


@router.post(
    "/courses/{course_id}/learning-loop/resources/{resource_id}/feedback",
    response_model=ResourceFeedbackSubmitResponse,
    status_code=202,
)
async def submit_student_resource_feedback(
    course_id: str,
    resource_id: UUID,
    payload: ResourceFeedbackRequest,
    request: Request,
    session: SessionDep,
    user: RequiredCurrentUserDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ResourceFeedbackSubmitResponse | JSONResponse:
    """Persist feedback first, then attach one shared durable retry root."""

    canonical_course_id = _ready_course_id(course_id)
    service = StudentLearningLoopService(session)
    try:
        feedback = await service.create_feedback(
            actor=user,
            course_id=canonical_course_id,
            resource_id=resource_id,
            feedback_kinds=payload.feedback_kinds,
            comment=payload.comment,
            recommendation_id=payload.recommendation_id,
        )
        # A feedback record is an auditable learning event even when the
        # provider is unavailable.  Commit it before starting a separate
        # workflow-service transaction.
        await session.commit()
    except StudentLearningLoopError as exc:
        await session.rollback()
        _raise_learning_loop_error(exc)

    resource = await session.get(GeneratedResource, feedback.resource_id)
    if resource is None:
        # This cannot normally occur because create_feedback checked scope,
        # but never launch a root when the verified parent disappeared.
        failed = await service.mark_feedback_failed(
            actor=user,
            course_id=canonical_course_id,
            feedback_id=feedback.id,
            code="RESOURCE_PARENT_MISSING",
            message="资源反馈已保存，但原资源已不可读取；未启动重生成。",
        )
        await session.commit()
        raise HTTPException(
            status_code=409,
            detail={"code": "RESOURCE_PARENT_MISSING", "message": failed.outcome["message"]},
        )

    product = resolve_course_product(canonical_course_id)
    if product is None:  # Defensive: the canonical id was validated above.
        raise HTTPException(status_code=404, detail={"code": "COURSE_NOT_FOUND", "message": "课程不存在或链接已失效。"})
    options: dict[str, Any] = {
        "parent_resource_id": str(resource.id),
        "retry_source_resource_id": str(resource.id),
        "retry_source_workflow_run_id": str(resource.workflow_run_id) if resource.workflow_run_id else None,
        "retry_source_step_attempt_id": str(resource.step_attempt_id) if resource.step_attempt_id else None,
        "student_feedback": {
            "feedback_id": str(feedback.id),
            "feedback_kinds": list(feedback.feedback_kinds or []),
            "comment": feedback.comment,
        },
    }
    try:
        start = await start_product_workflow(
            workflow_service(request),
            workflow="resource_generate_v1",
            actor_user_id=user.id,
            course_id=canonical_course_id,
            input_payload={
                "resource_type": resource.resource_type,
                "kp_id": str(resource.kp_id) if resource.kp_id else None,
                "query": _feedback_retry_query(resource, list(feedback.feedback_kinds or []), feedback.comment),
                "options": options,
                "domain": product.domain,
            },
            mode="real",
            provider=payload.provider,
            model=payload.model,
            idempotency_key=idempotency_key or f"student-feedback:{feedback.id}",
        )
    except HTTPException as exc:
        code, message = _workflow_error_detail(exc)
        if exc.status_code == 503 or code == "PROVIDER_UNAVAILABLE":
            updated = await service.mark_feedback_unavailable(
                actor=user,
                course_id=canonical_course_id,
                feedback_id=feedback.id,
                code=code,
                message=message,
            )
            await session.commit()
            await session.refresh(updated)
            body = ResourceFeedbackSubmitResponse(
                feedback=service.feedback_dto(updated),
                workflow=None,
            ).model_dump(mode="json")
            body["detail"] = {"code": "PROVIDER_UNAVAILABLE", "message": message}
            return JSONResponse(status_code=503, content=body)
        updated = await service.mark_feedback_failed(
            actor=user,
            course_id=canonical_course_id,
            feedback_id=feedback.id,
            code=code,
            message=message,
        )
        await session.commit()
        await session.refresh(updated)
        raise HTTPException(status_code=exc.status_code, detail={"code": code, "message": updated.outcome["message"]}) from exc

    attached = await service.attach_retry_run(
        actor=user,
        course_id=canonical_course_id,
        feedback_id=feedback.id,
        workflow_run_id=start.run_id,
    )
    await session.commit()
    await session.refresh(attached)
    return ResourceFeedbackSubmitResponse(
        feedback=service.feedback_dto(attached),
        workflow=start.model_dump(mode="json"),
    )


__all__ = [
    "router",
    "create_student_replan_candidate",
    "decide_student_replan_candidate",
    "decide_student_resource_recommendation",
    "get_student_learning_loop",
    "submit_student_resource_feedback",
]
