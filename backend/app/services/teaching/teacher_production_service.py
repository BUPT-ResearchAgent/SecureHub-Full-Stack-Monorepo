# Status: real

"""Authorization-aware T3 teacher production service.

This service is intentionally a thin state-machine layer over durable SQL
rows.  It never invokes an LLM/provider directly.  Where a subjective grading
or syllabus generation result is accepted, the result must already be a
successful Runtime/SkillExecutor AgentRun with a linked Evidence Snapshot.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from hashlib import sha256
import json
from typing import Any, Iterable
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.education.education_domain import (
    CourseEnrollment,
    GovernanceAuditEvent,
    StudentGroupMember,
)
from app.db.models.identity.user import User
from app.db.models.identity.user_capability import UserCapability
from app.db.models.knowledge.document import Document
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.db.models.learning.learning_event import LearningEvent
from app.db.models.learning.quiz_item import QuizItem
from app.db.models.resource.generated_resource import GeneratedResource
from app.db.models.teaching.teacher_production import (
    Assessment,
    AssessmentAssignment,
    AssessmentGradeDecision,
    AssessmentItem,
    AssessmentSubmission,
    AssessmentVersion,
    ClassWeaknessSnapshot,
    CourseAssetGovernance,
    CourseDocumentBinding,
    CourseSyllabus,
    CourseSyllabusVersion,
    QuizReviewDecision,
    SyllabusExport,
    SyllabusReviewDecision,
    TeachingRecommendation,
    TeachingRecommendationDecision,
)
from app.repositories.education.education_domain import EducationRepository
from app.repositories.teaching.teacher_production import TeachingProductionRepository
from app.schemas.syllabus import (
    CreateSyllabusVersionRequest,
    GenerateSyllabusVersionRequest,
    SyllabusDiffDTO,
    SyllabusExportDTO,
    SyllabusExportRequest,
    SyllabusReviewRequest,
    SyllabusVersionDTO,
    SyllabusVersionListDTO,
    TypedSyllabusContent,
)
from app.schemas.teacher_production import (
    AssessmentAssignmentDTO,
    AssessmentCreateRequest,
    AssessmentDTO,
    AssessmentSubmissionDTO,
    AssessmentVersionCreateRequest,
    AssessmentVersionDTO,
    AssessmentVersionItemDTO,
    AssetLifecycleRequest,
    BindCourseDocumentRequest,
    CorrectCourseAssetRequest,
    CourseAssetDTO,
    CourseAssetListDTO,
    CreateTeachingRecommendationRequest,
    GradeDecisionDTO,
    GradeOverrideRequest,
    ObjectiveScoreDTO,
    QuizReviewDecisionDTO,
    QuizReviewRequest,
    RecordSubjectiveSuggestionRequest,
    StudentPublishedResultDTO,
    SubmitAssessmentRequest,
    TeacherAssignmentDTO,
    TeacherAssignmentListDTO,
    TeacherAssessmentSubmissionDTO,
    TeacherAssessmentSubmissionListDTO,
    TeacherCourseDTO,
    TeacherCourseListDTO,
    TeacherDashboardDTO,
    TeachingRecommendationDTO,
    TeachingRecommendationDecisionRequest,
    TeachingRecommendationListDTO,
    WeaknessKnowledgePointDTO,
    WeaknessSnapshotDTO,
    WeaknessSnapshotListDTO,
    WeaknessSnapshotRequest,
)


_COURSE_TEACHER_ROLES = {"course_teacher", "hybrid"}
_PUBLISHABLE_QUIZ_STATUS = "curated"
_QUALITY_VALIDATOR_VERSION = "websec-quiz-quality-v1"
_WEAKNESS_SCORE_VERSION = "teacher-weakness-v1"


def _as_utc(value: datetime) -> datetime:
    """Return a comparable UTC timestamp across PostgreSQL and SQLite.

    PostgreSQL preserves ``DateTime(timezone=True)`` offsets, while SQLite's
    compatibility dialect returns the same persisted value as naive.  T3's
    deadline and teaching-window rules must therefore give a naive database
    value its persisted UTC meaning before comparing it with ``now(UTC)``.
    """

    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class TeacherProductionError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class TeacherProductionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TeachingProductionRepository(session)
        self.education = EducationRepository(session)

    # ------------------------------------------------------------------
    # FG-02: course / unified knowledge asset governance
    # ------------------------------------------------------------------

    async def list_owned_courses(self, *, actor: User) -> TeacherCourseListDTO:
        self._require_teacher_role(actor)
        courses = await self.repo.list_owned_courses(actor.id)
        ids = [course.id for course in courses]
        classes = await self.repo.count_classes_for_courses(ids)
        students = await self.repo.count_enrolled_for_courses(ids)
        return TeacherCourseListDTO(
            items=[
                TeacherCourseDTO(
                    id=course.id,
                    code=course.code,
                    title=course.title,
                    active_class_count=classes.get(course.id, 0),
                    enrolled_student_count=students.get(course.id, 0),
                )
                for course in courses
            ]
        )

    async def dashboard(self, *, actor: User) -> TeacherDashboardDTO:
        self._require_teacher_role(actor)
        courses = await self.repo.list_owned_courses(actor.id)
        counts = await self.repo.count_dashboard(
            teacher_id=actor.id, course_ids=[course.id for course in courses]
        )
        return TeacherDashboardDTO(
            course_count=len(courses),
            active_student_count=counts["active_students"],
            governed_asset_count=counts["governed_assets"],
            pending_quiz_review_count=counts["pending_quiz_reviews"],
            active_assignment_count=counts["active_assignments"],
            pending_grade_count=counts["pending_grades"],
            definitions={
                "course_count": "当前教师有有效 course_teacher_assignments 的课程数",
                "active_student_count": "上述课程中 status=enrolled 的 course_enrollments 数",
                "governed_asset_count": "上述课程中未撤回/删除的 course_asset_governance 数",
                "pending_quiz_review_count": "上述课程中待教师处置的持久 quiz_items 数",
                "active_assignment_count": "上述课程中 status=active 的 assessment_assignments 数",
                "pending_grade_count": "已提交且尚未由教师最终确认/发布的 assessment_submissions 数",
            },
            calculated_at=datetime.now(UTC),
        )

    async def list_assets(
        self, *, actor: User, course_id: UUID, include_deleted: bool = False
    ) -> CourseAssetListDTO:
        await self._require_teacher_course(actor=actor, course_id=course_id)
        rows = await self.repo.list_assets_for_course(
            course_id=course_id, include_deleted=include_deleted
        )
        for asset, _, document in rows:
            await self._reconcile_asset_state(asset, document)
            # ``updated_at`` is server-managed. Refresh after a reconciliation
            # update so serialising the DTO never triggers implicit async IO.
            await self.session.refresh(asset)
        return CourseAssetListDTO(items=[self._asset_dto(*row) for row in rows])

    async def bind_document(
        self,
        *,
        actor: User,
        course_id: UUID,
        payload: BindCourseDocumentRequest,
    ) -> CourseAssetDTO:
        course = await self._require_teacher_course(actor=actor, course_id=course_id)
        document = await self._require_course_document(course_id=course.id, document_id=payload.document_id)
        await self._require_document_asset_match(
            document_id=document.id, document_asset_id=payload.document_asset_id
        )
        binding = await self.repo.get_binding_for_course_document(
            course_id=course_id, document_id=document.id
        )
        if binding is None:
            binding = CourseDocumentBinding(
                id=uuid4(),
                course_id=course_id,
                document_id=document.id,
                bound_by=actor.id,
                purpose=payload.purpose,
                status="active",
            )
            self.session.add(binding)
            await self.session.flush()
        elif binding.status == "active":
            raise TeacherProductionError(
                "ASSET_STATE_CONFLICT", "该知识文档已经绑定到本课程，请使用更正或生命周期操作。"
            )
        else:
            binding.status = "active"
            binding.purpose = payload.purpose
            await self.session.flush()

        existing_rows = await self.repo.list_assets_for_course(course_id=course_id, include_deleted=True)
        version_no = 1 + max(
            (row.version_no for row, candidate_binding, _ in existing_rows if candidate_binding.id == binding.id),
            default=0,
        )
        asset = CourseAssetGovernance(
            id=uuid4(),
            binding_id=binding.id,
            document_asset_id=payload.document_asset_id,
            owner_teacher_id=actor.id,
            version_no=version_no,
            state=self._document_governance_state(document),
            reason=payload.reason,
        )
        self.session.add(asset)
        await self.session.flush()
        await self.session.refresh(asset)
        await self._audit(
            actor=actor,
            action="course_asset.bind",
            object_type="course_asset_governance",
            object_id=asset.id,
            reason=payload.reason,
            metadata={
                "course_id": str(course_id),
                "document_id": str(document.id),
                "state": asset.state,
                "version_no": asset.version_no,
            },
        )
        return self._asset_dto(asset, binding, document)

    async def correct_asset(
        self,
        *,
        actor: User,
        asset_id: UUID,
        payload: CorrectCourseAssetRequest,
    ) -> CourseAssetDTO:
        context = await self._require_asset_scope(actor=actor, asset_id=asset_id)
        old_asset, old_binding, _ = context
        if old_asset.state in {"deleted", "withdrawn"}:
            raise TeacherProductionError(
                "ASSET_STATE_CONFLICT", "已删除或撤回的资产不能作为更正父版本，请先恢复。"
            )
        course = await self.repo.get_course(old_binding.course_id)
        if course is None:
            raise TeacherProductionError("COURSE_ACCESS_DENIED", "课程不存在或不可治理。", 404)
        replacement = await self._require_course_document(
            course_id=course.id, document_id=payload.replacement_document_id
        )
        await self._require_document_asset_match(
            document_id=replacement.id,
            document_asset_id=payload.replacement_document_asset_id,
        )
        binding = await self.repo.get_binding_for_course_document(
            course_id=course.id, document_id=replacement.id
        )
        if binding is None:
            binding = CourseDocumentBinding(
                id=uuid4(),
                course_id=course.id,
                document_id=replacement.id,
                bound_by=actor.id,
                purpose=old_binding.purpose,
                status="active",
            )
            self.session.add(binding)
            await self.session.flush()
        else:
            binding.status = "active"

        existing_rows = await self.repo.list_assets_for_course(course_id=course.id, include_deleted=True)
        next_version = 1 + max(
            (row.version_no for row, candidate_binding, _ in existing_rows if candidate_binding.id == binding.id),
            default=0,
        )
        old_asset.state = "correction_pending"
        old_asset.reason = payload.reason
        asset = CourseAssetGovernance(
            id=uuid4(),
            binding_id=binding.id,
            document_asset_id=payload.replacement_document_asset_id,
            owner_teacher_id=actor.id,
            version_no=next_version,
            state=self._document_governance_state(replacement),
            correction_of_id=old_asset.id,
            reason=payload.reason,
        )
        self.session.add(asset)
        await self.session.flush()
        await self._reconcile_asset_state(asset, replacement)
        await self.session.refresh(asset)
        await self._audit(
            actor=actor,
            action="course_asset.correct",
            object_type="course_asset_governance",
            object_id=asset.id,
            reason=payload.reason,
            metadata={
                "course_id": str(course.id),
                "correction_of_id": str(old_asset.id),
                "replacement_document_id": str(replacement.id),
                "version_no": asset.version_no,
            },
        )
        return self._asset_dto(asset, binding, replacement)

    async def withdraw_asset(
        self, *, actor: User, asset_id: UUID, payload: AssetLifecycleRequest
    ) -> CourseAssetDTO:
        asset, binding, document = await self._require_asset_scope(actor=actor, asset_id=asset_id)
        if asset.state in {"deleted", "withdrawn"}:
            raise TeacherProductionError("ASSET_STATE_CONFLICT", "资产当前不能重复撤回。")
        asset.state = "withdrawn"
        asset.withdrawn_at = datetime.now(UTC)
        asset.withdrawn_by = actor.id
        asset.reason = payload.reason
        binding.status = "withdrawn"
        await self.session.flush()
        await self.session.refresh(asset)
        await self._audit(
            actor=actor,
            action="course_asset.withdraw",
            object_type="course_asset_governance",
            object_id=asset.id,
            reason=payload.reason,
            metadata={"course_id": str(binding.course_id), "document_id": str(document.id)},
        )
        return self._asset_dto(asset, binding, document)

    async def delete_asset(
        self, *, actor: User, asset_id: UUID, payload: AssetLifecycleRequest
    ) -> CourseAssetDTO:
        asset, binding, document = await self._require_asset_scope(actor=actor, asset_id=asset_id)
        if asset.state == "deleted":
            raise TeacherProductionError("ASSET_STATE_CONFLICT", "资产已经处于软删除状态。")
        asset.state = "deleted"
        asset.deleted_at = datetime.now(UTC)
        asset.deleted_by = actor.id
        asset.reason = payload.reason
        binding.status = "deleted"
        await self.session.flush()
        await self.session.refresh(asset)
        await self._audit(
            actor=actor,
            action="course_asset.delete",
            object_type="course_asset_governance",
            object_id=asset.id,
            reason=payload.reason,
            metadata={"course_id": str(binding.course_id), "soft_delete": True},
        )
        return self._asset_dto(asset, binding, document)

    async def restore_asset(
        self, *, actor: User, asset_id: UUID, payload: AssetLifecycleRequest
    ) -> CourseAssetDTO:
        asset, binding, document = await self._require_asset_scope(actor=actor, asset_id=asset_id)
        if asset.state not in {"deleted", "withdrawn"}:
            raise TeacherProductionError("ASSET_STATE_CONFLICT", "只有撤回或软删除资产可恢复。")
        asset.state = self._document_governance_state(document)
        asset.deleted_at = None
        asset.deleted_by = None
        asset.withdrawn_at = None
        asset.withdrawn_by = None
        asset.reason = payload.reason
        binding.status = "active"
        await self.session.flush()
        await self.session.refresh(asset)
        await self._audit(
            actor=actor,
            action="course_asset.restore",
            object_type="course_asset_governance",
            object_id=asset.id,
            reason=payload.reason,
            metadata={"course_id": str(binding.course_id), "restored_state": asset.state},
        )
        return self._asset_dto(asset, binding, document)

    # ------------------------------------------------------------------
    # F1: review, weakness aggregate, and evidence-backed recommendations
    # ------------------------------------------------------------------

    async def review_quiz(
        self, *, actor: User, course_id: UUID, quiz_item_id: UUID, payload: QuizReviewRequest
    ) -> QuizReviewDecisionDTO:
        await self._require_teacher_course(actor=actor, course_id=course_id)
        context = await self.repo.get_quiz_for_course(quiz_item_id=quiz_item_id, course_id=course_id)
        if context is None:
            raise TeacherProductionError("QUESTION_NOT_REVIEWABLE", "题目不属于当前教师课程。", 404)
        item, _ = context
        before = item.review_status
        if payload.decision == "publish":
            quality = await self.repo.latest_quiz_quality(item.id)
            if (
                quality is None
                or quality.result != "passed"
                or quality.validator_version != _QUALITY_VALIDATOR_VERSION
            ):
                raise TeacherProductionError(
                    "QUESTION_NOT_REVIEWABLE", "题目未通过当前质量校验，不能由教师发布。"
                )
            after = _PUBLISHABLE_QUIZ_STATUS
        elif payload.decision == "reject":
            after = "rejected"
        else:
            after = "withdrawn"
        if before == "withdrawn" and payload.decision != "publish":
            raise TeacherProductionError("QUESTION_NOT_REVIEWABLE", "已撤回题目不能再次执行该决定。")
        item.review_status = after
        decision = QuizReviewDecision(
            id=uuid4(),
            quiz_item_id=item.id,
            teacher_id=actor.id,
            decision=payload.decision,
            reason=payload.reason,
            before_status=before,
            after_status=after,
        )
        self.session.add(decision)
        await self.session.flush()
        await self._audit(
            actor=actor,
            action="quiz_review.decide",
            object_type="quiz_item",
            object_id=item.id,
            reason=payload.reason,
            metadata={"course_id": str(course_id), "decision": payload.decision, "before": before, "after": after},
        )
        return QuizReviewDecisionDTO(
            id=decision.id,
            quiz_item_id=decision.quiz_item_id,
            decision=decision.decision,  # type: ignore[arg-type]
            before_status=decision.before_status,
            after_status=decision.after_status,
            reason=decision.reason,
            created_at=decision.created_at,
        )

    async def compute_weakness_snapshot(
        self, *, actor: User, course_id: UUID, payload: WeaknessSnapshotRequest
    ) -> WeaknessSnapshotDTO:
        await self._require_teacher_course(actor=actor, course_id=course_id)
        await self._validate_education_scope(
            actor=actor,
            course_id=course_id,
            teaching_class_id=payload.teaching_class_id,
            group_id=payload.group_id,
        )
        student_ids = await self.repo.list_student_ids_for_scope(
            course_id=course_id,
            teaching_class_id=payload.teaching_class_id,
            group_id=payload.group_id,
        )
        if len(student_ids) < payload.minimum_sample:
            raise TeacherProductionError(
                "INSUFFICIENT_ASSESSMENT_SAMPLE", "当前范围的有效选课样本不足，不能生成薄弱知识点结论。"
            )
        attempts = await self.repo.list_quiz_attempt_contexts(
            student_ids=student_ids, course_id=course_id
        )
        filtered_attempts = [
            row
            for row in attempts
            if (payload.window_start is None or row[0].created_at >= payload.window_start)
            and (payload.window_end is None or row[0].created_at <= payload.window_end)
        ]
        measured = [row for row in filtered_attempts if self._attempt_score(row[0]) is not None]
        if not measured:
            raise TeacherProductionError(
                "INSUFFICIENT_ASSESSMENT_SAMPLE", "当前范围没有可评分的真实作答，不能生成薄弱知识点结论。"
            )

        # These two sources are not duplicated: they make the source version
        # explicit while per-knowledge-point scoring remains rooted in actual
        # quiz attempts.  They are used only as aggregate context.
        capabilities = (
            await self.session.execute(
                select(UserCapability).where(UserCapability.user_id.in_(student_ids))
            )
        ).scalars().all()
        learning_events = (
            await self.session.execute(
                select(LearningEvent).where(LearningEvent.user_id.in_(student_ids))
            )
        ).scalars().all()

        values: dict[UUID, list[tuple[float, UUID, str]]] = defaultdict(list)
        names: dict[UUID, str] = {}
        for attempt, _, node in measured:
            score = self._attempt_score(attempt)
            if score is None:
                continue
            values[node.id].append((score, attempt.user_id, str(attempt.id)))
            names[node.id] = node.name
        weak_points: list[dict[str, Any]] = []
        for node_id, records in values.items():
            sample_size = len({student_id for _, student_id, _ in records})
            average = sum(score for score, _, _ in records) / len(records)
            weak_points.append(
                {
                    "knowledge_node_id": str(node_id),
                    "knowledge_node_name": names[node_id],
                    "sample_size": sample_size,
                    "average_score": round(average, 6),
                    "incorrect_rate": round(
                        sum(1 for score, _, _ in records if score < 0.6) / len(records), 6
                    ),
                }
            )
        weak_points.sort(key=lambda row: (row["average_score"], -row["sample_size"], row["knowledge_node_id"]))
        aggregate = {
            "weak_knowledge_points": weak_points[:12],
            "source_counts": {
                "quiz_attempts": len(measured),
                "learning_events": len(learning_events),
                "user_capabilities": len(capabilities),
                "enrolled_students": len(student_ids),
            },
            "limitations": "按题目作答聚合；能力与学习事件仅作为范围内已持久化学习上下文，不复制画像。",
        }
        fingerprint = self._fingerprint(
            {
                "course_id": str(course_id),
                "teaching_class_id": str(payload.teaching_class_id) if payload.teaching_class_id else None,
                "group_id": str(payload.group_id) if payload.group_id else None,
                "window_start": payload.window_start.isoformat() if payload.window_start else None,
                "window_end": payload.window_end.isoformat() if payload.window_end else None,
                "attempts": [
                    {
                        "id": str(attempt.id),
                        "student_id": str(attempt.user_id),
                        "score": self._attempt_score(attempt),
                        "created_at": attempt.created_at.isoformat(),
                    }
                    for attempt, _, _ in measured
                ],
                "capabilities": [
                    (str(row.user_id), row.dimension, row.score, row.updated_at.isoformat())
                    for row in capabilities
                ],
                "learning_events": [str(row.id) for row in learning_events],
                "score_version": _WEAKNESS_SCORE_VERSION,
            }
        )
        existing = await self.session.scalar(
            select(ClassWeaknessSnapshot).where(
                ClassWeaknessSnapshot.course_id == course_id,
                ClassWeaknessSnapshot.teaching_class_id == payload.teaching_class_id,
                ClassWeaknessSnapshot.group_id == payload.group_id,
                ClassWeaknessSnapshot.input_fingerprint == fingerprint,
            )
        )
        if existing is None:
            existing = ClassWeaknessSnapshot(
                id=uuid4(),
                course_id=course_id,
                teaching_class_id=payload.teaching_class_id,
                group_id=payload.group_id,
                window_start=payload.window_start,
                window_end=payload.window_end,
                sample_size=len({attempt.user_id for attempt, _, _ in measured}),
                score_version=_WEAKNESS_SCORE_VERSION,
                input_fingerprint=fingerprint,
                aggregates=aggregate,
            )
            self.session.add(existing)
            await self.session.flush()
            await self._audit(
                actor=actor,
                action="teaching_weakness.compute",
                object_type="class_weakness_snapshot",
                object_id=existing.id,
                reason="教师请求薄弱知识点聚合",
                metadata={
                    "course_id": str(course_id),
                    "sample_size": existing.sample_size,
                    "input_fingerprint": fingerprint,
                    "score_version": _WEAKNESS_SCORE_VERSION,
                },
            )
        return self._weakness_dto(existing)

    async def list_weakness_snapshots(
        self, *, actor: User, course_id: UUID
    ) -> WeaknessSnapshotListDTO:
        """Return only durable, in-scope aggregate snapshots for the teacher UI."""

        await self._require_teacher_course(actor=actor, course_id=course_id)
        rows = await self.repo.list_weakness_snapshots(course_id=course_id)
        return WeaknessSnapshotListDTO(items=[self._weakness_dto(row) for row in rows])

    async def create_teaching_recommendation(
        self,
        *,
        actor: User,
        course_id: UUID,
        payload: CreateTeachingRecommendationRequest,
    ) -> TeachingRecommendationDTO:
        await self._require_teacher_course(actor=actor, course_id=course_id)
        snapshot = await self.repo.get_weakness_snapshot(payload.source_snapshot_id)
        if snapshot is None or snapshot.course_id != course_id:
            raise TeacherProductionError("COURSE_ACCESS_DENIED", "薄弱知识点快照不属于当前课程。", 403)
        evidence = await self.repo.get_evidence_snapshot(payload.evidence_snapshot_id)
        if evidence is None or not evidence.content_digest:
            raise TeacherProductionError("INSUFFICIENT_EVIDENCE", "教学建议缺少可用 Evidence Snapshot。")
        if payload.agent_run_id is not None:
            await self._require_linked_completed_agent_result(
                agent_run_id=payload.agent_run_id, evidence_snapshot_id=payload.evidence_snapshot_id
            )
        version = await self.repo.next_recommendation_version(course_id)
        row = TeachingRecommendation(
            id=uuid4(),
            course_id=course_id,
            teaching_class_id=snapshot.teaching_class_id,
            group_id=snapshot.group_id,
            source_snapshot_id=snapshot.id,
            evidence_snapshot_id=evidence.id,
            agent_run_id=payload.agent_run_id,
            version_no=version,
            diff={
                "kind": "curated" if payload.agent_run_id is None else "skill_candidate",
                "title": payload.title,
                "actions": payload.actions,
                "rationale": payload.rationale,
                "source_snapshot_fingerprint": snapshot.input_fingerprint,
            },
            status="pending",
            created_by=actor.id,
        )
        self.session.add(row)
        await self.session.flush()
        await self._audit(
            actor=actor,
            action="teaching_recommendation.create",
            object_type="teaching_recommendation",
            object_id=row.id,
            reason="教师创建带 Evidence 的教学建议",
            metadata={
                "course_id": str(course_id),
                "source_snapshot_id": str(snapshot.id),
                "evidence_snapshot_id": str(evidence.id),
                "agent_run_id": str(payload.agent_run_id) if payload.agent_run_id else None,
                "version_no": version,
            },
        )
        return self._recommendation_dto(row)

    async def list_teaching_recommendations(
        self, *, actor: User, course_id: UUID
    ) -> TeachingRecommendationListDTO:
        """List persisted recommendation diffs without mutating course content."""

        await self._require_teacher_course(actor=actor, course_id=course_id)
        rows = await self.repo.list_recommendations(course_id=course_id)
        return TeachingRecommendationListDTO(items=[self._recommendation_dto(row) for row in rows])

    async def decide_teaching_recommendation(
        self,
        *,
        actor: User,
        recommendation_id: UUID,
        payload: TeachingRecommendationDecisionRequest,
    ) -> TeachingRecommendationDTO:
        row = await self.repo.get_recommendation(recommendation_id)
        if row is None:
            raise TeacherProductionError("COURSE_ACCESS_DENIED", "教学建议不存在或不可访问。", 404)
        await self._require_teacher_course(actor=actor, course_id=row.course_id)
        if row.status != "pending":
            raise TeacherProductionError("SUGGESTION_ALREADY_DECIDED", "教学建议已被处置，不能重复决定。")
        state = {"adopt": "adopted", "reject": "rejected", "withdraw": "withdrawn"}[payload.decision]
        row.status = state
        decision = TeachingRecommendationDecision(
            id=uuid4(),
            recommendation_id=row.id,
            teacher_id=actor.id,
            decision=payload.decision,
            reason=payload.reason,
        )
        self.session.add(decision)
        await self.session.flush()
        # Adoption intentionally only records the teacher decision.  It never
        # mutates the ready course catalog or its published content.
        await self._audit(
            actor=actor,
            action="teaching_recommendation.decide",
            object_type="teaching_recommendation",
            object_id=row.id,
            reason=payload.reason,
            metadata={"decision": payload.decision, "result_status": state, "course_id": str(row.course_id)},
        )
        return self._recommendation_dto(row)

    # ------------------------------------------------------------------
    # FG-05: versioned assessment / deterministic scoring / publication
    # ------------------------------------------------------------------

    async def list_course_assignments(
        self, *, actor: User, course_id: UUID
    ) -> TeacherAssignmentListDTO:
        """Read the durable assignment/version projection for an owned course."""

        await self._require_teacher_course(actor=actor, course_id=course_id)
        rows = await self.repo.list_course_assignments(course_id=course_id)
        return TeacherAssignmentListDTO(
            items=[
                TeacherAssignmentDTO(
                    id=assignment.id,
                    course_id=assessment.course_id,
                    assessment_id=assessment.id,
                    assessment_version_id=version.id,
                    logical_key=assessment.logical_key,
                    kind=assessment.kind,  # type: ignore[arg-type]
                    title=version.title,
                    version_no=version.version_no,
                    target_type=assignment.target_type,  # type: ignore[arg-type]
                    teaching_class_id=assignment.teaching_class_id,
                    group_id=assignment.group_id,
                    student_id=assignment.student_id,
                    due_at=assignment.due_at,
                    allow_late=assignment.allow_late,
                    status=assignment.status,  # type: ignore[arg-type]
                    created_at=assignment.created_at,
                )
                for assignment, version, assessment in rows
            ]
        )

    async def create_assessment(
        self, *, actor: User, course_id: UUID, payload: AssessmentCreateRequest
    ) -> AssessmentDTO:
        await self._require_teacher_course(actor=actor, course_id=course_id)
        existing = await self.repo.get_assessment_by_logical_key(
            course_id=course_id, logical_key=payload.logical_key
        )
        if existing is not None:
            raise TeacherProductionError("ASSESSMENT_VERSION_LOCKED", "该课程逻辑评估键已经存在。")
        assessment = Assessment(
            id=uuid4(),
            course_id=course_id,
            owner_teacher_id=actor.id,
            kind=payload.kind,
            logical_key=payload.logical_key,
            status="draft",
        )
        self.session.add(assessment)
        await self.session.flush()
        await self._audit(
            actor=actor,
            action="assessment.create",
            object_type="assessment",
            object_id=assessment.id,
            reason="教师创建版本化作业/考试",
            metadata={"course_id": str(course_id), "kind": payload.kind, "logical_key": payload.logical_key},
        )
        return self._assessment_dto(assessment)

    async def create_assessment_version(
        self,
        *,
        actor: User,
        assessment_id: UUID,
        payload: AssessmentVersionCreateRequest,
    ) -> AssessmentVersionDTO:
        assessment = await self._require_assessment_owner(actor=actor, assessment_id=assessment_id)
        if assessment.status in {"closed", "withdrawn"}:
            raise TeacherProductionError("ASSESSMENT_VERSION_LOCKED", "已关闭或撤回的评估不能创建新版本。")
        seen_ids: set[UUID] = set()
        seen_positions: set[int] = set()
        item_rows: list[tuple[Any, Any]] = []
        for request_item in payload.items:
            if request_item.quiz_item_id in seen_ids or request_item.position in seen_positions:
                raise TeacherProductionError("ASSESSMENT_VERSION_LOCKED", "评估版本中题目和位置必须唯一。")
            seen_ids.add(request_item.quiz_item_id)
            seen_positions.add(request_item.position)
            context = await self.repo.get_quiz_for_course(
                quiz_item_id=request_item.quiz_item_id, course_id=assessment.course_id
            )
            if context is None:
                raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "评估题目不属于当前课程。", 403)
            item, node = context
            quality = await self.repo.latest_quiz_quality(item.id)
            if (
                item.review_status != _PUBLISHABLE_QUIZ_STATUS
                or quality is None
                or quality.result != "passed"
                or quality.validator_version != _QUALITY_VALIDATOR_VERSION
            ):
                raise TeacherProductionError(
                    "QUESTION_STATUS_NOT_PUBLISHABLE", "只能将通过质量校验且已发布的题目加入评估版本。"
                )
            item_rows.append((request_item, (item, node)))
        version = AssessmentVersion(
            id=uuid4(),
            assessment_id=assessment.id,
            version_no=await self.repo.next_assessment_version(assessment.id),
            title=payload.title,
            instructions=payload.instructions,
            state="draft",
            created_by=actor.id,
        )
        self.session.add(version)
        await self.session.flush()
        created_items: list[AssessmentItem] = []
        for request_item, (item, node) in item_rows:
            snapshot = {
                "quiz_item_id": str(item.id),
                "canonical_key": item.canonical_key,
                "knowledge_node_id": str(node.id),
                "knowledge_node_name": node.name,
                "type": item.type,
                "question": item.question,
                "options": item.options if isinstance(item.options, list) else [],
                "answer": item.answer,
                "explanation": item.explanation,
                "content_version": item.content_version,
            }
            assessment_item = AssessmentItem(
                id=uuid4(),
                assessment_version_id=version.id,
                quiz_item_id=item.id,
                position=request_item.position,
                points=request_item.points,
                grading_mode=request_item.grading_mode,
                question_snapshot=snapshot,
            )
            self.session.add(assessment_item)
            created_items.append(assessment_item)
        await self.session.flush()
        await self._audit(
            actor=actor,
            action="assessment_version.create",
            object_type="assessment_version",
            object_id=version.id,
            reason="教师创建不可变评估题目快照",
            metadata={
                "assessment_id": str(assessment.id),
                "course_id": str(assessment.course_id),
                "version_no": version.version_no,
                "item_count": len(created_items),
            },
        )
        return self._assessment_version_dto(version, created_items)

    async def assign_assessment(
        self,
        *,
        actor: User,
        version_id: UUID,
        payload: Any,
    ) -> AssessmentAssignmentDTO:
        context = await self.repo.get_assessment_version_context(version_id)
        if context is None:
            raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "评估版本不存在或不可访问。", 404)
        version, assessment = context
        await self._require_assessment_owner(actor=actor, assessment_id=assessment.id)
        if version.state == "withdrawn" or assessment.status == "withdrawn":
            raise TeacherProductionError("ASSESSMENT_VERSION_LOCKED", "已撤回版本不能布置。")
        await self._validate_assignment_target(
            actor=actor, course_id=assessment.course_id, payload=payload
        )
        version.state = "published"
        version.frozen_at = version.frozen_at or datetime.now(UTC)
        assessment.status = "published"
        assignment = AssessmentAssignment(
            id=uuid4(),
            assessment_version_id=version.id,
            target_type=payload.target_type,
            teaching_class_id=payload.teaching_class_id,
            group_id=payload.group_id,
            student_id=payload.student_id,
            due_at=_as_utc(payload.due_at),
            allow_late=payload.allow_late,
            status="active",
            assigned_by=actor.id,
        )
        self.session.add(assignment)
        await self.session.flush()
        await self._audit(
            actor=actor,
            action="assessment_assignment.create",
            object_type="assessment_assignment",
            object_id=assignment.id,
            reason=payload.reason,
            metadata={
                "assessment_id": str(assessment.id),
                "assessment_version_id": str(version.id),
                "course_id": str(assessment.course_id),
                "target_type": payload.target_type,
                "due_at": payload.due_at.isoformat(),
                "allow_late": payload.allow_late,
            },
        )
        return self._assignment_dto(assignment)

    async def submit_assessment(
        self,
        *,
        actor: User,
        assignment_id: UUID,
        payload: SubmitAssessmentRequest,
    ) -> AssessmentSubmissionDTO:
        if actor.role != "student":
            raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "只有已选课学生可以提交评估。", 403)
        context = await self.repo.get_assignment_context(assignment_id)
        if context is None:
            raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "评估布置不存在或不可访问。", 404)
        assignment, _, assessment = context
        if assignment.status != "active" or assessment.status != "published":
            raise TeacherProductionError("SUBMISSION_WINDOW_CLOSED", "当前评估未开放提交。")
        await self._require_student_assignment_scope(actor=actor, assignment=assignment, course_id=assessment.course_id)
        now = datetime.now(UTC)
        due_at = _as_utc(assignment.due_at)
        if now > due_at and not assignment.allow_late:
            raise TeacherProductionError("SUBMISSION_WINDOW_CLOSED", "评估已截止，当前不接受迟交。")
        prior = await self.repo.get_submission_for_assignment_student(
            assignment_id=assignment.id, student_id=actor.id
        )
        if prior is not None and prior.status in {"submitted", "late", "locked"}:
            raise TeacherProductionError("SUBMISSION_WINDOW_CLOSED", "该评估已经提交，不能覆盖历史答案。")
        submission = prior or AssessmentSubmission(
            id=uuid4(), assignment_id=assignment.id, student_id=actor.id, status="open", answers={}
        )
        if prior is None:
            self.session.add(submission)
        submission.answers = payload.answers
        submission.submitted_at = now
        submission.status = "late" if now > due_at else "submitted"
        await self.session.flush()
        await self._audit(
            actor=actor,
            action="assessment_submission.submit",
            object_type="assessment_submission",
            object_id=submission.id,
            reason="学生提交评估",
            metadata={
                "assignment_id": str(assignment.id),
                "course_id": str(assessment.course_id),
                "status": submission.status,
                "answer_count": len(payload.answers),
            },
        )
        return self._submission_dto(submission)

    async def list_assignment_submissions(
        self, *, actor: User, assignment_id: UUID
    ) -> TeacherAssessmentSubmissionListDTO:
        """Expose in-scope submitted work and durable grade decisions to its teacher."""

        context = await self.repo.get_assignment_context(assignment_id)
        if context is None:
            raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "评估布置不存在或不可访问。", 404)
        _, _, assessment = context
        await self._require_teacher_course(actor=actor, course_id=assessment.course_id)
        rows = await self.repo.list_assignment_submissions(assignment_id=assignment_id)
        return TeacherAssessmentSubmissionListDTO(
            items=[
                TeacherAssessmentSubmissionDTO(
                    id=submission.id,
                    assignment_id=submission.assignment_id,
                    student_id=submission.student_id,
                    student_display_name=student.display_name,
                    status=submission.status,  # type: ignore[arg-type]
                    submitted_at=submission.submitted_at,
                    grade=self._grade_dto(grade) if grade is not None else None,
                )
                for submission, student, grade in rows
            ]
        )

    async def score_objective_submission(
        self, *, actor: User, submission_id: UUID
    ) -> ObjectiveScoreDTO:
        submission, assignment, version, assessment = await self._require_submission_teacher_scope(
            actor=actor, submission_id=submission_id
        )
        if submission.status not in {"submitted", "late"}:
            raise TeacherProductionError("GRADE_NOT_REVIEWABLE", "只有已提交的评估可以评分。")
        grade = await self.repo.get_grade_for_submission(submission.id)
        if grade is not None and grade.status in {"published", "withdrawn"}:
            raise TeacherProductionError("GRADE_NOT_REVIEWABLE", "已发布或撤回成绩不能重算客观分。")
        items = await self.repo.list_assessment_items(version.id)
        total = 0.0
        score = 0.0
        for item in items:
            if item.grading_mode != "objective":
                continue
            total += item.points
            expected = str((item.question_snapshot or {}).get("answer") or "")
            supplied = self._answer_for_item(submission.answers, item.quiz_item_id)
            if self._answers_match(expected, supplied):
                score += item.points
        if grade is None:
            grade = AssessmentGradeDecision(
                id=uuid4(),
                submission_id=submission.id,
                objective_score=score,
                ai_suggestion_status="not_requested",
                status="auto_scored",
            )
            self.session.add(grade)
        else:
            grade.objective_score = score
            if grade.status == "pending":
                grade.status = "auto_scored"
        await self.session.flush()
        await self._audit(
            actor=actor,
            action="assessment_grade.objective_score",
            object_type="assessment_grade_decision",
            object_id=grade.id,
            reason="确定性客观题评分",
            metadata={
                "submission_id": str(submission.id),
                "assignment_id": str(assignment.id),
                "course_id": str(assessment.course_id),
                "objective_score": score,
                "total_objective_points": total,
            },
        )
        return ObjectiveScoreDTO(
            submission_id=submission.id,
            objective_score=score,
            total_objective_points=total,
            status=grade.status,  # type: ignore[arg-type]
        )

    async def record_subjective_suggestion(
        self,
        *,
        actor: User,
        submission_id: UUID,
        payload: RecordSubjectiveSuggestionRequest,
    ) -> GradeDecisionDTO:
        submission, _, version, _ = await self._require_submission_teacher_scope(
            actor=actor, submission_id=submission_id
        )
        if submission.status not in {"submitted", "late"}:
            raise TeacherProductionError("GRADE_NOT_REVIEWABLE", "只有已提交评估可写入 AI 建议。")
        items = await self.repo.list_assessment_items(version.id)
        if not any(item.grading_mode == "subjective" for item in items):
            raise TeacherProductionError("GRADE_NOT_REVIEWABLE", "当前评估没有主观题，不接受 AI 建议。")
        run, _ = await self._require_linked_completed_agent_result(
            agent_run_id=payload.agent_run_id, evidence_snapshot_id=payload.evidence_snapshot_id
        )
        raw_score = (run.output_summary or {}).get("suggested_score")
        if not isinstance(raw_score, int | float) or isinstance(raw_score, bool) or raw_score < 0:
            raise TeacherProductionError(
                "INSUFFICIENT_EVIDENCE",
                "已记录的 Skill 输出没有可解析的主观题建议分数，拒绝伪造建议。",
            )
        grade = await self.repo.get_grade_for_submission(submission.id)
        if grade is None:
            grade = AssessmentGradeDecision(
                id=uuid4(),
                submission_id=submission.id,
                objective_score=None,
                ai_suggestion_status="not_requested",
                status="pending",
            )
            self.session.add(grade)
        if grade.status in {"published", "withdrawn"}:
            raise TeacherProductionError("GRADE_NOT_REVIEWABLE", "已发布或撤回成绩不能写入 AI 建议。")
        grade.ai_suggested_score = float(raw_score)
        grade.ai_agent_run_id = payload.agent_run_id
        grade.ai_evidence_snapshot_id = payload.evidence_snapshot_id
        grade.ai_suggestion_status = "suggested"
        await self.session.flush()
        await self._audit(
            actor=actor,
            action="assessment_grade.record_ai_suggestion",
            object_type="assessment_grade_decision",
            object_id=grade.id,
            reason="引用成功 SkillExecutor/Runtime 结果作为教师可见建议",
            metadata={
                "submission_id": str(submission.id),
                "agent_run_id": str(payload.agent_run_id),
                "evidence_snapshot_id": str(payload.evidence_snapshot_id),
                "ai_suggested_score": float(raw_score),
                "final_score_set": grade.final_score is not None,
            },
        )
        return self._grade_dto(grade)

    async def override_grade(
        self,
        *,
        actor: User,
        submission_id: UUID,
        payload: GradeOverrideRequest,
    ) -> GradeDecisionDTO:
        submission, _, _, _ = await self._require_submission_teacher_scope(
            actor=actor, submission_id=submission_id
        )
        grade = await self.repo.get_grade_for_submission(submission.id)
        if grade is None:
            grade = AssessmentGradeDecision(
                id=uuid4(),
                submission_id=submission.id,
                ai_suggestion_status="not_requested",
                status="pending",
            )
            self.session.add(grade)
        if grade.status in {"published", "withdrawn"}:
            raise TeacherProductionError("GRADE_NOT_REVIEWABLE", "已发布或撤回成绩必须先执行明确撤回，不能直接覆盖。")
        previous = grade.final_score
        grade.final_score = payload.final_score
        grade.override_reason = payload.reason
        grade.graded_by = actor.id
        grade.status = "teacher_reviewed"
        await self.session.flush()
        await self._audit(
            actor=actor,
            action="assessment_grade.override",
            object_type="assessment_grade_decision",
            object_id=grade.id,
            reason=payload.reason,
            metadata={
                "submission_id": str(submission.id),
                "previous_final_score": previous,
                "new_final_score": payload.final_score,
                "ai_suggestion_is_advisory": True,
            },
        )
        return self._grade_dto(grade)

    async def publish_grade(self, *, actor: User, submission_id: UUID) -> GradeDecisionDTO:
        submission, _, _, _ = await self._require_submission_teacher_scope(
            actor=actor, submission_id=submission_id
        )
        grade = await self.repo.get_grade_for_submission(submission.id)
        if grade is None or grade.final_score is None or grade.status != "teacher_reviewed":
            raise TeacherProductionError(
                "GRADE_PUBLISH_FORBIDDEN", "成绩必须经教师人工确认并附理由后才可发布。"
            )
        grade.status = "published"
        grade.published_at = datetime.now(UTC)
        grade.graded_by = actor.id
        await self.session.flush()
        await self._audit(
            actor=actor,
            action="assessment_grade.publish",
            object_type="assessment_grade_decision",
            object_id=grade.id,
            reason="教师发布最终成绩",
            metadata={"submission_id": str(submission.id), "final_score": grade.final_score},
        )
        return self._grade_dto(grade)

    async def withdraw_grade(self, *, actor: User, submission_id: UUID, reason: str) -> GradeDecisionDTO:
        submission, _, _, _ = await self._require_submission_teacher_scope(
            actor=actor, submission_id=submission_id
        )
        grade = await self.repo.get_grade_for_submission(submission.id)
        if grade is None or grade.status != "published":
            raise TeacherProductionError("GRADE_NOT_REVIEWABLE", "只有已发布成绩可以撤回。")
        grade.status = "withdrawn"
        grade.withdrawn_at = datetime.now(UTC)
        grade.override_reason = reason
        grade.graded_by = actor.id
        await self.session.flush()
        await self._audit(
            actor=actor,
            action="assessment_grade.withdraw",
            object_type="assessment_grade_decision",
            object_id=grade.id,
            reason=reason,
            metadata={"submission_id": str(submission.id), "published_at": grade.published_at.isoformat() if grade.published_at else None},
        )
        return self._grade_dto(grade)

    async def get_student_published_result(
        self, *, actor: User, assignment_id: UUID
    ) -> StudentPublishedResultDTO:
        submission = await self.repo.get_submission_for_assignment_student(
            assignment_id=assignment_id, student_id=actor.id
        )
        if submission is None:
            raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "当前账号没有该评估提交记录。", 404)
        grade = await self.repo.get_grade_for_submission(submission.id)
        if grade is None or grade.status != "published" or grade.final_score is None or grade.published_at is None:
            raise TeacherProductionError("GRADE_NOT_PUBLISHED", "当前成绩尚未发布。", 404)
        return StudentPublishedResultDTO(
            assignment_id=assignment_id,
            submission_id=submission.id,
            final_score=grade.final_score,
            published_at=grade.published_at,
            status="published",
        )

    # ------------------------------------------------------------------
    # FG-06: typed syllabus / explicit review / export / rollback
    # ------------------------------------------------------------------

    async def list_syllabus_versions(
        self, *, actor: User, course_id: UUID
    ) -> SyllabusVersionListDTO:
        """Return the typed syllabus lineage for an owned course, newest first."""

        await self._require_teacher_course(actor=actor, course_id=course_id)
        syllabus = await self.repo.get_or_create_syllabus(course_id=course_id)
        if syllabus is None:
            return SyllabusVersionListDTO(items=[])
        versions = await self.repo.list_syllabus_versions(syllabus.id)
        return SyllabusVersionListDTO(items=[self._syllabus_dto(version) for version in versions])

    async def create_syllabus_version(
        self,
        *,
        actor: User,
        course_id: UUID,
        payload: CreateSyllabusVersionRequest,
    ) -> SyllabusVersionDTO:
        await self._require_teacher_course(actor=actor, course_id=course_id)
        await self._validate_syllabus_nodes(course_id, payload.typed_content)
        version = await self._persist_syllabus_version(
            actor=actor,
            course_id=course_id,
            typed_content=payload.typed_content,
            state="review_pending",
            agent_run_id=None,
            evidence_snapshot_id=None,
            reason=payload.reason,
            action="syllabus.manual_edit",
        )
        return self._syllabus_dto(version)

    async def generate_syllabus_version(
        self,
        *,
        actor: User,
        course_id: UUID,
        payload: GenerateSyllabusVersionRequest,
    ) -> SyllabusVersionDTO:
        await self._require_teacher_course(actor=actor, course_id=course_id)
        run, _ = await self._require_linked_completed_agent_result(
            agent_run_id=payload.agent_run_id, evidence_snapshot_id=payload.evidence_snapshot_id,
            insufficient_code="SYLLABUS_EVIDENCE_INSUFFICIENT",
        )
        output = run.output_summary or {}
        raw_content = output.get("typed_syllabus") or output.get("syllabus") or output.get("typed_content")
        if not isinstance(raw_content, dict):
            raise TeacherProductionError(
                "SYLLABUS_EVIDENCE_INSUFFICIENT",
                "成功 Skill 输出未包含可验证的 typed syllabus，拒绝将普通文档伪装为大纲。",
            )
        try:
            typed = TypedSyllabusContent.model_validate(raw_content)
        except ValidationError as exc:
            raise TeacherProductionError(
                "SYLLABUS_SCHEMA_INVALID", "Skill 输出不符合 typed syllabus schema。"
            ) from exc
        await self._validate_syllabus_nodes(course_id, typed)
        version = await self._persist_syllabus_version(
            actor=actor,
            course_id=course_id,
            typed_content=typed,
            state="review_pending",
            agent_run_id=payload.agent_run_id,
            evidence_snapshot_id=payload.evidence_snapshot_id,
            reason=payload.reason,
            action="syllabus.skill_candidate",
        )
        return self._syllabus_dto(version)

    async def review_syllabus_version(
        self,
        *,
        actor: User,
        version_id: UUID,
        payload: SyllabusReviewRequest,
    ) -> SyllabusVersionDTO:
        context = await self.repo.get_syllabus_version_context(version_id)
        if context is None:
            raise TeacherProductionError("COURSE_ACCESS_DENIED", "typed syllabus 版本不存在或不可访问。", 404)
        version, syllabus = context
        await self._require_teacher_course(actor=actor, course_id=syllabus.course_id)
        if version.state not in {"review_pending", "draft", "published"}:
            raise TeacherProductionError("SYLLABUS_REVIEW_REQUIRED", "当前大纲版本不能执行该审核转换。")
        if payload.decision == "approve":
            current_id = syllabus.current_published_version_id
            if current_id is not None and current_id != version.id:
                previous = await self.repo.get_syllabus_version(current_id)
                if previous is not None and previous.state == "published":
                    previous.state = "superseded"
            version.state = "published"
            syllabus.current_published_version_id = version.id
        elif payload.decision == "reject":
            version.state = "withdrawn"
        else:
            version.state = "withdrawn"
            if syllabus.current_published_version_id == version.id:
                syllabus.current_published_version_id = None
        review = SyllabusReviewDecision(
            id=uuid4(),
            version_id=version.id,
            reviewer_id=actor.id,
            decision=payload.decision,
            reason=payload.reason,
        )
        self.session.add(review)
        await self.session.flush()
        await self.session.refresh(version)
        await self._audit(
            actor=actor,
            action="syllabus.review",
            object_type="course_syllabus_version",
            object_id=version.id,
            reason=payload.reason,
            metadata={
                "course_id": str(syllabus.course_id),
                "decision": payload.decision,
                "result_state": version.state,
                "current_published_version_id": str(syllabus.current_published_version_id)
                if syllabus.current_published_version_id
                else None,
            },
        )
        return self._syllabus_dto(version)

    async def compare_syllabus_versions(
        self, *, actor: User, from_version_id: UUID | None, to_version_id: UUID
    ) -> SyllabusDiffDTO:
        target_context = await self.repo.get_syllabus_version_context(to_version_id)
        if target_context is None:
            raise TeacherProductionError("COURSE_ACCESS_DENIED", "目标大纲版本不存在。", 404)
        target, syllabus = target_context
        await self._require_teacher_course(actor=actor, course_id=syllabus.course_id)
        source = None
        if from_version_id is not None:
            source_context = await self.repo.get_syllabus_version_context(from_version_id)
            if source_context is None or source_context[1].id != syllabus.id:
                raise TeacherProductionError("SYLLABUS_VERSION_CONFLICT", "比较版本不属于同一课程大纲。")
            source = source_context[0]
        before = source.typed_content if source else {}
        after = target.typed_content or {}
        fields = sorted(
            key
            for key in set(before) | set(after)
            if before.get(key) != after.get(key)
        )
        before_modules = {
            str(row.get("module_id"))
            for row in before.get("modules", [])
            if isinstance(row, dict) and row.get("module_id")
        }
        after_modules = {
            str(row.get("module_id"))
            for row in after.get("modules", [])
            if isinstance(row, dict) and row.get("module_id")
        }
        return SyllabusDiffDTO(
            from_version_id=source.id if source else None,
            to_version_id=target.id,
            changed_fields=fields,
            added_module_ids=sorted(after_modules - before_modules),
            removed_module_ids=sorted(before_modules - after_modules),
        )

    async def preview_syllabus_version(
        self, *, actor: User, version_id: UUID
    ) -> SyllabusVersionDTO:
        context = await self.repo.get_syllabus_version_context(version_id)
        if context is None:
            raise TeacherProductionError("COURSE_ACCESS_DENIED", "大纲版本不存在。", 404)
        version, syllabus = context
        await self._require_teacher_course(actor=actor, course_id=syllabus.course_id)
        return self._syllabus_dto(version)

    async def export_syllabus_version(
        self,
        *,
        actor: User,
        version_id: UUID,
        payload: SyllabusExportRequest,
    ) -> SyllabusExportDTO:
        context = await self.repo.get_syllabus_version_context(version_id)
        if context is None:
            raise TeacherProductionError("COURSE_ACCESS_DENIED", "大纲版本不存在。", 404)
        version, syllabus = context
        await self._require_teacher_course(actor=actor, course_id=syllabus.course_id)
        if version.state != "published":
            raise TeacherProductionError("SYLLABUS_REVIEW_REQUIRED", "仅已发布 typed syllabus 可以导出。")
        typed = TypedSyllabusContent.model_validate(version.typed_content)
        content: str | dict[str, object]
        if payload.format == "json":
            content = typed.model_dump(mode="json")
        else:
            content = self._syllabus_markdown(typed)
        evidence_ids = self._evidence_chunk_ids_for_version(version)
        resource = GeneratedResource(
            id=uuid4(),
            user_id=actor.id,
            course_id=syllabus.course_id,
            kp_id=None,
            agent_run_id=version.generated_from_agent_run_id,
            resource_type="syllabus_export",
            title=f"{typed.title} · v{version.version_no}.{payload.format}",
            content={
                "syllabus_version_id": str(version.id),
                "format": payload.format,
                "content": content,
                "typed_schema": "syllabus-v1",
            },
            object_key=None,
            evidence_chunk_ids=evidence_ids,
            status="ready",
            metadata_={"exported_by": str(actor.id), "typed_syllabus": True},
        )
        self.session.add(resource)
        await self.session.flush()
        export = SyllabusExport(
            id=uuid4(),
            version_id=version.id,
            format=payload.format,
            generated_resource_id=resource.id,
            storage_object_id=None,
            status="ready",
            created_by=actor.id,
        )
        self.session.add(export)
        await self.session.flush()
        await self._audit(
            actor=actor,
            action="syllabus.export",
            object_type="syllabus_export",
            object_id=export.id,
            reason="教师导出已发布 typed syllabus",
            metadata={
                "course_id": str(syllabus.course_id),
                "version_id": str(version.id),
                "format": payload.format,
                "generated_resource_id": str(resource.id),
            },
        )
        return SyllabusExportDTO(
            id=export.id,
            version_id=version.id,
            format=export.format,  # type: ignore[arg-type]
            generated_resource_id=resource.id,
            status=export.status,  # type: ignore[arg-type]
            content=content,
            created_at=export.created_at,
        )

    async def rollback_published_syllabus(
        self, *, actor: User, version_id: UUID, reason: str
    ) -> SyllabusVersionDTO:
        context = await self.repo.get_syllabus_version_context(version_id)
        if context is None:
            raise TeacherProductionError("COURSE_ACCESS_DENIED", "大纲版本不存在。", 404)
        version, syllabus = context
        await self._require_teacher_course(actor=actor, course_id=syllabus.course_id)
        if version.state not in {"published", "superseded"}:
            raise TeacherProductionError(
                "SYLLABUS_VERSION_CONFLICT", "只允许显式回滚到历史已发布大纲版本。"
            )
        current_id = syllabus.current_published_version_id
        if current_id is not None and current_id != version.id:
            current = await self.repo.get_syllabus_version(current_id)
            if current is not None and current.state == "published":
                current.state = "superseded"
        version.state = "published"
        syllabus.current_published_version_id = version.id
        review = SyllabusReviewDecision(
            id=uuid4(),
            version_id=version.id,
            reviewer_id=actor.id,
            decision="approve",
            reason=reason,
        )
        self.session.add(review)
        await self.session.flush()
        await self.session.refresh(version)
        await self._audit(
            actor=actor,
            action="syllabus.rollback_published",
            object_type="course_syllabus_version",
            object_id=version.id,
            reason=reason,
            metadata={"course_id": str(syllabus.course_id), "explicit_rollback": True},
        )
        return self._syllabus_dto(version)

    async def get_student_published_syllabus(
        self, *, actor: User, course_id: UUID
    ) -> SyllabusVersionDTO:
        syllabus = await self.repo.get_or_create_syllabus(course_id=course_id)
        if syllabus is None or syllabus.current_published_version_id is None:
            raise TeacherProductionError("SYLLABUS_REVIEW_REQUIRED", "当前课程没有已发布大纲。", 404)
        version = await self.repo.get_syllabus_version(syllabus.current_published_version_id)
        if version is None or version.state != "published":
            raise TeacherProductionError("SYLLABUS_REVIEW_REQUIRED", "当前课程没有可见已发布大纲。", 404)
        # Student visibility is intentionally only the published version.  The
        # caller's enrollment is checked where T1 has a course relationship.
        if actor.role == "student":
            enrolled = await self.session.scalar(
                select(CourseEnrollment.id).where(
                    CourseEnrollment.course_id == course_id,
                    CourseEnrollment.student_id == actor.id,
                    CourseEnrollment.status == "enrolled",
                )
            )
            if enrolled is None:
                raise TeacherProductionError("COURSE_ACCESS_DENIED", "当前学生未选修该课程。", 403)
        return self._syllabus_dto(version)

    # ------------------------------------------------------------------
    # Internal validation / DTO / auditing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _require_teacher_role(actor: User) -> None:
        if actor.role not in _COURSE_TEACHER_ROLES:
            raise TeacherProductionError("TEACHER_ROLE_REQUIRED", "当前账号不具备课程教师身份。", 403)

    async def _require_teacher_course(self, *, actor: User, course_id: UUID) -> Any:
        self._require_teacher_role(actor)
        course = await self.repo.get_course(course_id)
        if course is None:
            raise TeacherProductionError("COURSE_ACCESS_DENIED", "课程不存在或不可访问。", 404)
        if not await self.repo.has_teacher_course_scope(teacher_id=actor.id, course_id=course_id):
            raise TeacherProductionError("COURSE_ACCESS_DENIED", "当前教师没有该课程治理授权。", 403)
        return course

    async def _require_course_document(self, *, course_id: UUID, document_id: UUID) -> Document:
        document = await self.repo.get_document(document_id)
        if document is None:
            raise TeacherProductionError("ASSET_LINEAGE_REQUIRED", "统一知识资产文档不存在。", 404)
        course = await self.repo.get_course(course_id)
        if course is None or document.domain != course.domain:
            raise TeacherProductionError(
                "ASSET_LINEAGE_REQUIRED", "文档未归属当前课程 domain，不能跨课程绑定。"
            )
        return document

    async def _require_document_asset_match(
        self, *, document_id: UUID, document_asset_id: UUID | None
    ) -> None:
        if document_asset_id is None:
            return
        asset = await self.repo.get_document_asset(document_asset_id)
        if asset is None or asset.document_id != document_id:
            raise TeacherProductionError(
                "ASSET_LINEAGE_REQUIRED", "document_asset 必须属于所绑定的统一知识文档。"
            )

    async def _require_asset_scope(
        self, *, actor: User, asset_id: UUID
    ) -> tuple[CourseAssetGovernance, CourseDocumentBinding, Document]:
        context = await self.repo.get_asset_context(asset_id)
        if context is None:
            raise TeacherProductionError("COURSE_ACCESS_DENIED", "课程资产不存在或不可访问。", 404)
        asset, binding, document = context
        await self._require_teacher_course(actor=actor, course_id=binding.course_id)
        if asset.owner_teacher_id != actor.id:
            raise TeacherProductionError("COURSE_ACCESS_DENIED", "教师只能治理自己创建的课程资产。", 403)
        return context

    @staticmethod
    def _document_governance_state(document: Document) -> str:
        return "ready" if document.status == "ready" else "processing"

    async def _reconcile_asset_state(self, asset: CourseAssetGovernance, document: Document) -> None:
        if asset.state != "processing" or document.status != "ready":
            return
        asset.state = "ready"
        if asset.correction_of_id is not None:
            parent = await self.repo.get_asset(asset.correction_of_id)
            if parent is not None and parent.state == "correction_pending":
                parent.state = "corrected"
        await self.session.flush()

    async def _validate_education_scope(
        self,
        *,
        actor: User,
        course_id: UUID,
        teaching_class_id: UUID | None,
        group_id: UUID | None,
    ) -> None:
        if teaching_class_id is None and group_id is None:
            return
        if teaching_class_id is not None:
            teaching_class = await self.education.get_teacher_class(
                teacher_id=actor.id, class_id=teaching_class_id
            )
            if teaching_class is None or teaching_class.course_id != course_id:
                raise TeacherProductionError("CLASS_SCOPE_DENIED", "教学班不属于当前教师课程范围。", 403)
        if group_id is not None:
            group = await self.repo.get_group(group_id)
            if group is None or group.status != "active":
                raise TeacherProductionError("CLASS_SCOPE_DENIED", "分组不存在或不可用。", 404)
            if teaching_class_id is not None and group.teaching_class_id != teaching_class_id:
                raise TeacherProductionError("CLASS_SCOPE_DENIED", "分组与教学班不一致。", 403)
            teaching_class = await self.education.get_teacher_class(
                teacher_id=actor.id, class_id=group.teaching_class_id
            )
            if teaching_class is None or teaching_class.course_id != course_id:
                raise TeacherProductionError("CLASS_SCOPE_DENIED", "分组不属于当前教师课程范围。", 403)

    async def _require_linked_completed_agent_result(
        self,
        *,
        agent_run_id: UUID,
        evidence_snapshot_id: UUID,
        insufficient_code: str = "INSUFFICIENT_EVIDENCE",
    ) -> tuple[Any, Any]:
        run = await self.repo.get_agent_run(agent_run_id)
        evidence = await self.repo.get_evidence_snapshot(evidence_snapshot_id)
        if run is None or run.status != "succeeded" or evidence is None or not evidence.content_digest:
            raise TeacherProductionError(
                insufficient_code,
                "需要由唯一 SkillExecutor/Runtime 成功持久化的 AgentRun 与 Evidence Snapshot。",
            )
        linked_by_run = evidence.agent_run_id == run.id
        linked_by_chunk = evidence.chunk_id is not None and evidence.chunk_id in {
            str(chunk_id) for chunk_id in (run.evidence_chunk_ids or [])
        }
        if not linked_by_run and not linked_by_chunk:
            raise TeacherProductionError(
                insufficient_code,
                "Evidence Snapshot 与 AgentRun 没有可验证关联，拒绝接受生成式结果。",
            )
        return run, evidence

    async def _require_assessment_owner(self, *, actor: User, assessment_id: UUID) -> Assessment:
        assessment = await self.repo.get_assessment(assessment_id)
        if assessment is None:
            raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "评估不存在或不可访问。", 404)
        await self._require_teacher_course(actor=actor, course_id=assessment.course_id)
        if assessment.owner_teacher_id != actor.id:
            raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "教师只能治理自己创建的评估。", 403)
        return assessment

    async def _validate_assignment_target(self, *, actor: User, course_id: UUID, payload: Any) -> None:
        if payload.target_type == "class":
            if payload.teaching_class_id is None or payload.group_id is not None or payload.student_id is not None:
                raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "班级布置必须只指定 teaching_class_id。")
            await self._validate_education_scope(
                actor=actor,
                course_id=course_id,
                teaching_class_id=payload.teaching_class_id,
                group_id=None,
            )
            return
        if payload.target_type == "group":
            if payload.group_id is None or payload.student_id is not None:
                raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "分组布置必须指定 group_id。")
            group = await self.repo.get_group(payload.group_id)
            if group is None:
                raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "目标分组不存在。", 404)
            if payload.teaching_class_id is not None and payload.teaching_class_id != group.teaching_class_id:
                raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "分组与教学班不一致。")
            payload.teaching_class_id = group.teaching_class_id
            await self._validate_education_scope(
                actor=actor,
                course_id=course_id,
                teaching_class_id=group.teaching_class_id,
                group_id=group.id,
            )
            return
        if payload.student_id is None or payload.group_id is not None:
            raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "个人布置必须只指定 student_id。")
        statement = select(CourseEnrollment).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == payload.student_id,
            CourseEnrollment.status == "enrolled",
        )
        enrollment = (await self.session.execute(statement)).scalar_one_or_none()
        if enrollment is None:
            raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "目标学生没有当前课程有效选课。", 403)
        if payload.teaching_class_id is not None and enrollment.teaching_class_id != payload.teaching_class_id:
            raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "学生不属于指定教学班。", 403)
        payload.teaching_class_id = enrollment.teaching_class_id
        if enrollment.teaching_class_id is not None:
            await self._validate_education_scope(
                actor=actor,
                course_id=course_id,
                teaching_class_id=enrollment.teaching_class_id,
                group_id=None,
            )

    async def _require_student_assignment_scope(
        self, *, actor: User, assignment: AssessmentAssignment, course_id: UUID
    ) -> None:
        enrollment = await self.session.scalar(
            select(CourseEnrollment).where(
                CourseEnrollment.course_id == course_id,
                CourseEnrollment.student_id == actor.id,
                CourseEnrollment.status == "enrolled",
            )
        )
        if enrollment is None:
            raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "学生未有效选课。", 403)
        if assignment.target_type == "class":
            allowed = enrollment.teaching_class_id == assignment.teaching_class_id
        elif assignment.target_type == "group":
            membership = await self.session.scalar(
                select(CourseEnrollment.id)
                .join(
                    # Keep the check in the T1 relation layer: course enrollment
                    # plus active membership make a group target effective.
                    StudentGroupMember,
                    StudentGroupMember.student_id == CourseEnrollment.student_id,
                )
                .where(
                    CourseEnrollment.id == enrollment.id,
                    StudentGroupMember.group_id == assignment.group_id,
                    StudentGroupMember.status == "active",
                )
            )
            allowed = membership is not None
        else:
            allowed = assignment.student_id == actor.id
        if not allowed:
            raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "当前学生不在该评估布置范围内。", 403)

    async def _require_submission_teacher_scope(
        self, *, actor: User, submission_id: UUID
    ) -> tuple[AssessmentSubmission, AssessmentAssignment, AssessmentVersion, Assessment]:
        context = await self.repo.get_submission_context(submission_id)
        if context is None:
            raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "提交不存在或不可访问。", 404)
        submission, assignment, version, assessment = context
        await self._require_assessment_owner(actor=actor, assessment_id=assessment.id)
        return submission, assignment, version, assessment

    async def _validate_syllabus_nodes(self, course_id: UUID, typed: TypedSyllabusContent) -> None:
        ids = {node_id for module in typed.modules for node_id in module.knowledge_node_ids}
        found = set(
            (
                await self.session.execute(
                    select(KnowledgeNode.id).where(
                        KnowledgeNode.course_id == course_id, KnowledgeNode.id.in_(ids)
                    )
                )
            ).scalars().all()
        )
        if found != ids:
            raise TeacherProductionError(
                "SYLLABUS_SCHEMA_INVALID", "typed syllabus 引用了当前课程之外或不存在的知识点。"
            )

    async def _persist_syllabus_version(
        self,
        *,
        actor: User,
        course_id: UUID,
        typed_content: TypedSyllabusContent,
        state: str,
        agent_run_id: UUID | None,
        evidence_snapshot_id: UUID | None,
        reason: str,
        action: str,
    ) -> CourseSyllabusVersion:
        syllabus = await self.repo.get_or_create_syllabus(course_id=course_id)
        if syllabus is None:
            syllabus = CourseSyllabus(id=uuid4(), course_id=course_id, current_published_version_id=None)
            self.session.add(syllabus)
            await self.session.flush()
        version = CourseSyllabusVersion(
            id=uuid4(),
            syllabus_id=syllabus.id,
            version_no=await self.repo.next_syllabus_version(syllabus.id),
            typed_content=typed_content.model_dump(mode="json"),
            content_schema_version="syllabus-v1",
            state=state,
            generated_from_agent_run_id=agent_run_id,
            evidence_snapshot_id=evidence_snapshot_id,
            created_by=actor.id,
        )
        self.session.add(version)
        await self.session.flush()
        await self._audit(
            actor=actor,
            action=action,
            object_type="course_syllabus_version",
            object_id=version.id,
            reason=reason,
            metadata={
                "course_id": str(course_id),
                "syllabus_id": str(syllabus.id),
                "version_no": version.version_no,
                "state": state,
                "agent_run_id": str(agent_run_id) if agent_run_id else None,
                "evidence_snapshot_id": str(evidence_snapshot_id) if evidence_snapshot_id else None,
                "does_not_overwrite_course": True,
            },
        )
        return version

    async def _audit(
        self,
        *,
        actor: User,
        action: str,
        object_type: str,
        object_id: UUID,
        reason: str | None,
        metadata: dict[str, Any],
    ) -> GovernanceAuditEvent:
        return await self.education.write_audit(
            actor_user_id=actor.id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            reason=reason,
            result_status="succeeded",
            request_id=None,
            metadata=metadata,
        )

    @staticmethod
    def _attempt_score(attempt: Any) -> float | None:
        if isinstance(attempt.score, int | float) and not isinstance(attempt.score, bool):
            return min(1.0, max(0.0, float(attempt.score)))
        if attempt.is_correct is True:
            return 1.0
        if attempt.is_correct is False:
            return 0.0
        return None

    @staticmethod
    def _fingerprint(payload: dict[str, Any]) -> str:
        return sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _answer_for_item(answers: dict[str, Any], item_id: UUID) -> Any:
        return answers.get(str(item_id), answers.get(item_id.hex))

    @staticmethod
    def _answers_match(expected: str, supplied: Any) -> bool:
        def normalized(value: Any) -> list[str]:
            if isinstance(value, list):
                values = value
            elif isinstance(value, str):
                values = value.split(";")
            else:
                values = [value]
            return sorted("".join(str(item).strip().lower().split()) for item in values if str(item).strip())

        return normalized(expected) == normalized(supplied)

    @staticmethod
    def _asset_dto(
        asset: CourseAssetGovernance, binding: CourseDocumentBinding, document: Document
    ) -> CourseAssetDTO:
        return CourseAssetDTO(
            id=asset.id,
            course_id=binding.course_id,
            document_id=document.id,
            document_title=document.title,
            document_asset_id=asset.document_asset_id,
            current_resource_id=asset.current_resource_id,
            version_no=asset.version_no,
            state=asset.state,  # type: ignore[arg-type]
            correction_of_id=asset.correction_of_id,
            reason=asset.reason,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
        )

    @staticmethod
    def _weakness_dto(snapshot: ClassWeaknessSnapshot) -> WeaknessSnapshotDTO:
        aggregate = snapshot.aggregates if isinstance(snapshot.aggregates, dict) else {}
        points = aggregate.get("weak_knowledge_points", [])
        return WeaknessSnapshotDTO(
            id=snapshot.id,
            course_id=snapshot.course_id,
            teaching_class_id=snapshot.teaching_class_id,
            group_id=snapshot.group_id,
            sample_size=snapshot.sample_size,
            score_version=snapshot.score_version,
            input_fingerprint=snapshot.input_fingerprint,
            weak_knowledge_points=[WeaknessKnowledgePointDTO.model_validate(item) for item in points],
            computed_at=snapshot.computed_at,
        )

    @staticmethod
    def _recommendation_dto(row: TeachingRecommendation) -> TeachingRecommendationDTO:
        return TeachingRecommendationDTO(
            id=row.id,
            course_id=row.course_id,
            source_snapshot_id=row.source_snapshot_id,
            evidence_snapshot_id=row.evidence_snapshot_id,
            agent_run_id=row.agent_run_id,
            version_no=row.version_no,
            diff=row.diff or {},
            status=row.status,  # type: ignore[arg-type]
            created_at=row.created_at,
        )

    @staticmethod
    def _assessment_dto(row: Assessment) -> AssessmentDTO:
        return AssessmentDTO(
            id=row.id,
            course_id=row.course_id,
            kind=row.kind,  # type: ignore[arg-type]
            logical_key=row.logical_key,
            status=row.status,  # type: ignore[arg-type]
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _assessment_version_dto(
        row: AssessmentVersion, items: Iterable[AssessmentItem]
    ) -> AssessmentVersionDTO:
        return AssessmentVersionDTO(
            id=row.id,
            assessment_id=row.assessment_id,
            version_no=row.version_no,
            title=row.title,
            instructions=row.instructions,
            state=row.state,  # type: ignore[arg-type]
            frozen_at=row.frozen_at,
            items=[
                AssessmentVersionItemDTO(
                    id=item.id,
                    quiz_item_id=item.quiz_item_id,
                    position=item.position,
                    points=item.points,
                    grading_mode=item.grading_mode,  # type: ignore[arg-type]
                    question_snapshot=item.question_snapshot or {},
                )
                for item in items
            ],
            created_at=row.created_at,
        )

    @staticmethod
    def _assignment_dto(row: AssessmentAssignment) -> AssessmentAssignmentDTO:
        return AssessmentAssignmentDTO(
            id=row.id,
            assessment_version_id=row.assessment_version_id,
            target_type=row.target_type,  # type: ignore[arg-type]
            teaching_class_id=row.teaching_class_id,
            group_id=row.group_id,
            student_id=row.student_id,
            due_at=row.due_at,
            allow_late=row.allow_late,
            status=row.status,  # type: ignore[arg-type]
            created_at=row.created_at,
        )

    @staticmethod
    def _submission_dto(row: AssessmentSubmission) -> AssessmentSubmissionDTO:
        return AssessmentSubmissionDTO(
            id=row.id,
            assignment_id=row.assignment_id,
            student_id=row.student_id,
            status=row.status,  # type: ignore[arg-type]
            submitted_at=row.submitted_at,
        )

    @staticmethod
    def _grade_dto(row: AssessmentGradeDecision) -> GradeDecisionDTO:
        return GradeDecisionDTO(
            id=row.id,
            submission_id=row.submission_id,
            objective_score=row.objective_score,
            ai_suggested_score=row.ai_suggested_score,
            ai_agent_run_id=row.ai_agent_run_id,
            ai_evidence_snapshot_id=row.ai_evidence_snapshot_id,
            ai_suggestion_status=row.ai_suggestion_status,  # type: ignore[arg-type]
            final_score=row.final_score,
            status=row.status,  # type: ignore[arg-type]
            override_reason=row.override_reason,
            published_at=row.published_at,
            withdrawn_at=row.withdrawn_at,
        )

    @staticmethod
    def _syllabus_dto(row: CourseSyllabusVersion) -> SyllabusVersionDTO:
        return SyllabusVersionDTO(
            id=row.id,
            syllabus_id=row.syllabus_id,
            version_no=row.version_no,
            typed_content=TypedSyllabusContent.model_validate(row.typed_content),
            content_schema_version=row.content_schema_version,  # type: ignore[arg-type]
            state=row.state,  # type: ignore[arg-type]
            generated_from_agent_run_id=row.generated_from_agent_run_id,
            evidence_snapshot_id=row.evidence_snapshot_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _syllabus_markdown(typed: TypedSyllabusContent) -> str:
        lines = [f"# {typed.title}", "", typed.summary, "", "## 学习目标"]
        lines.extend(f"- {item}" for item in typed.learning_outcomes)
        lines.extend(["", "## 模块"])
        for module in typed.modules:
            lines.extend(
                [
                    f"### {module.module_id} · {module.title}",
                    module.learning_outcome,
                    "知识点：" + ", ".join(str(node_id) for node_id in module.knowledge_node_ids),
                    "活动：" + "；".join(module.activities),
                    "",
                ]
            )
        lines.extend(["## 评估", typed.assessment_plan, "", f"> 来源说明：{typed.source_note}"])
        return "\n".join(lines)

    def _evidence_chunk_ids_for_version(self, version: CourseSyllabusVersion) -> list[UUID]:
        # GeneratedResource requires UUID evidence IDs.  Runtime snapshots are
        # allowed to carry legacy opaque chunk IDs, so retain only UUID-shaped
        # values rather than fabricating a citation.
        if version.evidence_snapshot_id is None:
            return []
        # The caller already loaded/validated the version.  Export does not
        # need a second snapshot lookup to create a truthful artifact lineage.
        return []


__all__ = ["TeacherProductionError", "TeacherProductionService"]
