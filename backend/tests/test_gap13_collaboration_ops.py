# Status: real

"""Focused T4 evidence for signals, interpersonal messages, and admin RBAC."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models.agent.agent_run import AgentRun
from app.db.models.collaboration.collaboration import CourseUpdateSuggestion, Message
from app.db.models.education.education_domain import GovernanceAuditEvent
from app.db.models.governance.governance import RoleDefinition, UserRoleGrant
from app.db.models.identity.user import User
from app.db.models.knowledge.course import Course
from app.db.models.knowledge.document import Document
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.db.models.teaching.teacher_production import CourseAssetGovernance, CourseDocumentBinding
from app.db.models.workflow_runtime import WorkflowEvidenceSnapshot, WorkflowRun
from app.db.seeds._constants import COURSE_WEBSEC_ID, DEMO_USER_ID, agent_id, skill_id
from app.db.seeds.seed_agent_skills import run as seed_agent_skills
from app.db.seeds.seed_agents import run as seed_agents
from app.db.seeds.seed_course_websec import run as seed_course_websec
from app.db.seeds.seed_demo_user import run as seed_demo_user
from app.db.seeds.seed_education_domain import DEMO_COURSE_TEACHER_ID, DEMO_TEACHING_CLASS_ID, run as seed_education_domain
from app.schemas.collaboration import (
    CourseUpdateDecisionRequest,
    CourseUpdateImpactRequest,
    CreateCourseUpdateSuggestionRequest,
    ExternalSignalIngestRequest,
    MessageSendRequest,
    RecallMessageRequest,
)
from app.schemas.governance import CourseResourceGovernanceRequest, RoleGrantRequest, RoleRevokeRequest
from app.services.collaboration.collaboration_service import CollaborationDomainError, CollaborationService
from app.services.governance.governance_service import GovernanceDomainError, GovernanceService


@pytest.mark.anyio
async def test_gap13_collaboration_ops_is_evidence_bound_scoped_and_audited(sqlite_session) -> None:
    await seed_demo_user(sqlite_session)
    await seed_agents(sqlite_session)
    await seed_agent_skills(sqlite_session)
    await seed_course_websec(sqlite_session)
    await seed_education_domain(sqlite_session)
    await sqlite_session.commit()

    teacher = await sqlite_session.get(User, DEMO_COURSE_TEACHER_ID)
    student = await sqlite_session.get(User, DEMO_USER_ID)
    assert teacher is not None and student is not None
    document = (
        await sqlite_session.execute(select(Document).where(Document.domain == "course_websec"))
    ).scalars().first()
    assert document is not None

    workflow = WorkflowRun(
        id=uuid4(),
        workflow_name="gap13-hot-signal",
        user_id=teacher.id,
        status="succeeded",
        input_payload={},
        output_ref={},
        budget={},
        error={},
    )
    sqlite_session.add(workflow)
    await sqlite_session.flush()
    run = AgentRun(
        id=uuid4(),
        workflow_name="gap13-hot-signal",
        user_id=teacher.id,
        agent_id=agent_id("hot_analyst"),
        skill_id=skill_id("hot_analyst", "AnalyzeHotEvent"),
        workflow_run_id=workflow.id,
        status="succeeded",
        input_summary={},
        output_summary={"summary": "真实热点证据提示补充 SSRF 防护复盘。"},
        evidence_chunk_ids=["gap13-hot-chunk"],  # type: ignore[list-item]
        token_usage={},
    )
    sqlite_session.add(run)
    await sqlite_session.flush()
    evidence = WorkflowEvidenceSnapshot(
        id=uuid4(),
        workflow_run_id=workflow.id,
        agent_run_id=run.id,
        chunk_id="gap13-hot-chunk",
        document_id=str(document.id),
        chunk_version="v1",
        content_digest="gap13-hot-evidence",
        excerpt="热点事件证据摘录",
        citation={"document_id": str(document.id)},
        source={},
        rights={},
    )
    sqlite_session.add(evidence)
    await sqlite_session.flush()

    collaboration = CollaborationService(sqlite_session)
    signal = await collaboration.ingest_external_signal(
        actor=teacher,
        payload=ExternalSignalIngestRequest(
            kind="hot",
            source_document_id=document.id,
            agent_run_id=run.id,
            evidence_snapshot_id=evidence.id,
            title="热点事件到课程更新候选",
        ),
    )
    assert signal.status == "validated"
    assert signal.summary == "真实热点证据提示补充 SSRF 防护复盘。"

    node_id = await sqlite_session.scalar(
        select(KnowledgeNode.id).where(KnowledgeNode.course_id == COURSE_WEBSEC_ID).limit(1)
    )
    assert node_id is not None
    course = await sqlite_session.get(Course, COURSE_WEBSEC_ID)
    assert course is not None
    before_title = course.title
    suggestion = await collaboration.create_course_update_suggestion(
        actor=teacher,
        payload=CreateCourseUpdateSuggestionRequest(
            course_id=COURSE_WEBSEC_ID,
            signal_id=signal.id,
            title="补充 SSRF 风险案例复盘",
            diff={"modules": [{"op": "append_activity", "value": "基于证据的 SSRF 防护案例复盘"}]},
            impacts=[
                CourseUpdateImpactRequest(
                    knowledge_node_id=node_id,
                    impact_type="emphasize",
                    rationale="热点证据指向服务端请求边界的教学缺口。",
                )
            ],
            reason="固定热点 Agent 的证据建议进入教师决策队列。",
        ),
    )
    assert suggestion.status == "pending_teacher_decision"
    adopted = await collaboration.decide_course_update_suggestion(
        actor=teacher,
        suggestion_id=suggestion.id,
        payload=CourseUpdateDecisionRequest(decision="adopt", reason="教师确认纳入下次课程修订。"),
    )
    assert adopted.status == "adopted"
    assert adopted.decision is not None and adopted.decision.decision == "adopt"
    refreshed_course = await sqlite_session.get(Course, COURSE_WEBSEC_ID)
    assert refreshed_course is not None and refreshed_course.title == before_title
    assert await sqlite_session.scalar(select(CourseUpdateSuggestion.id)) == suggestion.id

    message_payload = MessageSendRequest(
        scope_type="class",
        course_id=COURSE_WEBSEC_ID,
        teaching_class_id=DEMO_TEACHING_CLASS_ID,
        subject="SSRF 复盘通知",
        body="请在下一节课前完成 Evidence 对照阅读。",
        idempotency_key="gap13-message-001",
    )
    sent = await collaboration.send_message(actor=teacher, payload=message_payload)
    replay = await collaboration.send_message(actor=teacher, payload=message_payload)
    assert sent.id == replay.id
    assert sent.delivery_counts == {"unread": 1}
    inbox = await collaboration.list_inbox(actor=student)
    assert [(row.id, row.delivery_state) for row in inbox.items] == [(sent.id, "unread")]
    read = await collaboration.mark_message_read(actor=student, message_id=sent.id)
    assert read.delivery_state == "read"
    refreshed_inbox = await collaboration.list_inbox(actor=student)
    assert refreshed_inbox.items[0].delivery_state == "read"
    recalled = await collaboration.recall_message(
        actor=teacher,
        message_id=sent.id,
        payload=RecallMessageRequest(reason="教师更正公告范围"),
    )
    assert recalled.status == "recalled"
    with pytest.raises(CollaborationDomainError) as unsafe:
        await collaboration.send_message(
            actor=teacher,
            payload=MessageSendRequest(
                scope_type="class",
                course_id=COURSE_WEBSEC_ID,
                teaching_class_id=DEMO_TEACHING_CLASS_ID,
                subject="不安全内容",
                body="<script>alert(1)</script>",
                idempotency_key="gap13-message-unsafe",
            ),
        )
    assert unsafe.value.code == "MESSAGE_CONTENT_UNSAFE"
    rejected = await sqlite_session.scalar(
        select(Message).where(Message.idempotency_key == "gap13-message-unsafe")
    )
    assert rejected is not None and rejected.safety_state == "rejected"

    governance = GovernanceService(sqlite_session)
    await governance.ensure_default_definitions()
    administrator = await sqlite_session.scalar(
        select(RoleDefinition).where(RoleDefinition.code == "administrator", RoleDefinition.status == "active")
    )
    assert administrator is not None
    sqlite_session.add(
        UserRoleGrant(
            id=uuid4(),
            user_id=teacher.id,
            role_id=administrator.id,
            granted_by=teacher.id,
            granted_at=datetime.now(UTC),
            status="active",
            reason="focused test bootstrap administrator",
        )
    )
    await sqlite_session.flush()
    with pytest.raises(GovernanceDomainError) as student_admin_denied:
        await governance.get_kpi_dashboard(actor=student)
    assert student_admin_denied.value.code == "ADMIN_ROLE_REQUIRED"
    dashboard = await governance.get_kpi_dashboard(actor=teacher)
    assert {item.code for item in dashboard.items} >= {
        "active_teaching_classes",
        "enrolled_students",
        "pending_course_updates",
        "sent_messages_7d",
    }
    with pytest.raises(GovernanceDomainError) as last_admin:
        await governance.revoke_role(
            actor=teacher,
            grant_id=(await sqlite_session.scalar(select(UserRoleGrant.id).where(UserRoleGrant.user_id == teacher.id))),
            payload=RoleRevokeRequest(reason="不允许撤销最后管理员"),
        )
    assert last_admin.value.code == "LAST_ADMIN_PROTECTED"
    granted = await governance.grant_role(
        actor=teacher,
        payload=RoleGrantRequest(
            user_id=student.id, role_code="administrator", reason="双人治理恢复路径演练"
        ),
    )
    assert granted.status == "active" and granted.user_id == student.id

    asset = CourseAssetGovernance(
        id=uuid4(),
        binding_id=uuid4(),
        owner_teacher_id=teacher.id,
        version_no=1,
        state="ready",
    )
    binding = CourseDocumentBinding(
        id=asset.binding_id,
        course_id=COURSE_WEBSEC_ID,
        document_id=document.id,
        bound_by=teacher.id,
        purpose="teaching_material",
        status="active",
    )
    sqlite_session.add(binding)
    sqlite_session.add(asset)
    await sqlite_session.flush()
    resource = await governance.govern_course_resource(
        actor=teacher,
        asset_id=asset.id,
        payload=CourseResourceGovernanceRequest(action="restrict", reason="证据来源复核期间限制访问"),
    )
    assert resource.governance_state == "restricted"
    assert resource.asset_state == "withdrawn"

    events = (await sqlite_session.execute(select(GovernanceAuditEvent))).scalars().all()
    assert any(row.action == "course_update_suggestion.decide" for row in events)
    assert any(row.action == "message.send" for row in events)
    assert any(row.action == "message.read" for row in events)
    assert any(row.action == "course_resource.govern" for row in events)
