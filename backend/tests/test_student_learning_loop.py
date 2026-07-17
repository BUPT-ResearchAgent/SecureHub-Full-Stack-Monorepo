# Status: real

"""Focused contracts for durable student path and resource-feedback loops."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.v1.endpoints import student_learning_loop as learning_loop_endpoint
from app.db.models.identity.user import User
from app.db.models.learning.learning_replan import CourseResourceRecommendation, LearningPathVersion
from app.db.models.resource.generated_resource import GeneratedResource
from app.db.models.resource.resource_feedback import ResourceFeedback
from app.db.models.resource.resource_version import ResourceVersion
from app.db.models.workflow_runtime import WorkflowRun
from app.db.seeds._constants import COURSE_WEBSEC_ID
from app.db.seeds.seed_showcase_course import _id, _student_id, run
from app.schemas.agent_control import WorkflowRunStartResponse
from app.schemas.student_learning_loop import (
    PathReplanCreateRequest,
    PathReplanDecisionRequest,
    ResourceFeedbackRequest,
)
from app.services.learning.student_learning_loop_service import (
    StudentLearningLoopError,
    StudentLearningLoopService,
)


@pytest.mark.anyio
async def test_seeded_loop_is_student_scoped_and_preserves_baseline(sqlite_session) -> None:
    await run(sqlite_session)
    hanyue = await sqlite_session.get(User, _student_id("hanyue"))
    qinglan = await sqlite_session.get(User, _student_id("qinglan"))
    assert hanyue is not None and qinglan is not None

    overview = await learning_loop_endpoint.get_student_learning_loop(
        course_id=str(COURSE_WEBSEC_ID), session=sqlite_session, user=hanyue
    )
    assert len(overview.path_versions) == 1
    assert overview.path_versions[0].kind == "baseline"
    assert overview.candidates and overview.candidates[0].status == "pending"
    assert overview.candidates[0].trigger_label.startswith("学习事件")
    assert overview.recommendations and overview.recommendations[0].status == "scheduled"

    with pytest.raises(HTTPException) as denied:
        await learning_loop_endpoint.decide_student_replan_candidate(
            course_id=str(COURSE_WEBSEC_ID),
            candidate_id=overview.candidates[0].id,
            payload=PathReplanDecisionRequest(decision="accept"),
            session=sqlite_session,
            user=qinglan,
        )
    assert denied.value.status_code == 404
    assert denied.value.detail["code"] == "REPLAN_CANDIDATE_NOT_FOUND"


@pytest.mark.anyio
async def test_candidate_decisions_create_versions_without_overwriting_history(sqlite_session) -> None:
    await run(sqlite_session)
    actor = await sqlite_session.get(User, _student_id("qinglan"))
    outsider = await sqlite_session.get(User, _student_id("hanyue"))
    assert actor is not None and outsider is not None

    candidate = await learning_loop_endpoint.create_student_replan_candidate(
        course_id=str(COURSE_WEBSEC_ID),
        payload=PathReplanCreateRequest(),
        session=sqlite_session,
        user=actor,
    )
    deferred = await learning_loop_endpoint.decide_student_replan_candidate(
        course_id=str(COURSE_WEBSEC_ID),
        candidate_id=candidate.id,
        payload=PathReplanDecisionRequest(decision="defer"),
        session=sqlite_session,
        user=actor,
    )
    assert deferred.status == "deferred"

    with pytest.raises(HTTPException) as forged:
        await learning_loop_endpoint.decide_student_replan_candidate(
            course_id=str(COURSE_WEBSEC_ID),
            candidate_id=uuid4(),
            payload=PathReplanDecisionRequest(decision="accept"),
            session=sqlite_session,
            user=actor,
        )
    assert forged.value.status_code == 404

    accepted = await learning_loop_endpoint.decide_student_replan_candidate(
        course_id=str(COURSE_WEBSEC_ID),
        candidate_id=candidate.id,
        payload=PathReplanDecisionRequest(decision="accept"),
        session=sqlite_session,
        user=actor,
    )
    assert accepted.status == "accepted"
    assert accepted.accepted_version_no == 2

    versions = list(
        (
            await sqlite_session.execute(
                select(LearningPathVersion)
                .where(LearningPathVersion.user_id == actor.id, LearningPathVersion.course_id == COURSE_WEBSEC_ID)
                .order_by(LearningPathVersion.version_no)
            )
        ).scalars()
    )
    assert [(row.version_no, row.state, row.kind) for row in versions] == [
        (1, "historical", "baseline"),
        (2, "active", "replan"),
    ]
    recommendations = list(
        (
            await sqlite_session.execute(
                select(CourseResourceRecommendation).where(CourseResourceRecommendation.student_id == actor.id)
            )
        ).scalars()
    )
    assert recommendations

    reverted = await learning_loop_endpoint.decide_student_replan_candidate(
        course_id=str(COURSE_WEBSEC_ID),
        candidate_id=candidate.id,
        payload=PathReplanDecisionRequest(decision="revert"),
        session=sqlite_session,
        user=actor,
    )
    assert reverted.status == "reverted"
    active = await sqlite_session.scalar(
        select(LearningPathVersion).where(
            LearningPathVersion.user_id == actor.id,
            LearningPathVersion.course_id == COURSE_WEBSEC_ID,
            LearningPathVersion.state == "active",
        )
    )
    assert active is not None and active.version_no == 3 and active.kind == "revert"

    with pytest.raises(HTTPException) as cross_student:
        await learning_loop_endpoint.decide_student_replan_candidate(
            course_id=str(COURSE_WEBSEC_ID),
            candidate_id=candidate.id,
            payload=PathReplanDecisionRequest(decision="revert"),
            session=sqlite_session,
            user=outsider,
        )
    assert cross_student.value.status_code == 404


@pytest.mark.anyio
async def test_feedback_reconciles_only_real_child_lineage_and_rejects_cross_student_resource(sqlite_session) -> None:
    await run(sqlite_session)
    actor = await sqlite_session.get(User, _student_id("qinglan"))
    other = await sqlite_session.get(User, _student_id("hanyue"))
    assert actor is not None and other is not None
    service = StudentLearningLoopService(sqlite_session)
    original = await sqlite_session.get(GeneratedResource, _id("resource", "input-validation-guide-v2"))
    assert original is not None

    private_resource = GeneratedResource(
        id=uuid4(),
        user_id=other.id,
        course_id=COURSE_WEBSEC_ID,
        kp_id=original.kp_id,
        agent_run_id=None,
        workflow_run_id=None,
        step_attempt_id=None,
        parent_resource_id=None,
        lineage_root_id=None,
        version=1,
        resource_type="doc",
        title="其他学生的私有资源",
        content={"body": "私有学习笔记"},
        object_key=None,
        evidence_chunk_ids=[],
        quality_score=0.8,
        status="ready",
        metadata_={},
    )
    sqlite_session.add(private_resource)
    await sqlite_session.flush()
    with pytest.raises(StudentLearningLoopError) as inaccessible:
        await service.create_feedback(
            actor=actor,
            course_id=COURSE_WEBSEC_ID,
            resource_id=private_resource.id,
            feedback_kinds=["too_difficult"],
            comment=None,
            recommendation_id=None,
        )
    assert inaccessible.value.code == "RESOURCE_NOT_ACCESSIBLE"

    feedback = await service.create_feedback(
        actor=actor,
        course_id=COURSE_WEBSEC_ID,
        resource_id=original.id,
        feedback_kinds=["missing_example", "want_practice"],
        comment="补充参数化查询的防御性验证检查点。",
        recommendation_id=None,
    )
    retry_run = WorkflowRun(
        id=uuid4(),
        workflow_name="resource_generate_v1",
        user_id=actor.id,
        status="succeeded",
        input_payload={"course_id": str(COURSE_WEBSEC_ID)},
        finished_at=datetime.now(UTC),
    )
    sqlite_session.add(retry_run)
    child = GeneratedResource(
        id=uuid4(),
        user_id=actor.id,
        course_id=COURSE_WEBSEC_ID,
        kp_id=original.kp_id,
        agent_run_id=None,
        workflow_run_id=retry_run.id,
        step_attempt_id=None,
        parent_resource_id=original.id,
        lineage_root_id=original.lineage_root_id or original.id,
        version=original.version + 1,
        resource_type=original.resource_type,
        title="输入验证与参数化查询防御学习单（学生反馈版）",
        content={"body": "保留原有防御边界，并补充参数化查询验证检查点。"},
        object_key=None,
        evidence_chunk_ids=list(original.evidence_chunk_ids or []),
        quality_score=0.93,
        status="ready",
        metadata_={"source_kind": "real", "quality_state": "accepted"},
    )
    sqlite_session.add(child)
    sqlite_session.add(
        ResourceVersion(
            id=uuid4(),
            resource_id=child.id,
            version=child.version,
            content=child.content,
            object_key=None,
            change_summary="根据结构化学生反馈补充防御性案例与验收点。",
            metadata_={"feedback": True},
        )
    )
    await sqlite_session.flush()
    await service.attach_retry_run(
        actor=actor,
        course_id=COURSE_WEBSEC_ID,
        feedback_id=feedback.id,
        workflow_run_id=retry_run.id,
    )
    await service.reconcile_feedback(actor=actor, course_id=COURSE_WEBSEC_ID)
    assert feedback.status == "regenerated"
    assert feedback.resulting_resource_id == child.id

    overview = await service.overview(actor=actor, course_id=COURSE_WEBSEC_ID)
    lineage = next(item for item in overview.resource_lineages if item.lineage_root_id == (original.lineage_root_id or original.id))
    assert lineage.versions[0].resource_id == child.id
    assert lineage.versions[0].change_summary
    assert any(item.resource_id == child.id for item in overview.recommendations)


@pytest.mark.anyio
async def test_feedback_endpoint_starts_shared_root_and_persists_provider_unavailable(sqlite_session, monkeypatch) -> None:
    await run(sqlite_session)
    actor = await sqlite_session.get(User, _student_id("qinglan"))
    assert actor is not None
    resource = await sqlite_session.get(GeneratedResource, _id("resource", "input-validation-guide-v2"))
    assert resource is not None

    run_id = uuid4()
    sqlite_session.add(
        WorkflowRun(
            id=run_id,
            workflow_name="resource_generate_v1",
            user_id=actor.id,
            status="queued",
            input_payload={"course_id": str(COURSE_WEBSEC_ID)},
        )
    )
    await sqlite_session.commit()
    captured: dict[str, object] = {}

    async def fake_start(_service, **kwargs):
        captured.update(kwargs)
        return WorkflowRunStartResponse(
            run_id=run_id,
            workflow="resource_generate_v1",
            status="queued",
            events_url=f"/api/v1/workflow-runs/{run_id}/events",
            cancel_url=f"/api/v1/workflow-runs/{run_id}/cancel",
            mode="real",
        )

    monkeypatch.setattr(learning_loop_endpoint, "workflow_service", lambda _request: object())
    monkeypatch.setattr(learning_loop_endpoint, "start_product_workflow", fake_start)
    result = await learning_loop_endpoint.submit_student_resource_feedback(
        course_id=str(COURSE_WEBSEC_ID),
        resource_id=resource.id,
        payload=ResourceFeedbackRequest(feedback_kinds=["want_diagram"]),
        request=object(),
        session=sqlite_session,
        user=actor,
    )
    assert result.feedback.status == "retry_requested"
    assert captured["workflow"] == "resource_generate_v1"
    assert captured["input_payload"]["options"]["parent_resource_id"] == str(resource.id)

    async def unavailable_start(_service, **kwargs):
        raise HTTPException(status_code=503, detail={"code": "PROVIDER_UNAVAILABLE", "message": "Provider 未配置"})

    monkeypatch.setattr(learning_loop_endpoint, "start_product_workflow", unavailable_start)
    unavailable = await learning_loop_endpoint.submit_student_resource_feedback(
        course_id=str(COURSE_WEBSEC_ID),
        resource_id=resource.id,
        payload=ResourceFeedbackRequest(feedback_kinds=["want_practice"]),
        request=object(),
        session=sqlite_session,
        user=actor,
    )
    assert isinstance(unavailable, JSONResponse)
    assert unavailable.status_code == 503
    body = json.loads(unavailable.body)
    assert body["feedback"]["status"] == "provider_unavailable"
    assert body["detail"]["code"] == "PROVIDER_UNAVAILABLE"
    persisted = list(
        (
            await sqlite_session.execute(
                select(ResourceFeedback).where(ResourceFeedback.course_id == COURSE_WEBSEC_ID)
            )
        ).scalars()
    )
    assert any(
        row.feedback_kinds == ["want_practice"] and row.status == "provider_unavailable"
        for row in persisted
    )
