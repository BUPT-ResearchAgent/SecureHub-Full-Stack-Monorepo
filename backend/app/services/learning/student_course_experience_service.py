# Status: real

"""Current-student projection for the controlled WEBSEC-101 learning view.

The service composes the existing education, learning, resource, teaching,
and evidence authorities.  It deliberately has no caller-provided student or
class selector, so a student cannot use this read model to inspect another
learner's submissions, grades, group, or evidence records.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import fmean
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.collaboration.collaboration import Message, MessageDelivery
from app.db.models.education.education_domain import (
    CourseEnrollment,
    StudentGroup,
    StudentGroupMember,
    TeachingClass,
)
from app.db.models.identity.user import User
from app.db.models.identity.user_capability import UserCapability
from app.db.models.identity.user_profile import UserProfile
from app.db.models.knowledge.chunk import Chunk
from app.db.models.knowledge.document import Document
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.db.models.learning.learning_event import LearningEvent
from app.db.models.learning.learning_path import LearningPath
from app.db.models.learning.learning_task import LearningTask
from app.db.models.learning.quiz_attempt import QuizAttempt
from app.db.models.learning.quiz_item import QuizItem
from app.db.models.resource.generated_resource import GeneratedResource
from app.db.models.teaching.teacher_production import (
    Assessment,
    AssessmentAssignment,
    AssessmentGradeDecision,
    AssessmentItem,
    AssessmentSubmission,
    AssessmentVersion,
)
from app.db.models.workflow_runtime import WorkflowEvidenceSnapshot
from app.schemas.student_course_experience import (
    StudentCourseAssessmentDTO,
    StudentCourseAssignmentDTO,
    StudentCourseCapabilityDTO,
    StudentCourseDemoAssessmentDraftDTO,
    StudentCourseEvidenceDTO,
    StudentCourseExperienceDTO,
    StudentCourseKnowledgeMetricDTO,
    StudentCourseProfileDTO,
    StudentCourseResourceDTO,
    StudentCourseTaskDTO,
    StudentCourseTutorExchangeDTO,
    StudentCourseUpdateDTO,
)


RESOURCE_TYPES = {"doc", "ppt", "mindmap", "quiz", "lab", "readings", "video"}
RESOURCE_TYPE_ORDER = {name: index for index, name in enumerate(("doc", "ppt", "mindmap", "quiz", "lab", "readings", "video"))}
CAPABILITY_LABELS = {
    "web_security": "Web 安全综合能力",
    "http_security": "HTTP 安全边界",
    "authentication": "认证与会话",
    "input_validation": "输入验证",
    "xss_defense": "XSS 防御",
    "secure_coding": "安全编码",
    "learning_progress": "学习进度",
}


class StudentCourseExperienceError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 403) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class StudentCourseExperienceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_experience(
        self, *, actor: User, course_id: UUID
    ) -> StudentCourseExperienceDTO:
        if actor.role != "student":
            raise StudentCourseExperienceError(
                "STUDENT_ROLE_REQUIRED",
                "当前课程学习视图仅面向已登录的学生账户。",
            )

        enrollment = await self.session.scalar(
            select(CourseEnrollment)
            .where(
                CourseEnrollment.course_id == course_id,
                CourseEnrollment.student_id == actor.id,
                CourseEnrollment.status.in_(("enrolled", "completed")),
            )
            .order_by(CourseEnrollment.enrolled_at.desc())
            .limit(1)
        )
        if enrollment is None:
            raise StudentCourseExperienceError(
                "COURSE_ENROLLMENT_REQUIRED",
                "尚未检测到当前账户在该课程的有效选课记录；请使用课程花名账户登录或联系教师确认选课。",
            )

        teaching_class = (
            await self.session.get(TeachingClass, enrollment.teaching_class_id)
            if enrollment.teaching_class_id is not None
            else None
        )
        if teaching_class is None:
            raise StudentCourseExperienceError(
                "TEACHING_CLASS_REQUIRED",
                "当前选课缺少有效教学班归属，暂不能展示班级作业和课程更新。",
            )

        group = await self.session.scalar(
            select(StudentGroup)
            .join(StudentGroupMember, StudentGroupMember.group_id == StudentGroup.id)
            .where(
                StudentGroupMember.student_id == actor.id,
                StudentGroupMember.status == "active",
                StudentGroup.teaching_class_id == teaching_class.id,
                StudentGroup.status == "active",
            )
            .limit(1)
        )
        profile = await self.session.get(UserProfile, actor.id)
        profile_dimensions = dict(profile.dimensions or {}) if profile is not None else {}
        capabilities = await self._capabilities(actor.id)
        tasks, next_task = await self._tasks(actor.id, course_id)
        resources = await self._resources(actor.id, course_id)
        assignments = await self._assignments(
            actor_id=actor.id,
            course_id=course_id,
            teaching_class_id=teaching_class.id,
            group_id=group.id if group is not None else None,
        )
        updates = await self._updates(actor.id, course_id)
        tutor_exchanges = await self._tutor_exchanges(actor.id)
        assessment_demo_draft = await self._assessment_demo_draft(
            user_id=actor.id,
            course_id=course_id,
            assignments=assignments,
        )
        assessment = await self._assessment(actor.id, course_id)

        completed_count = sum(task.status == "done" for task in tasks)
        task_progress = round(completed_count / len(tasks) * 100, 1) if tasks else 0.0
        profile_progress = _as_score(profile_dimensions.get("current_progress"))
        progress_percent = task_progress if tasks else round(profile_progress * 100, 1)
        missing: list[str] = []
        if not tasks:
            missing.append("个性化学习路径")
        if {resource.resource_type for resource in resources} != RESOURCE_TYPES:
            missing.append("七类课程资源")
        if not assignments:
            missing.append("已发布或已撤回的课程作业")
        if not tutor_exchanges:
            missing.append("可恢复的课程辅导记录")
        if assessment.scored_attempt_count == 0:
            missing.append("可评分学习记录")
        next_step = next_task.title if next_task is not None else str(
            profile_dimensions.get("recommended_next_step") or "查看课程资源与近期作业。"
        )

        return StudentCourseExperienceDTO(
            course_id=course_id,
            course_code="WEBSEC-101",
            data_status="ready" if not missing else "incomplete",
            missing_dependencies=missing,
            profile=StudentCourseProfileDTO(
                display_name=actor.display_name,
                teaching_class_name=teaching_class.name,
                group_name=group.name if group is not None else None,
                learning_story=str(profile_dimensions.get("learning_story") or "course_learning"),
                learning_story_summary=str(
                    profile_dimensions.get("learning_story_summary") or "当前学习状态由已持久化的课程记录投影。"
                ),
                source_boundary=str(
                    profile_dimensions.get("source_boundary")
                    or "课程数据来源未标注，页面不会将其表述为实时模型生成。"
                ),
            ),
            progress_percent=progress_percent,
            next_step=next_step,
            tasks=tasks,
            capabilities=capabilities,
            resources=resources,
            assignments=assignments,
            updates=updates,
            tutor_exchanges=tutor_exchanges,
            assessment_demo_draft=assessment_demo_draft,
            assessment=assessment,
        )

    async def _capabilities(self, user_id: UUID) -> list[StudentCourseCapabilityDTO]:
        rows = list(
            (await self.session.execute(
                select(UserCapability)
                .where(UserCapability.user_id == user_id)
                .order_by(UserCapability.dimension)
            )).scalars()
        )
        return [
            StudentCourseCapabilityDTO(
                dimension=CAPABILITY_LABELS.get(row.dimension, row.dimension),
                score=_bounded_score(row.score),
                confidence=_bounded_score(row.confidence),
                evidence_count=max(0, row.evidence_count),
            )
            for row in rows
            if row.dimension in CAPABILITY_LABELS
        ]

    async def _tasks(
        self, user_id: UUID, course_id: UUID
    ) -> tuple[list[StudentCourseTaskDTO], StudentCourseTaskDTO | None]:
        path = await self.session.scalar(
            select(LearningPath)
            .where(
                LearningPath.user_id == user_id,
                LearningPath.course_id == course_id,
                LearningPath.status == "active",
            )
            .order_by(LearningPath.updated_at.desc())
            .limit(1)
        )
        if path is None:
            return [], None
        rows = (await self.session.execute(
            select(LearningTask, KnowledgeNode)
            .outerjoin(KnowledgeNode, KnowledgeNode.id == LearningTask.kp_id)
            .where(LearningTask.path_id == path.id)
            .order_by(LearningTask.order_index)
        )).all()
        tasks = [
            StudentCourseTaskDTO(
                title=row.title,
                knowledge_point=node.name if node is not None else None,
                status=_task_status(row.status),
                order_index=max(0, row.order_index),
            )
            for row, node in rows
        ]
        next_task = next((task for task in tasks if task.status in {"active", "todo"}), None)
        return tasks, next_task

    async def _resources(
        self, user_id: UUID, course_id: UUID
    ) -> list[StudentCourseResourceDTO]:
        rows = (await self.session.execute(
            select(GeneratedResource, KnowledgeNode)
            .outerjoin(KnowledgeNode, KnowledgeNode.id == GeneratedResource.kp_id)
            .where(
                GeneratedResource.course_id == course_id,
                GeneratedResource.resource_type.in_(RESOURCE_TYPES),
                GeneratedResource.status.in_(("ready", "active")),
                or_(GeneratedResource.user_id.is_(None), GeneratedResource.user_id == user_id),
            )
            .order_by(GeneratedResource.resource_type, GeneratedResource.version.desc(), GeneratedResource.updated_at.desc())
        )).all()
        grouped: dict[UUID, list[tuple[GeneratedResource, KnowledgeNode | None]]] = defaultdict(list)
        for resource, node in rows:
            grouped[resource.lineage_root_id or resource.id].append((resource, node))
        latest_rows: list[tuple[GeneratedResource, KnowledgeNode | None, list[int]]] = []
        for versions in grouped.values():
            versions.sort(key=lambda item: (item[0].version, item[0].updated_at), reverse=True)
            latest, node = versions[0]
            latest_rows.append((latest, node, sorted({item[0].version for item in versions}, reverse=True)))
        evidence_by_resource = await self._resource_evidence(latest_rows)
        resources: list[StudentCourseResourceDTO] = []
        for resource, node, versions in latest_rows:
            metadata = dict(resource.metadata_ or {})
            content = dict(resource.content or {})
            source_kind = _source_kind(metadata.get("source_kind") or content.get("source_type"))
            resources.append(
                StudentCourseResourceDTO(
                    resource_id=resource.id,
                    lineage_root_id=resource.lineage_root_id or resource.id,
                    logical_key=str(metadata.get("logical_key") or f"{resource.resource_type}-course-v{resource.version}"),
                    resource_type=resource.resource_type,  # type: ignore[arg-type]
                    title=resource.title,
                    knowledge_point=node.name if node is not None else None,
                    version=max(1, resource.version),
                    available_versions=versions,
                    quality_state=str(metadata.get("quality_state") or "ready"),
                    source_kind=source_kind,
                    source_boundary=_resource_boundary(source_kind, content),
                    content=content,
                    evidence=evidence_by_resource.get(resource.id, []),
                    updated_at=resource.updated_at,
                )
            )
        return sorted(resources, key=lambda item: (RESOURCE_TYPE_ORDER[item.resource_type], item.title))

    async def _resource_evidence(
        self,
        rows: Iterable[tuple[GeneratedResource, KnowledgeNode | None, list[int]]],
    ) -> dict[UUID, list[StudentCourseEvidenceDTO]]:
        by_resource: dict[UUID, list[UUID]] = {}
        all_chunk_ids: set[UUID] = set()
        for resource, _, _ in rows:
            chunk_ids = _uuid_values(resource.evidence_chunk_ids)
            by_resource[resource.id] = chunk_ids
            all_chunk_ids.update(chunk_ids)
        if not all_chunk_ids:
            return {}
        chunk_rows = (await self.session.execute(
            select(Chunk, Document)
            .join(Document, Document.id == Chunk.document_id)
            .where(Chunk.id.in_(all_chunk_ids))
        )).all()
        evidence_by_chunk = {
            chunk.id: StudentCourseEvidenceDTO(
                label=document.title,
                excerpt=_excerpt(chunk.chunk_text),
                source_kind=_source_kind(dict(document.metadata_ or {}).get("source_kind") or document.source_type),
                source_url=document.url,
            )
            for chunk, document in chunk_rows
        }
        return {
            resource_id: [evidence_by_chunk[chunk_id] for chunk_id in chunk_ids if chunk_id in evidence_by_chunk]
            for resource_id, chunk_ids in by_resource.items()
        }

    async def _assignments(
        self,
        *,
        actor_id: UUID,
        course_id: UUID,
        teaching_class_id: UUID,
        group_id: UUID | None,
    ) -> list[StudentCourseAssignmentDTO]:
        scopes = [
            and_(
                AssessmentAssignment.target_type == "class",
                AssessmentAssignment.teaching_class_id == teaching_class_id,
            ),
            and_(
                AssessmentAssignment.target_type == "student",
                AssessmentAssignment.student_id == actor_id,
            ),
        ]
        if group_id is not None:
            scopes.append(
                and_(
                    AssessmentAssignment.target_type == "group",
                    AssessmentAssignment.group_id == group_id,
                )
            )
        rows = (await self.session.execute(
            select(AssessmentAssignment, AssessmentVersion, Assessment)
            .join(AssessmentVersion, AssessmentVersion.id == AssessmentAssignment.assessment_version_id)
            .join(Assessment, Assessment.id == AssessmentVersion.assessment_id)
            .where(Assessment.course_id == course_id, or_(*scopes))
            .order_by(AssessmentAssignment.due_at)
        )).all()
        result: list[StudentCourseAssignmentDTO] = []
        for assignment, version, assessment in rows:
            question_count = await self.session.scalar(
                select(func.count(AssessmentItem.id)).where(AssessmentItem.assessment_version_id == version.id)
            )
            submission = await self.session.scalar(
                select(AssessmentSubmission).where(
                    AssessmentSubmission.assignment_id == assignment.id,
                    AssessmentSubmission.student_id == actor_id,
                )
            )
            grade = (
                await self.session.scalar(
                    select(AssessmentGradeDecision).where(AssessmentGradeDecision.submission_id == submission.id)
                )
                if submission is not None
                else None
            )
            learner_status, score, next_action = _learner_assignment_status(assignment, submission, grade)
            result.append(
                StudentCourseAssignmentDTO(
                    id=assignment.id,
                    logical_key=assessment.logical_key,
                    title=version.title,
                    due_at=assignment.due_at,
                    allow_late=assignment.allow_late,
                    question_count=int(question_count or 0),
                    assignment_status=assignment.status,  # type: ignore[arg-type]
                    learner_status=learner_status,
                    published_score=score,
                    next_action=next_action,
                )
            )
        return result

    async def _updates(self, user_id: UUID, course_id: UUID) -> list[StudentCourseUpdateDTO]:
        rows = (await self.session.execute(
            select(Message, MessageDelivery)
            .join(MessageDelivery, MessageDelivery.message_id == Message.id)
            .where(
                Message.course_id == course_id,
                MessageDelivery.recipient_user_id == user_id,
                Message.status.in_(("sent", "partially_delivered")),
                Message.safety_state == "accepted",
            )
            .order_by(MessageDelivery.delivered_at.desc())
            .limit(6)
        )).all()
        return [
            StudentCourseUpdateDTO(
                subject=message.subject,
                body=message.body,
                delivered_at=delivery.delivered_at,
                read=delivery.delivery_state == "read",
            )
            for message, delivery in rows
        ]

    async def _tutor_exchanges(self, user_id: UUID) -> list[StudentCourseTutorExchangeDTO]:
        events = list(
            (await self.session.execute(
                select(LearningEvent)
                .where(
                    LearningEvent.user_id == user_id,
                    LearningEvent.event_type == "tutor_curated_exchange",
                )
                .order_by(LearningEvent.occurred_at)
            )).scalars()
        )
        results = [dict(event.result or {}) for event in events]
        evidence_by_index = await self._tutor_evidence(results)
        exchanges: list[StudentCourseTutorExchangeDTO] = []
        for index, (event, result) in enumerate(zip(events, results, strict=True)):
            evidence_status = "insufficient" if result.get("evidence_status") == "insufficient" else "available"
            question = str(result.get("question") or "").strip()
            concept = str(result.get("concept") or "").strip()
            defensive_example = str(result.get("defensive_example") or "").strip()
            next_step = str(result.get("next_step") or "").strip()
            if not all((question, concept, defensive_example, next_step)):
                continue
            exchanges.append(
                StudentCourseTutorExchangeDTO(
                    question=question,
                    concept=concept,
                    defensive_example=defensive_example,
                    next_step=next_step,
                    evidence_status=evidence_status,
                    source_kind="curated-demo" if result.get("source_kind") == "curated-demo" else "real",
                    source_boundary=str(
                        result.get("source_boundary")
                        or "课程辅导记录来源未标注；页面不会将其描述为实时模型回答。"
                    ),
                    evidence=[] if evidence_status == "insufficient" else evidence_by_index.get(index, []),
                    recorded_at=event.occurred_at,
                    quick_reply_available=(
                        result.get("source_kind") == "curated-demo"
                        and result.get("quick_reply_available") is True
                    ),
                )
            )
        return exchanges

    async def _assessment_demo_draft(
        self,
        *,
        user_id: UUID,
        course_id: UUID,
        assignments: list[StudentCourseAssignmentDTO],
    ) -> StudentCourseDemoAssessmentDraftDTO | None:
        """Read one explicitly seeded, current-student assessment draft.

        The event is not a generic answer-key channel: it is accepted only
        for the controlled showcase profile, a current assignment already in
        this student's projection, and an owned active quiz resource that the
        normal assessment workflow will validate again before it can run. A
        submitted controlled answer set remains recoverable for review and a
        deliberately audited re-evaluation; it is never reopened as a new
        blank submission or used to overwrite the learner's durable result.
        """

        event = await self.session.scalar(
            select(LearningEvent)
            .where(
                LearningEvent.user_id == user_id,
                LearningEvent.event_type == "assessment_demo_draft",
            )
            .order_by(LearningEvent.occurred_at.desc())
            .limit(1)
        )
        if event is None:
            return None
        result = dict(event.result or {})
        if (
            result.get("seed_profile") != "showcase_course"
            or result.get("source_kind") != "curated-demo"
            or result.get("assessment_profile") != "websec_comprehensive_36"
        ):
            return None

        assignment_ids = {
            assignment.id
            for assignment in assignments
            if assignment.assignment_status == "active"
            and assignment.learner_status in {"not_started", "submitted", "late"}
        }
        parsed_assignment = _uuid_values([result.get("assignment_id")])
        if len(parsed_assignment) != 1 or parsed_assignment[0] not in assignment_ids:
            return None
        assignment_id = parsed_assignment[0]
        assignment = await self.session.get(AssessmentAssignment, assignment_id)
        if assignment is None:
            return None
        items = list(
            (
                await self.session.execute(
                    select(AssessmentItem)
                    .where(AssessmentItem.assessment_version_id == assignment.assessment_version_id)
                    .order_by(AssessmentItem.position)
                )
            ).scalars()
        )
        expected_ids = {str(item.quiz_item_id) for item in items}
        if len(items) != 36 or len(expected_ids) != 36:
            return None
        raw_answers = result.get("answers")
        if not expected_ids or not isinstance(raw_answers, dict):
            return None
        answers: dict[str, str | list[str]] = {}
        for raw_key, raw_value in raw_answers.items():
            question_ids = _uuid_values([raw_key])
            if len(question_ids) != 1:
                return None
            key = str(question_ids[0])
            if key not in expected_ids:
                return None
            if isinstance(raw_value, str) and raw_value.strip():
                answers[key] = raw_value.strip()
                continue
            if (
                isinstance(raw_value, list)
                and raw_value
                and all(isinstance(value, str) and value.strip() for value in raw_value)
            ):
                answers[key] = [value.strip() for value in raw_value]
                continue
            return None
        if set(answers) != expected_ids:
            return None

        submission = await self.session.scalar(
            select(AssessmentSubmission).where(
                AssessmentSubmission.assignment_id == assignment_id,
                AssessmentSubmission.student_id == user_id,
            )
        )
        if submission is None:
            return None
        if submission.status == "open":
            # An open controlled submission must remain genuinely empty until
            # the learner explicitly submits the editable draft.
            if submission.answers:
                return None
        elif submission.status in {"submitted", "late"}:
            # Once submitted, only expose the recovery action when the
            # persisted answer set is exactly the controlled draft.  This
            # avoids presenting seed answers for a learner-edited submission
            # that the real workflow would correctly reject as mismatched.
            if not _assessment_answer_maps_match(submission.answers, answers):
                return None
        else:
            return None

        resource_ids = _uuid_values([result.get("quiz_resource_id")])
        if len(resource_ids) != 1:
            return None
        resource = await self.session.get(GeneratedResource, resource_ids[0])
        if (
            resource is None
            or resource.user_id != user_id
            or resource.course_id != course_id
            or resource.resource_type != "quiz"
            or resource.status != "active"
            or not resource.evidence_chunk_ids
        ):
            return None
        assignment_dto = next(
            item for item in assignments if item.id == assignment_id
        )
        return StudentCourseDemoAssessmentDraftDTO(
            assignment_id=assignment_id,
            assignment_title=assignment_dto.title,
            quiz_resource_id=resource.id,
            answers=answers,
            source_kind="curated-demo",
            source_boundary=str(
                result.get("source_boundary")
                or "受控预置演示作答仅填入可编辑草稿；分数、能力和路径只会在真实提交与工作流完成后更新。"
            ),
        )

    async def _tutor_evidence(
        self, results: list[dict[str, Any]]
    ) -> dict[int, list[StudentCourseEvidenceDTO]]:
        snapshot_ids = {
            parsed
            for result in results
            for parsed in _uuid_values([result.get("evidence_snapshot_id")])
        }
        if not snapshot_ids:
            return {}
        snapshots = list(
            (await self.session.execute(
                select(WorkflowEvidenceSnapshot).where(WorkflowEvidenceSnapshot.id.in_(snapshot_ids))
            )).scalars()
        )
        snapshot_map = {snapshot.id: snapshot for snapshot in snapshots}
        resolved: dict[int, list[StudentCourseEvidenceDTO]] = {}
        for index, result in enumerate(results):
            ids = _uuid_values([result.get("evidence_snapshot_id")])
            references: list[StudentCourseEvidenceDTO] = []
            for snapshot_id in ids:
                snapshot = snapshot_map.get(snapshot_id)
                if snapshot is None:
                    continue
                document = await self._document_from_snapshot(snapshot)
                source = dict(snapshot.source or {})
                references.append(
                    StudentCourseEvidenceDTO(
                        label=document.title if document is not None else "课程 Evidence 摘要",
                        excerpt=_excerpt(snapshot.excerpt or "课程证据摘要可在已授权详情中查看。"),
                        source_kind=_source_kind(source.get("source_kind")),
                        source_url=document.url if document is not None else None,
                    )
                )
            if references:
                resolved[index] = references
        return resolved

    async def _document_from_snapshot(self, snapshot: WorkflowEvidenceSnapshot) -> Document | None:
        values = _uuid_values([snapshot.document_id])
        return await self.session.get(Document, values[0]) if values else None

    async def _assessment(self, user_id: UUID, course_id: UUID) -> StudentCourseAssessmentDTO:
        rows = (await self.session.execute(
            select(QuizAttempt, KnowledgeNode)
            .join(QuizItem, QuizItem.id == QuizAttempt.quiz_item_id)
            .join(KnowledgeNode, KnowledgeNode.id == QuizItem.kp_id)
            .where(
                QuizAttempt.user_id == user_id,
                QuizAttempt.score.is_not(None),
                KnowledgeNode.course_id == course_id,
            )
            .order_by(QuizAttempt.created_at)
        )).all()
        by_node: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"baseline": [], "recent": []})
        baseline_scores: list[float] = []
        recent_scores: list[float] = []
        for attempt, node in rows:
            score = _bounded_score(attempt.score)
            window = str(dict(attempt.metadata_ or {}).get("window") or "")
            if window not in {"baseline", "recent"}:
                continue
            by_node[node.name][window].append(score)
            (baseline_scores if window == "baseline" else recent_scores).append(score)
        metrics = [
            _knowledge_metric(name, values["baseline"], values["recent"])
            for name, values in by_node.items()
        ]
        metrics.sort(key=lambda item: (item.trend != "needs_attention", item.knowledge_point))
        baseline_average = round(fmean(baseline_scores), 3) if baseline_scores else None
        recent_average = round(fmean(recent_scores), 3) if recent_scores else None
        return StudentCourseAssessmentDTO(
            baseline_average=baseline_average,
            recent_average=recent_average,
            trend=_overall_trend(baseline_average, recent_average),
            scored_attempt_count=len(rows),
            metrics=metrics,
            feedback_boundary=(
                "这里展示的是当前学生自己的已评分作答与已持久化能力快照；新的阶段评估仍由 "
                "assessment_update_v2 经过 Evidence、质量检查和能力回写后才会刷新后续推荐。"
            ),
        )


def _task_status(value: str) -> str:
    if value == "done":
        return "done"
    if value in {"active", "in_progress"}:
        return "active"
    if value in {"blocked", "locked"}:
        return "blocked"
    return "todo"


def _source_kind(value: Any) -> str:
    if str(value or "").strip() == "external-preview":
        return "external-preview"
    if str(value or "").strip() in {"curated-demo", "curated_lecture", "preprocessed_seed"}:
        return "curated-demo"
    return "real"


def _resource_boundary(source_kind: str, content: dict[str, Any]) -> str:
    if source_kind == "external-preview":
        return "外部公开资料目录；平台只保留合规跳转和学习导引，不托管或伪称生成该内容。"
    if source_kind == "curated-demo":
        return "受控课程整理内容，已写入真实课程资源记录；不是实时模型生成。"
    return str(content.get("source_boundary") or "真实持久化课程资源；详情保留来源和 Evidence。")


def _uuid_values(values: Iterable[Any]) -> list[UUID]:
    result: list[UUID] = []
    for value in values:
        try:
            parsed = UUID(str(value))
        except (TypeError, ValueError, AttributeError):
            continue
        if parsed not in result:
            result.append(parsed)
    return result


def _excerpt(value: str, maximum: int = 180) -> str:
    normalized = " ".join(value.split())
    return normalized if len(normalized) <= maximum else f"{normalized[: maximum - 1]}…"


def _as_score(value: Any) -> float:
    try:
        return _bounded_score(float(value))
    except (TypeError, ValueError):
        return 0.0


def _bounded_score(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _learner_assignment_status(
    assignment: AssessmentAssignment,
    submission: AssessmentSubmission | None,
    grade: AssessmentGradeDecision | None,
) -> tuple[str, float | None, str]:
    if assignment.status == "withdrawn":
        return "withdrawn", None, "该作业已撤回，不会显示题目或未发布成绩。"
    if submission is None or submission.status == "open":
        return "not_started", None, "开始已发布作业"
    if grade is None:
        return ("late" if submission.status == "late" else "submitted"), None, "作答已提交，等待评分。"
    if grade.status == "published" and grade.withdrawn_at is None and grade.final_score is not None:
        return "published", grade.final_score, "查看已发布成绩与复盘建议"
    if grade.status == "withdrawn" or grade.withdrawn_at is not None:
        return "withdrawn", None, "成绩已撤回，等待教师重新发布。"
    if grade.status == "teacher_reviewed":
        return "teacher_review", None, "教师复核中，当前不显示未发布成绩。"
    return "grading", None, "系统评分或教师复核中，当前不显示未发布成绩。"


def _assessment_answer_maps_match(
    persisted: object,
    expected: dict[str, str | list[str]],
) -> bool:
    """Compare a durable submission with the controlled draft without grading it.

    This only establishes whether it is truthful to offer the demo learner a
    recovery view of the same frozen answers.  It deliberately does not treat
    a matching answer set as a score, QualityCheck result, or capability
    update.
    """

    if not isinstance(persisted, dict) or set(map(str, persisted)) != set(expected):
        return False

    def signature(value: object) -> tuple[str, ...] | None:
        if isinstance(value, list):
            values = value
        elif isinstance(value, str):
            values = value.split(";")
        else:
            return None
        normalized = sorted(
            "".join(str(item).strip().lower().split())
            for item in values
            if str(item).strip()
        )
        return tuple(normalized) if normalized else None

    return all(
        signature(persisted.get(item_id)) == signature(answer)
        for item_id, answer in expected.items()
    )


def _knowledge_metric(
    knowledge_point: str, baseline: list[float], recent: list[float]
) -> StudentCourseKnowledgeMetricDTO:
    baseline_average = round(fmean(baseline), 3) if baseline else None
    recent_average = round(fmean(recent), 3) if recent else None
    trend = _overall_trend(baseline_average, recent_average)
    if recent_average is not None and recent_average < 0.6:
        trend = "needs_attention"
    return StudentCourseKnowledgeMetricDTO(
        knowledge_point=knowledge_point,
        baseline_average=baseline_average,
        recent_average=recent_average,
        sample_size=len(baseline) + len(recent),
        trend=trend,
    )


def _overall_trend(baseline: float | None, recent: float | None) -> str:
    if baseline is None or recent is None:
        return "insufficient"
    if recent - baseline >= 0.04:
        return "improving"
    if recent < 0.6:
        return "needs_attention"
    return "stable"
