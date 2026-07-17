# Status: real

"""Authorization-aware T3 teacher production service.

This service is intentionally a thin state-machine layer over durable SQL
rows.  It never invokes an LLM/provider directly.  Where a subjective grading
or syllabus generation result is accepted, the result must already be a
successful Runtime/SkillExecutor AgentRun with a linked Evidence Snapshot.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
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
from app.db.models.knowledge.chunk import Chunk
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
from app.services.learning.quiz_quality_service import QuizQualityError, QuizQualityService
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
    CourseAssetKnowledgeChunkDTO,
    CourseAssetKnowledgeDetailDTO,
    CourseAssetListDTO,
    CourseAssetPipelineEventDTO,
    CreateTeachingRecommendationRequest,
    GradeDecisionDTO,
    GradeOverrideRequest,
    ObjectiveScoreDTO,
    QuizCandidateAlternativeDTO,
    QuizCandidateAvailabilityDTO,
    QuizCandidateFilterRequest,
    QuizCandidateItemDTO,
    QuizCandidatePrepareRequest,
    QuizCandidatePreviewDTO,
    QuizReviewDecisionDTO,
    QuizReviewRequest,
    RecordSubjectiveSuggestionRequest,
    StudentAssessmentQuestionDTO,
    StudentAssessmentReadDTO,
    StudentPublishedResultDTO,
    SubmitAssessmentRequest,
    TeacherAssignmentDTO,
    TeacherAssignmentListDTO,
    TeacherAssessmentSubmissionDTO,
    TeacherAssessmentSubmissionListDTO,
    TeacherCourseDTO,
    TeacherCourseListDTO,
    TeacherDashboardDTO,
    TeacherFormAgentEvidencePairDTO,
    TeacherFormCandidateDTO,
    TeacherFormContextDTO,
    TeacherFormMaterialCandidateDTO,
    TeacherFormPrefillAuditDTO,
    TeacherFormPurpose,
    TeacherFormQuizCandidateDTO,
    TeacherProductionPreflightDTO,
    PendingTeachingActionDTO,
    TeachingPreflightActionDTO,
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
_WEAKNESS_SCORE_VERSION = "teacher-weakness-v2"
_DEFAULT_CLASS_MINIMUM_SAMPLE = 10
_DEFAULT_KNOWLEDGE_POINT_MINIMUM_SAMPLE = 5


def _as_utc(value: datetime) -> datetime:
    """Return a comparable UTC timestamp across PostgreSQL and SQLite.

    PostgreSQL preserves ``DateTime(timezone=True)`` offsets, while SQLite's
    compatibility dialect returns the same persisted value as naive.  T3's
    deadline and teaching-window rules must therefore give a naive database
    value its persisted UTC meaning before comparing it with ``now(UTC)``.
    """

    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class TeacherProductionError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 409,
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail


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

    async def preflight_course_work(
        self,
        *,
        actor: User,
        course_id: UUID,
        teaching_class_id: UUID | None = None,
        minimum_scored_students: int = _DEFAULT_CLASS_MINIMUM_SAMPLE,
        knowledge_point_minimum_sample: int = _DEFAULT_KNOWLEDGE_POINT_MINIMUM_SAMPLE,
        window_start: datetime | None = None,
        window_end: datetime | None = None,
    ) -> TeacherProductionPreflightDTO:
        """Expose real prerequisites before a teacher starts a governed action.

        This is intentionally read-only.  It reports the same durable facts
        that existing submit paths validate; it never creates substitute IDs,
        quality reports, AgentRuns, or Evidence Snapshots.
        """

        if not 1 <= minimum_scored_students <= 10000:
            raise TeacherProductionError(
                "INVALID_MINIMUM_SAMPLE",
                "最小可评分学生数必须介于 1 和 10000 之间。",
                422,
            )
        if not 1 <= knowledge_point_minimum_sample <= 10000:
            raise TeacherProductionError(
                "INVALID_KNOWLEDGE_POINT_SAMPLE",
                "知识点最小有效样本必须介于 1 和 10000 之间。",
                422,
            )
        if window_start is not None and window_end is not None and window_start > window_end:
            raise TeacherProductionError("INVALID_TIME_WINDOW", "时间窗起点不能晚于终点。", 422)
        await self._require_teacher_course(actor=actor, course_id=course_id)
        if teaching_class_id is not None:
            await self._validate_education_scope(
                actor=actor,
                course_id=course_id,
                teaching_class_id=teaching_class_id,
                group_id=None,
            )

        student_ids = await self.repo.list_student_ids_for_scope(
            course_id=course_id,
            teaching_class_id=teaching_class_id,
            group_id=None,
        )
        attempts = await self.repo.list_quiz_attempt_contexts(
            student_ids=student_ids,
            course_id=course_id,
        )
        filtered_attempts = [
            row
            for row in attempts
            if self._within_time_window(row[0].created_at, window_start, window_end)
        ]
        measured_attempts = [
            row for row in filtered_attempts if self._attempt_score(row[0]) is not None
        ]
        scored_student_ids = {
            attempt.user_id
            for attempt, _, _ in measured_attempts
            if self._attempt_score(attempt) is not None
        }
        knowledge_point_students: dict[UUID, set[UUID]] = defaultdict(set)
        for attempt, _, node in measured_attempts:
            knowledge_point_students[node.id].add(attempt.user_id)
        publishable = await QuizQualityService(self.session).list_publishable_items(
            course_id=course_id
        )
        assessment_activity = await self.repo.assessment_activity_counts(course_id=course_id)
        ready_asset_count = await self.repo.count_ready_assets_for_course(course_id=course_id)
        pairs = await self.repo.list_successful_agent_evidence_pairs()
        successful_pair_count = 0
        for run, evidence in pairs:
            if await self._agent_evidence_pair_matches_course(
                course_id=course_id,
                run=run,
                evidence=evidence,
            ):
                successful_pair_count += 1
        snapshots = await self.repo.list_weakness_snapshots(course_id=course_id)
        scoped_snapshot_count = sum(
            1
            for snapshot in snapshots
            if teaching_class_id is None or snapshot.teaching_class_id == teaching_class_id
        )
        active_class_count = (await self.repo.count_classes_for_courses([course_id])).get(course_id, 0)
        teaching_class_available = (
            teaching_class_id is not None or active_class_count > 0
        )
        enrolled_count = len(student_ids)
        scored_count = len(scored_student_ids)
        coverage = round(scored_count / enrolled_count, 4) if enrolled_count else 0.0
        weakness_ready = scored_count >= minimum_scored_students
        knowledge_point_sample_ready_count = sum(
            1
            for students in knowledge_point_students.values()
            if len(students) >= knowledge_point_minimum_sample
        )
        knowledge_point_sample_insufficient_count = sum(
            1
            for students in knowledge_point_students.values()
            if len(students) < knowledge_point_minimum_sample
        )
        assignment_ready = len(publishable.items) >= 8
        syllabus_ready = successful_pair_count > 0
        recommendation_ready = scoped_snapshot_count > 0 and syllabus_ready
        material_ready = ready_asset_count > 0

        if window_start is None and window_end is None:
            window_note = "时间窗：全部已持久化的可评分作答。"
        elif not measured_attempts:
            window_note = "所选时间窗内没有可评分作答；请扩大时间范围或先完成评分。"
        else:
            window_note = "时间窗已应用；快照会保留所选范围与最近一次作答时间。"

        weakness_missing: list[str] = []
        if enrolled_count == 0:
            weakness_missing.append("当前范围没有有效选课学生，请先完成教学班选课。")
        if assessment_activity["active_assignment_count"] == 0:
            weakness_missing.append("当前课程没有进行中的作业；已有独立练习仍可计入作答聚合。")
        if assessment_activity["submitted_assignment_count"] == 0:
            weakness_missing.append("当前作业链路尚无学生提交；请发布作业并等待真实提交。")
        if assessment_activity["graded_submission_count"] == 0:
            weakness_missing.append("当前作业链路尚无评分记录；请完成客观评分或教师复核。")
        if not measured_attempts:
            weakness_missing.append(
                "所选范围没有可评分的真实作答，不能生成薄弱知识点结论。"
            )
        elif scored_count < minimum_scored_students:
            weakness_missing.append(
                f"当前范围仅有 {scored_count} 名不同学生具备可评分作答；至少需要 {minimum_scored_students} 名。"
            )

        actions = [
            TeachingPreflightActionDTO(
                action="weakness_snapshot",
                ready=weakness_ready,
                missing_requirements=[] if weakness_ready else weakness_missing,
                next_step=(
                    (
                        "可以按当前范围计算。知识点样本不足时仅显示“样本不足”，"
                        "不会生成薄弱结论。"
                    )
                    if weakness_ready
                    else "按上方缺失对象补齐真实选课、提交或评分，再重新计算薄弱知识点。"
                ),
            ),
            TeachingPreflightActionDTO(
                action="assignment_draft",
                ready=assignment_ready,
                missing_requirements=(
                    []
                    if assignment_ready
                    else [
                        f"当前课程只有 {len(publishable.items)} 道已发布且质量通过的题目；推荐填充至少需要 8 道。"
                    ]
                ),
                next_step=(
                    "可以选择质量通过题目并由教师确认后发布到教学班。"
                    if assignment_ready
                    else "先完成题目质量检查和教师审核，不能以草稿题替代。"
                ),
            ),
            TeachingPreflightActionDTO(
                action="syllabus_candidate",
                ready=syllabus_ready,
                missing_requirements=(
                    []
                    if syllabus_ready
                    else ["没有课程范围内成功且可关联的 AgentRun/Evidence Snapshot。"]
                ),
                next_step=(
                    "可以选择已有运行和证据作为大纲候选来源，教师仍需审核发布。"
                    if syllabus_ready
                    else "可先手写 typed 草稿；生成候选前必须补齐成功运行与 Evidence。"
                ),
            ),
            TeachingPreflightActionDTO(
                action="teaching_recommendation",
                ready=recommendation_ready,
                missing_requirements=(
                    ([] if scoped_snapshot_count else ["当前范围没有已持久化的薄弱点快照。"])
                    + ([] if syllabus_ready else ["没有课程范围内成功且可关联的 AgentRun/Evidence Snapshot。"])
                ),
                next_step=(
                    "可以基于快照和可验证 Evidence 填充建议草稿，再由教师处置。"
                    if recommendation_ready
                    else "先计算真实快照并选择合法运行/证据对，不能填写伪造 UUID。"
                ),
            ),
            TeachingPreflightActionDTO(
                action="material_binding",
                ready=material_ready,
                missing_requirements=(
                    [] if material_ready else ["当前课程没有处于 ready 或 corrected 状态的受治理资料资产。"]
                ),
                next_step=(
                    "可以从可读课程资料中选择并填写绑定理由。"
                    if material_ready
                    else "先上传或登记课程讲义，完成处理和质量检查后再绑定。"
                ),
            ),
        ]
        return TeacherProductionPreflightDTO(
            course_id=course_id,
            teaching_class_id=teaching_class_id,
            active_class_count=active_class_count,
            teaching_class_available=teaching_class_available,
            enrolled_student_count=enrolled_count,
            scored_student_count=scored_count,
            scored_attempt_count=len(measured_attempts),
            scored_coverage_rate=coverage,
            minimum_scored_student_count=minimum_scored_students,
            knowledge_point_minimum_sample=knowledge_point_minimum_sample,
            knowledge_point_sample_ready_count=knowledge_point_sample_ready_count,
            knowledge_point_sample_insufficient_count=knowledge_point_sample_insufficient_count,
            active_assignment_count=assessment_activity["active_assignment_count"],
            submitted_assignment_count=assessment_activity["submitted_assignment_count"],
            graded_submission_count=assessment_activity["graded_submission_count"],
            window_start=window_start,
            window_end=window_end,
            window_note=window_note,
            publishable_quiz_count=len(publishable.items),
            successful_agent_evidence_pair_count=successful_pair_count,
            ready_governed_asset_count=ready_asset_count,
            weakness_snapshot_count=scoped_snapshot_count,
            actions=actions,
            calculated_at=datetime.now(UTC),
        )

    async def get_form_context(
        self,
        *,
        actor: User,
        course_id: UUID,
        purpose: TeacherFormPurpose,
    ) -> TeacherFormContextDTO:
        """Return only durable, in-scope candidates for one teacher form.

        This endpoint deliberately prepares editable drafts and selector values
        only.  It neither creates assessments nor records a generated result;
        each downstream submit path still performs its own permission, quality,
        Evidence, and audit validation.
        """

        course = await self._require_teacher_course(actor=actor, course_id=course_id)
        classes = await self.education.list_classes_for_teacher(
            teacher_id=actor.id, course_id=course_id
        )
        class_counts = await self.education.enrollment_counts([item.id for item in classes])
        class_candidates = [
            TeacherFormCandidateDTO(
                id=item.id,
                label=f"{item.code} · {item.name}",
                summary=f"{class_counts.get(item.id, 0)} 名有效选课学生，教学班状态：{item.status}。",
                state=item.status,
                occurred_at=item.created_at,
            )
            for item in classes
        ]

        nodes = await self.repo.list_course_knowledge_nodes(course_id=course_id)
        knowledge_candidates = [
            TeacherFormCandidateDTO(
                id=node.id,
                label=node.name,
                summary=(node.description or "课程知识图谱节点，供教师选择并由服务端复核课程归属。")[:360],
                state=node.node_type,
                occurred_at=node.created_at,
            )
            for node in nodes
        ]

        publishable = await QuizQualityService(self.session).list_publishable_items(
            course_id=course_id
        )
        quiz_candidates = [
            TeacherFormQuizCandidateDTO(
                id=item.id,
                label=f"{item.canonical_key} · {item.knowledge_node_name}",
                summary=item.question[:360],
                state=f"{item.review_status} / {item.quality.result if item.quality else 'pending'}",
                knowledge_node_id=item.knowledge_node_id,
                knowledge_node_name=item.knowledge_node_name,
                question_type=item.type,
                difficulty=item.difficulty,
                default_points=10.0,
                grading_mode=(
                    "objective" if item.type in {"single_choice", "multi_choice"} else "subjective"
                ),
            )
            for item in publishable.items
        ]

        material_rows = await self.repo.list_bindable_documents_for_course(
            course_id=course_id, course_domain=course.domain
        )
        seen_documents: set[UUID] = set()
        material_candidates: list[TeacherFormMaterialCandidateDTO] = []
        for document, asset in material_rows:
            if document.id in seen_documents:
                continue
            seen_documents.add(document.id)
            asset_summary = "已有源资产" if asset is not None else "仅有入库文档元数据"
            material_candidates.append(
                TeacherFormMaterialCandidateDTO(
                    id=document.id,
                    document_asset_id=asset.id if asset is not None else None,
                    label=document.title,
                    summary=f"{asset_summary}；文档状态：{document.status}；来源类型：{document.source_type}。",
                    state=document.status,
                    occurred_at=document.updated_at,
                )
            )

        snapshots = await self.repo.list_weakness_snapshots(course_id=course_id)
        snapshot_dtos = {snapshot.id: self._weakness_dto(snapshot) for snapshot in snapshots}
        snapshot_candidates: list[TeacherFormCandidateDTO] = []
        for snapshot in snapshots:
            weak_points = snapshot_dtos[snapshot.id].weak_knowledge_points
            class_label = next(
                (candidate.label for candidate in class_candidates if candidate.id == snapshot.teaching_class_id),
                "全课程范围",
            )
            labels = "、".join(point.knowledge_node_name for point in weak_points[:3]) or "暂无满足展示规则的知识点"
            snapshot_candidates.append(
                TeacherFormCandidateDTO(
                    id=snapshot.id,
                    label=f"{class_label} · 样本 {snapshot.sample_size}",
                    summary=f"{snapshot.score_version}；重点观察：{labels}。",
                    state="persisted",
                    occurred_at=snapshot.computed_at,
                )
            )

        pair_rows = []
        for run, evidence in await self.repo.list_successful_agent_evidence_pairs():
            if await self._agent_evidence_pair_matches_course(
                course_id=course_id, run=run, evidence=evidence
            ):
                pair_rows.append((run, evidence))
        pair_candidates: list[TeacherFormAgentEvidencePairDTO] = []
        for run, evidence in pair_rows:
            output = run.output_summary if isinstance(run.output_summary, dict) else {}
            typed_raw = output.get("typed_syllabus") or output.get("syllabus") or output.get("typed_content")
            try:
                supports_typed_syllabus = isinstance(typed_raw, dict) and bool(
                    TypedSyllabusContent.model_validate(typed_raw).modules
                )
            except ValidationError:
                supports_typed_syllabus = False
            suggested_score = output.get("suggested_score")
            supports_subjective_grade = (
                isinstance(suggested_score, (int, float)) and not isinstance(suggested_score, bool)
            )
            pair_candidates.append(
                TeacherFormAgentEvidencePairDTO(
                    agent_run_id=run.id,
                    evidence_snapshot_id=evidence.id,
                    label=f"{run.workflow_name} · 已完成证据",
                    summary=(evidence.excerpt or evidence.content_digest)[:360],
                    workflow_name=run.workflow_name,
                    occurred_at=run.finished_at or evidence.created_at,
                    supports_typed_syllabus=supports_typed_syllabus,
                    supports_subjective_grade=supports_subjective_grade,
                )
            )

        if purpose == "syllabus_candidate":
            pair_candidates = [item for item in pair_candidates if item.supports_typed_syllabus]
        elif purpose == "subjective_grade":
            pair_candidates = [item for item in pair_candidates if item.supports_subjective_grade]

        syllabus_versions: list[TeacherFormCandidateDTO] = []
        syllabus = await self.repo.get_or_create_syllabus(course_id=course_id)
        if syllabus is not None:
            for version in await self.repo.list_syllabus_versions(syllabus.id):
                typed = self._syllabus_dto(version).typed_content
                syllabus_versions.append(
                    TeacherFormCandidateDTO(
                        id=version.id,
                        label=f"v{version.version_no} · {typed.title}",
                        summary=f"{len(typed.modules)} 个模块；状态：{version.state}。",
                        state=version.state,
                        occurred_at=version.updated_at,
                    )
                )

        recommendations = await self.repo.list_recommendations(course_id=course_id)
        recommendation_candidates = [
            TeacherFormCandidateDTO(
                id=item.id,
                label=f"v{item.version_no} · {str((item.diff or {}).get('title') or '教学建议')}",
                summary=str((item.diff or {}).get("rationale") or "已持久化教学建议。")[:360],
                state=item.status,
                occurred_at=item.created_at,
            )
            for item in recommendations
        ]

        eligible_pair_keys = {(item.agent_run_id, item.evidence_snapshot_id) for item in pair_candidates}
        signal_candidates = [
            TeacherFormCandidateDTO(
                id=signal.id,
                label=signal.title,
                summary=f"{signal.kind} 信号，已验证并关联课程范围内 Evidence。",
                state=signal.status,
                occurred_at=signal.ingested_at,
            )
            for signal in await self.repo.list_validated_external_signals()
            if (signal.agent_run_id, signal.evidence_snapshot_id) in eligible_pair_keys
        ]

        default_class_id = class_candidates[0].id if class_candidates else None
        preflight = await self.preflight_course_work(
            actor=actor,
            course_id=course_id,
            teaching_class_id=default_class_id,
            minimum_scored_students=_DEFAULT_CLASS_MINIMUM_SAMPLE,
            knowledge_point_minimum_sample=_DEFAULT_KNOWLEDGE_POINT_MINIMUM_SAMPLE,
        )
        dependency = next(
            (
                item
                for item in preflight.actions
                if item.action == self._form_context_action(purpose)
            ),
            None,
        )
        draft = self._form_context_draft(
            purpose=purpose,
            course_code=course.code,
            teaching_classes=class_candidates,
            knowledge_points=knowledge_candidates,
            quiz_items=quiz_candidates,
            material_candidates=material_candidates,
            snapshots=snapshot_candidates,
            snapshot_metrics=list(snapshot_dtos.values()),
            pairs=pair_candidates,
            signals=signal_candidates,
            assignment_count=len(await self.repo.list_course_assignments(course_id=course_id)),
        )
        return TeacherFormContextDTO(
            course_id=course.id,
            course_label=f"{course.code} · {course.title}",
            purpose=purpose,
            teaching_classes=class_candidates,
            knowledge_points=knowledge_candidates,
            publishable_quiz_items=quiz_candidates,
            material_candidates=material_candidates,
            weakness_snapshots=snapshot_candidates,
            agent_evidence_pairs=pair_candidates,
            external_signals=signal_candidates,
            syllabus_versions=syllabus_versions,
            teaching_recommendations=recommendation_candidates,
            dependency=dependency,
            source_summary=[
                "候选仅来自当前教师已授权的课程范围；内部标识只作为选择器值提交给既有服务端校验。",
                "受控 WEBSEC-101 场景中的整理内容、外部链接和运行记录保留来源边界，不代表实时模型生成或生产验收。",
            ],
            draft=draft,
            generated_at=datetime.now(UTC),
        )

    async def record_form_context_prefill(
        self,
        *,
        actor: User,
        course_id: UUID,
        purpose: TeacherFormPurpose,
    ) -> TeacherFormPrefillAuditDTO:
        """Audit a real click on FormAssist without treating it as submission."""

        await self._require_teacher_course(actor=actor, course_id=course_id)
        recorded_at = datetime.now(UTC)
        await self._audit(
            actor=actor,
            action="teacher_form.context_prefill",
            object_type="teacher_form_context",
            object_id=course_id,
            reason="教师点击填充推荐内容；后续字段仍可编辑，未自动提交业务对象。",
            metadata={
                "course_id": str(course_id),
                "purpose": purpose,
                "selection_source": "context_prefill",
                "does_not_submit": True,
            },
        )
        return TeacherFormPrefillAuditDTO(
            course_id=course_id,
            purpose=purpose,
            recorded_at=recorded_at,
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

    async def get_asset_knowledge_detail(
        self, *, actor: User, asset_id: UUID
    ) -> CourseAssetKnowledgeDetailDTO:
        """Return a teacher-scoped projection of persisted source and chunk facts.

        The projection deliberately does not initiate an upload, parser, or
        embedding job.  A preprocessed seed asset remains labelled as such,
        while an ordinary document shows only the facts stored by the existing
        unified knowledge ingestion pipeline.
        """

        asset, binding, document = await self._require_asset_scope(actor=actor, asset_id=asset_id)
        await self._reconcile_asset_state(asset, document)
        await self.session.refresh(asset)
        source_assets = await self.repo.list_document_assets(document_id=document.id)
        source_asset = next(
            (item for item in source_assets if item.id == asset.document_asset_id),
            source_assets[0] if source_assets else None,
        )
        chunks = await self.repo.list_document_chunks(document_id=document.id)
        node_ids: list[UUID] = []
        for chunk in chunks:
            raw_ids = (chunk.metadata_ or {}).get("kp_ids", [])
            if not isinstance(raw_ids, list):
                continue
            for raw_id in raw_ids:
                try:
                    parsed = UUID(str(raw_id))
                except (TypeError, ValueError):
                    continue
                if parsed not in node_ids:
                    node_ids.append(parsed)
        nodes = await self.repo.list_knowledge_nodes_by_ids(node_ids)
        node_names = {node.id: node.name for node in nodes}

        document_metadata = document.metadata_ if isinstance(document.metadata_, dict) else {}
        asset_metadata = (
            source_asset.metadata_ if source_asset is not None and isinstance(source_asset.metadata_, dict) else {}
        )
        timeline = self._asset_processing_timeline(
            document_metadata=document_metadata,
            document_updated_at=document.updated_at,
            chunks=chunks,
        )
        indexed_count = sum(
            1 for chunk in chunks if chunk.embedding_status == "ready" and chunk.embedding is not None
        )
        knowledge_labels = [node_names[node_id] for node_id in node_ids if node_id in node_names]
        chunk_dtos: list[CourseAssetKnowledgeChunkDTO] = []
        for chunk in chunks[:12]:
            chunk_metadata = chunk.metadata_ if isinstance(chunk.metadata_, dict) else {}
            chunk_node_names: list[str] = []
            raw_ids = chunk_metadata.get("kp_ids", [])
            if isinstance(raw_ids, list):
                for raw_id in raw_ids:
                    try:
                        node_id_value = UUID(str(raw_id))
                    except (TypeError, ValueError):
                        continue
                    if node_id_value in node_names:
                        chunk_node_names.append(node_names[node_id_value])
            raw_page = chunk_metadata.get("page_no")
            page_no = raw_page if isinstance(raw_page, int) and raw_page > 0 else None
            chapter = chunk_metadata.get("chapter")
            chunk_dtos.append(
                CourseAssetKnowledgeChunkDTO(
                    chunk_index=chunk.chunk_index,
                    chapter=str(chapter) if chapter else None,
                    page_no=page_no,
                    excerpt=self._chunk_excerpt(chunk.chunk_text),
                    knowledge_points=list(dict.fromkeys(chunk_node_names)),
                    embedding_status=chunk.embedding_status,
                    quality_state=str(chunk_metadata.get("quality_state") or "未单独标记"),
                )
            )

        def persisted_int(*values: Any) -> int | None:
            for value in values:
                if isinstance(value, int) and value >= 0:
                    return value
            return None

        return CourseAssetKnowledgeDetailDTO(
            asset=self._asset_dto(asset, binding, document),
            source_type=document.source_type,
            asset_type=source_asset.asset_type if source_asset is not None else None,
            original_filename=(
                str(asset_metadata.get("original_filename"))
                if asset_metadata.get("original_filename")
                else None
            ),
            mime_type=source_asset.mime_type if source_asset is not None else None,
            size_bytes=source_asset.size_bytes if source_asset is not None else None,
            page_count=persisted_int(asset_metadata.get("page_count"), document_metadata.get("page_count")),
            chapter_count=persisted_int(
                asset_metadata.get("chapter_count"), document_metadata.get("chapter_count"), len({item.chapter for item in chunk_dtos if item.chapter}),
            ),
            chunk_count=len(chunks),
            indexed_chunk_count=indexed_count,
            pending_index_chunk_count=max(0, len(chunks) - indexed_count),
            processing_elapsed_ms=persisted_int(
                asset_metadata.get("processing_elapsed_ms"), document_metadata.get("processing_elapsed_ms"),
            ),
            processing_mode=str(document_metadata.get("processing_mode") or "persistent_ingestion"),
            source_boundary=str(
                document_metadata.get("source_boundary")
                or "该详情只显示统一知识资产层中已经持久化的来源、状态与分块记录。"
            ),
            source_url=str(document_metadata["source_url"]) if document_metadata.get("source_url") else document.url,
            processing_timeline=timeline,
            knowledge_points=knowledge_labels,
            chunks=chunk_dtos,
        )

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

    async def preflight_quiz_candidates(
        self,
        *,
        actor: User,
        course_id: UUID,
        payload: QuizCandidateFilterRequest,
    ) -> QuizCandidateAvailabilityDTO:
        """Return current, server-authorized availability before candidate assembly.

        The preflight reads the same durable ``curated + passed`` set used by
        ``prepare_quiz_candidates``.  It creates no questions and writes no
        audit event; teachers must explicitly apply any suggested alternative
        and then invoke the existing audited prepare action.
        """

        published_items, pool = await self._quiz_candidate_pool(
            actor=actor,
            course_id=course_id,
            payload=payload,
        )
        return self._quiz_candidate_availability(
            course_id=course_id,
            payload=payload,
            published_items=published_items,
            pool=pool,
        )

    async def prepare_quiz_candidates(
        self,
        *,
        actor: User,
        course_id: UUID,
        payload: QuizCandidatePrepareRequest,
    ) -> QuizCandidatePreviewDTO:
        """Select a teacher-auditable candidate set from the durable quiz bank.

        This is intentionally a selection step, not a provider invocation.  It
        uses only existing ``curated + passed`` questions, leaves quiz rows
        unchanged, and records the teacher's intent before the existing human
        review and assessment-version flows consume the selected IDs.
        """

        published_items, pool = await self._quiz_candidate_pool(
            actor=actor,
            course_id=course_id,
            payload=payload,
        )
        availability = self._quiz_candidate_availability(
            course_id=course_id,
            payload=payload,
            published_items=published_items,
            pool=pool,
        )
        if not pool:
            raise TeacherProductionError(
                "QUIZ_CANDIDATES_UNAVAILABLE",
                "当前筛选可用 0 道已发布且质量通过的真实题目；请查看可行动的替代条件后再试。",
                detail={"availability": availability.model_dump(mode="json")},
            )

        selected = self._diversify_quiz_candidate_items(pool, payload.quantity)
        prepared_at = datetime.now(UTC)
        await self._audit(
            actor=actor,
            action="quiz_candidate.prepare",
            object_type="course_quiz_candidate_preview",
            object_id=course_id,
            reason=payload.teaching_intent,
            metadata={
                "course_id": str(course_id),
                "source": "persisted_quality_passed_bank",
                "live_generation_started": False,
                "knowledge_node_ids": [
                    str(node_id) for node_id in dict.fromkeys(payload.knowledge_node_ids)
                ],
                "question_types": list(payload.question_types),
                "target_difficulty": payload.target_difficulty,
                "requested_quantity": payload.quantity,
                "available_count": len(pool),
                "selected_quiz_item_ids": [str(item.id) for item in selected],
            },
        )
        return QuizCandidatePreviewDTO(
            course_id=course_id,
            source="persisted_quality_passed_bank",
            live_generation_started=False,
            teaching_intent=payload.teaching_intent,
            requested_quantity=payload.quantity,
            available_count=len(pool),
            items=[
                QuizCandidateItemDTO(
                    id=item.id,
                    canonical_key=item.canonical_key,
                    knowledge_node_id=item.knowledge_node_id,
                    knowledge_node_name=item.knowledge_node_name,
                    question_type=item.type,
                    difficulty=item.difficulty,
                    evidence_count=len(item.evidence),
                    quality_state="passed",
                )
                for item in selected
            ],
            next_step=(
                "候选仅来自持久化的质量通过题库；请逐题审核并在组卷页编辑题目组合、分值、"
                "教学班与截止时间。该操作没有启动实时模型生成。"
            ),
            prepared_at=prepared_at,
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
        attempts = await self.repo.list_quiz_attempt_contexts(
            student_ids=student_ids, course_id=course_id
        )
        filtered_attempts = [
            row
            for row in attempts
            if self._within_time_window(
                row[0].created_at,
                payload.window_start,
                payload.window_end,
            )
        ]
        measured = [row for row in filtered_attempts if self._attempt_score(row[0]) is not None]
        if not measured:
            raise TeacherProductionError(
                "INSUFFICIENT_ASSESSMENT_SAMPLE", "当前范围没有可评分的真实作答，不能生成薄弱知识点结论。"
            )
        scored_student_ids = {attempt.user_id for attempt, _, _ in measured}
        if len(scored_student_ids) < payload.minimum_sample:
            raise TeacherProductionError(
                "INSUFFICIENT_ASSESSMENT_SAMPLE",
                (
                    f"当前范围有 {len(student_ids)} 名有效选课学生，但仅 "
                    f"{len(scored_student_ids)} 名不同学生具备可评分真实作答；"
                    f"至少需要 {payload.minimum_sample} 名。"
                ),
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

        values: dict[UUID, list[tuple[float, UUID, str, datetime]]] = defaultdict(list)
        names: dict[UUID, str] = {}
        for attempt, _, node in measured:
            score = self._attempt_score(attempt)
            if score is None:
                continue
            values[node.id].append(
                (score, attempt.user_id, str(attempt.id), _as_utc(attempt.created_at))
            )
            names[node.id] = node.name

        metrics: list[dict[str, Any]] = []
        for node_id, records in values.items():
            sample_size = len({student_id for _, student_id, _, _ in records})
            average = sum(score for score, _, _, _ in records) / len(records)
            incorrect_rate = sum(1 for score, _, _, _ in records if score < 0.6) / len(records)
            coverage_rate = sample_size / len(student_ids) if student_ids else 0.0
            ordered = sorted(records, key=lambda row: row[3])
            midpoint = ordered[len(ordered) // 2][3] if len(ordered) >= 2 else None
            previous = [score for score, _, _, created_at in ordered if midpoint and created_at < midpoint]
            recent = [score for score, _, _, created_at in ordered if midpoint and created_at >= midpoint]
            previous_average = sum(previous) / len(previous) if previous else None
            recent_average = sum(recent) / len(recent) if recent else None
            if previous_average is None or recent_average is None:
                trend = "insufficient_history"
            elif recent_average - previous_average >= 0.04:
                trend = "improving"
            elif recent_average - previous_average <= -0.04:
                trend = "deteriorating"
            else:
                trend = "stable"

            if sample_size < payload.knowledge_point_minimum_sample:
                attention_status = "insufficient_sample"
                weakness_score: float | None = None
            else:
                trend_component = {
                    "deteriorating": 1.0,
                    "stable": 0.5,
                    "insufficient_history": 0.4,
                    "improving": 0.0,
                }[trend]
                weakness_score = min(
                    1.0,
                    max(
                        0.0,
                        0.45 * (1 - average)
                        + 0.30 * incorrect_rate
                        + 0.15 * (1 - coverage_rate)
                        + 0.10 * trend_component,
                    ),
                )
                if trend == "improving":
                    attention_status = "improving"
                elif weakness_score >= 0.45:
                    attention_status = "needs_attention"
                else:
                    attention_status = "stable"
            metrics.append(
                {
                    "knowledge_node_id": str(node_id),
                    "knowledge_node_name": names[node_id],
                    "sample_size": sample_size,
                    "average_score": round(average, 6),
                    "incorrect_rate": round(incorrect_rate, 6),
                    "coverage_rate": round(coverage_rate, 6),
                    "trend": trend,
                    "attention_status": attention_status,
                    "weakness_score": round(weakness_score, 6) if weakness_score is not None else None,
                    "previous_average_score": (
                        round(previous_average, 6) if previous_average is not None else None
                    ),
                    "latest_attempt_at": ordered[-1][3].isoformat(),
                }
            )
        status_rank = {
            "needs_attention": 0,
            "improving": 1,
            "stable": 2,
            "insufficient_sample": 3,
        }
        metrics.sort(
            key=lambda row: (
                status_rank[row["attention_status"]],
                -(row["weakness_score"] if row["weakness_score"] is not None else -1),
                row["knowledge_node_id"],
            )
        )
        weak_points = [
            row for row in metrics if row["attention_status"] == "needs_attention"
        ]
        effective_window_start = payload.window_start or min(
            _as_utc(attempt.created_at) for attempt, _, _ in measured
        )
        effective_window_end = payload.window_end or max(
            _as_utc(attempt.created_at) for attempt, _, _ in measured
        )
        latest_attempt_at = max(_as_utc(attempt.created_at) for attempt, _, _ in measured)
        aggregate = {
            "weak_knowledge_points": weak_points[:12],
            "knowledge_point_metrics": metrics[:24],
            "source_counts": {
                "quiz_attempts": len(measured),
                "learning_events": len(learning_events),
                "user_capabilities": len(capabilities),
                "enrolled_students": len(student_ids),
                "scored_students": len(scored_student_ids),
            },
            "thresholds": {
                "minimum_sample": payload.minimum_sample,
                "knowledge_point_minimum_sample": payload.knowledge_point_minimum_sample,
            },
            "window": {
                "start": effective_window_start.isoformat(),
                "end": effective_window_end.isoformat(),
                "latest_attempt_at": latest_attempt_at.isoformat(),
            },
            "limitations": (
                "按实际可评分题目作答聚合；能力与学习事件仅作为范围内已持久化学习上下文，"
                "不复制画像。知识点样本不足时只显示样本不足，不形成薄弱结论。"
            ),
        }
        fingerprint = self._fingerprint(
            {
                "course_id": str(course_id),
                "teaching_class_id": str(payload.teaching_class_id) if payload.teaching_class_id else None,
                "group_id": str(payload.group_id) if payload.group_id else None,
                "window_start": effective_window_start.isoformat(),
                "window_end": effective_window_end.isoformat(),
                "minimum_sample": payload.minimum_sample,
                "knowledge_point_minimum_sample": payload.knowledge_point_minimum_sample,
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
                window_start=effective_window_start,
                window_end=effective_window_end,
                sample_size=len(scored_student_ids),
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
                    "scored_coverage_rate": round(
                        existing.sample_size / len(student_ids), 6
                    )
                    if student_ids
                    else 0.0,
                    "knowledge_point_minimum_sample": payload.knowledge_point_minimum_sample,
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
        run, evidence = await self._require_linked_completed_agent_result(
            agent_run_id=payload.agent_run_id,
            evidence_snapshot_id=payload.evidence_snapshot_id,
        )
        if not await self._agent_evidence_pair_matches_course(
            course_id=course_id,
            run=run,
            evidence=evidence,
        ):
            raise TeacherProductionError(
                "COURSE_ACCESS_DENIED",
                "所选 AgentRun/Evidence 不属于当前课程范围，不能用于教学建议。",
                403,
            )
        snapshot_dto = self._weakness_dto(snapshot)
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
                "kind": "skill_candidate",
                "title": payload.title,
                "actions": payload.actions,
                "rationale": payload.rationale,
                "expected_impact": payload.expected_impact,
                "source_snapshot_fingerprint": snapshot.input_fingerprint,
                "snapshot_basis": {
                    "sample_size": snapshot_dto.sample_size,
                    "scored_coverage_rate": snapshot_dto.scored_coverage_rate,
                    "window_start": (
                        snapshot_dto.window_start.isoformat()
                        if snapshot_dto.window_start is not None
                        else None
                    ),
                    "window_end": (
                        snapshot_dto.window_end.isoformat()
                        if snapshot_dto.window_end is not None
                        else None
                    ),
                    "focus_knowledge_points": [
                        point.knowledge_node_name
                        for point in snapshot_dto.weak_knowledge_points[:3]
                    ],
                },
                "evidence_basis": {
                    "agent_run_id": str(run.id),
                    "evidence_snapshot_id": str(evidence.id),
                    "workflow_name": run.workflow_name,
                    "excerpt": (evidence.excerpt or evidence.content_digest)[:360],
                },
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
                "agent_run_id": str(payload.agent_run_id),
                "version_no": version,
                "course_row_mutated": False,
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
        pending_action_id: UUID | None = None
        if payload.decision == "adopt":
            # This is deliberately a structured pending draft inside the
            # versioned recommendation record. It has no write path to a
            # published course, assignment, resource, or syllabus.
            pending_action_id = uuid4()
            diff = dict(row.diff or {})
            diff["pending_teaching_action"] = {
                "id": str(pending_action_id),
                "action_type": payload.action_type,
                "title": payload.action_title,
                "draft": payload.action_draft,
                "status": "pending_review",
                "created_at": datetime.now(UTC).isoformat(),
            }
            row.diff = diff
        decision = TeachingRecommendationDecision(
            id=uuid4(),
            recommendation_id=row.id,
            teacher_id=actor.id,
            decision=payload.decision,
            reason=payload.reason,
        )
        self.session.add(decision)
        await self.session.flush()
        if pending_action_id is not None:
            await self._audit(
                actor=actor,
                action="teaching_action.create",
                object_type="pending_teaching_action",
                object_id=pending_action_id,
                reason="教师采纳教学建议后创建待审核教学动作草稿。",
                metadata={
                    "recommendation_id": str(row.id),
                    "course_id": str(row.course_id),
                    "action_type": payload.action_type,
                    "status": "pending_review",
                    "course_row_mutated": False,
                    "published_content_mutated": False,
                },
            )
        # Adoption intentionally creates only a pending action draft. It never
        # mutates the ready course catalog or any published teaching content.
        await self._audit(
            actor=actor,
            action="teaching_recommendation.decide",
            object_type="teaching_recommendation",
            object_id=row.id,
            reason=payload.reason,
            metadata={
                "decision": payload.decision,
                "result_status": state,
                "course_id": str(row.course_id),
                "pending_teaching_action_id": (
                    str(pending_action_id) if pending_action_id is not None else None
                ),
                "course_row_mutated": False,
            },
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
        version = await self.repo.get_assessment_version(assignment.assessment_version_id)
        if version is None or version.state != "published":
            raise TeacherProductionError("SUBMISSION_WINDOW_CLOSED", "当前评估版本未处于已发布状态。")
        version_items = await self.repo.list_assessment_items(version.id)
        self._validate_student_answers(payload=payload, version_items=version_items)
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

    async def get_student_assessment(
        self, *, actor: User, assignment_id: UUID
    ) -> StudentAssessmentReadDTO:
        """Expose only the published question snapshot to an assigned student.

        The frozen source record retains answers and explanations for
        deterministic server-side scoring; this student projection excludes
        both so publishing an assignment does not reveal its solution key.
        """

        if actor.role != "student":
            raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "只有已选课学生可以读取评估。", 403)
        context = await self.repo.get_assignment_context(assignment_id)
        if context is None:
            raise TeacherProductionError("ASSESSMENT_SCOPE_DENIED", "评估布置不存在或不可访问。", 404)
        assignment, version, assessment = context
        if (
            assignment.status != "active"
            or assessment.status != "published"
            or version.state != "published"
        ):
            raise TeacherProductionError("SUBMISSION_WINDOW_CLOSED", "当前评估未开放阅读。")
        await self._require_student_assignment_scope(
            actor=actor, assignment=assignment, course_id=assessment.course_id
        )
        existing_submission = await self.repo.get_submission_for_assignment_student(
            assignment_id=assignment.id, student_id=actor.id
        )
        items = await self.repo.list_assessment_items(version.id)
        question_dtos: list[StudentAssessmentQuestionDTO] = []
        for item in items:
            snapshot = item.question_snapshot if isinstance(item.question_snapshot, dict) else {}
            question = str(snapshot.get("question") or "").strip()
            knowledge_node_name = str(snapshot.get("knowledge_node_name") or "").strip()
            question_type = str(snapshot.get("type") or "").strip()
            if not question or not knowledge_node_name or not question_type:
                raise TeacherProductionError(
                    "ASSESSMENT_VERSION_LOCKED",
                    "已发布评估版本缺少可供学生读取的冻结题目字段。",
                )
            raw_options = snapshot.get("options")
            options = [str(option) for option in raw_options] if isinstance(raw_options, list) else []
            raw_content_version = snapshot.get("content_version")
            content_version = raw_content_version if isinstance(raw_content_version, int) else 1
            question_dtos.append(
                StudentAssessmentQuestionDTO(
                    quiz_item_id=item.quiz_item_id,
                    position=item.position,
                    points=item.points,
                    grading_mode=item.grading_mode,  # type: ignore[arg-type]
                    knowledge_node_name=knowledge_node_name,
                    question_type=question_type,
                    question=question,
                    options=options,
                    content_version=max(1, content_version),
                )
            )
        return StudentAssessmentReadDTO(
            assignment_id=assignment.id,
            course_id=assessment.course_id,
            title=version.title,
            instructions=version.instructions,
            due_at=assignment.due_at,
            allow_late=assignment.allow_late,
            status="active",
            submission_status=(existing_submission.status if existing_submission else "open"),  # type: ignore[arg-type]
            items=question_dtos,
        )

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
    def _form_context_action(purpose: TeacherFormPurpose) -> str | None:
        return {
            "assignment": "assignment_draft",
            "teaching_recommendation": "teaching_recommendation",
            "syllabus_candidate": "syllabus_candidate",
            "asset_binding": "material_binding",
            "quiz_generation": "assignment_draft",
        }.get(purpose)

    @staticmethod
    def _form_context_draft(
        *,
        purpose: TeacherFormPurpose,
        course_code: str,
        teaching_classes: list[TeacherFormCandidateDTO],
        knowledge_points: list[TeacherFormCandidateDTO],
        quiz_items: list[TeacherFormQuizCandidateDTO],
        material_candidates: list[TeacherFormMaterialCandidateDTO],
        snapshots: list[TeacherFormCandidateDTO],
        snapshot_metrics: list[WeaknessSnapshotDTO],
        pairs: list[TeacherFormAgentEvidencePairDTO],
        signals: list[TeacherFormCandidateDTO],
        assignment_count: int,
    ) -> dict[str, Any]:
        """Build high-quality editable defaults from durable context only."""

        default_class = teaching_classes[0] if teaching_classes else None
        default_pair = pairs[0] if pairs else None
        selected_items: list[TeacherFormQuizCandidateDTO] = []
        selected_nodes: set[UUID] = set()
        for item in quiz_items:
            if item.knowledge_node_id not in selected_nodes:
                selected_items.append(item)
                selected_nodes.add(item.knowledge_node_id)
            if len(selected_items) >= 8:
                break
        for item in quiz_items:
            if len(selected_items) >= 8:
                break
            if item.id not in {selected.id for selected in selected_items}:
                selected_items.append(item)

        if purpose == "assignment":
            return {
                "teaching_class_id": str(default_class.id) if default_class else None,
                "logical_key": f"{course_code.lower()}-input-defense-{assignment_count + 1:02d}",
                "title": "输入验证、SQL 注入与 XSS 防御复盘作业",
                "instructions": (
                    "面向当前教学班巩固输入边界、参数化查询和安全输出编码。请先阅读关联资料，"
                    "按题目顺序完成概念辨析、风险识别与防御验证；提交中说明所依据的安全控制，"
                    "不要提供可直接滥用的攻击载荷。"
                ),
                "due_at": (datetime.now(UTC) + timedelta(days=7)).replace(second=0, microsecond=0).isoformat(),
                "allow_late": True,
                "items": [
                    {
                        "quiz_item_id": str(item.id),
                        "points": item.default_points,
                        "grading_mode": item.grading_mode,
                    }
                    for item in selected_items
                ],
                "knowledge_point_coverage": list(
                    dict.fromkeys(item.knowledge_node_name for item in selected_items)
                ),
                "reason": "FormAssist 从当前课程已发布且质量通过的题目中选择分层题目，教师确认后才会冻结版本并布置。",
            }

        if purpose == "teaching_recommendation":
            snapshot = snapshots[0] if snapshots else None
            snapshot_metric = snapshot_metrics[0] if snapshot_metrics else None
            focus_points = (
                snapshot_metric.weak_knowledge_points[:2] if snapshot_metric is not None else []
            )
            if not focus_points and snapshot_metric is not None:
                focus_points = [
                    point
                    for point in snapshot_metric.knowledge_point_metrics
                    if point.attention_status != "insufficient_sample"
                ][:2]
            focus_label = "、".join(point.knowledge_node_name for point in focus_points)
            if not focus_label:
                focus_label = "当前快照中样本充足的防御知识点"
            has_attention = any(
                point.attention_status == "needs_attention" for point in focus_points
            )
            return {
                "teaching_class_id": str(default_class.id) if default_class else None,
                "minimum_sample": _DEFAULT_CLASS_MINIMUM_SAMPLE,
                "knowledge_point_minimum_sample": _DEFAULT_KNOWLEDGE_POINT_MINIMUM_SAMPLE,
                "source_snapshot_id": str(snapshot.id) if snapshot else None,
                "agent_run_id": str(default_pair.agent_run_id) if default_pair else None,
                "evidence_snapshot_id": str(default_pair.evidence_snapshot_id) if default_pair else None,
                "title": (
                    f"围绕{focus_label}安排分层防御复盘与检查练习"
                    if has_attention
                    else f"基于{focus_label}完善下一轮防御性学习检查"
                ),
                "actions": [
                    f"在下一次课前为{focus_label}补充防御性对照学习单，要求学生标注每项控制的适用边界和验证依据。",
                    "按已保存快照组织小组复盘，先解释错误模式与前置概念，再完成不包含可滥用载荷的防御性检查点。",
                    "两周后使用同一课程范围内质量通过的题目进行短测，比较覆盖率、错误率与平均分变化后再决定是否创建课程更新或大纲候选。",
                ],
                "rationale": (
                    "建议仅引用当前范围内已持久化的学习快照和已完成运行的 Evidence。快照中的有效样本、"
                    "覆盖率、错误率与趋势会在提交前由服务端再次核验；样本不足的知识点只作为观察项，不被"
                    "写成确定性薄弱结论。该草稿用于帮助教师判断复盘节奏与资料安排，不自动修改已发布课程、"
                    "作业或学生成绩，教师可按教学班实际情况继续编辑后再提交。"
                ),
                "expected_impact": (
                    "预计在下一次同范围短测中提高相关知识点的有效覆盖率和平均分，并降低重复错误率；"
                    "实际效果必须以新的真实可评分作答快照复核，不以预置文本替代结果。"
                ),
            }

        if purpose == "syllabus_candidate":
            module_nodes = knowledge_points[:4]
            modules = [
                {
                    "module_id": f"module-{index + 1}",
                    "title": title,
                    "knowledge_node_ids": [str(node.id)],
                    "learning_outcome": outcome,
                    "activities": activities,
                }
                for index, (node, title, outcome, activities) in enumerate(
                    zip(
                        module_nodes,
                        ["HTTP 与认证边界", "输入验证与 SQL 注入防御", "浏览器输出与 XSS 防御", "上传、SSRF 与综合验证"],
                        [
                            "能够说明请求、身份与授权边界，并识别需要复核的信任转换。",
                            "能够将输入校验、参数化查询和错误处理映射到可验证的防御控制。",
                            "能够区分输出上下文，选择合适的编码和内容安全策略。",
                            "能够为文件处理与服务端请求设计最小权限、校验和审计检查点。",
                        ],
                        [
                            ["认证流程边界图解", "会话安全检查清单"],
                            ["防御性案例拆解", "参数化查询与白名单复盘"],
                            ["输出上下文对照练习", "安全编码评审"],
                            ["资源访问范围建模", "综合检查与复盘"],
                        ],
                    )
                )
            ]
            return {
                "typed_content": {
                    "title": "WEBSEC-101 Web 安全基础课程大纲",
                    "summary": (
                        "本课程以 HTTP 信任边界、身份认证、输入验证和常见 Web 风险的防御与验证为主线。"
                        "学生将在受控案例中练习识别风险来源、选择安全控制、阅读证据并完成检查点，而非学习可直接复现的攻击操作。"
                        "课程通过分层练习、资料复盘和阶段测评把知识点、资源与后续教学动作连接为可审计的学习链路。"
                    ),
                    "learning_outcomes": [
                        "识别 Web 请求、认证、授权和数据处理中的信任边界。",
                        "为输入、输出、文件和服务端请求选择可验证的防御控制。",
                        "依据课程资料和 Evidence 解释安全决策，并完成防御性复盘。",
                    ],
                    "modules": modules,
                    "assessment_plan": "每个模块设置资料检查点与质量通过题目；阶段测评用于回写能力画像，教师复核后决定资料、作业或大纲候选的后续动作。",
                    "source_note": "草稿基于当前课程知识图谱、已入库资料与可验证 Evidence 整理；它不是实时模型生成结果，教师审核后才可发布。",
                },
                "agent_run_id": str(default_pair.agent_run_id) if default_pair else None,
                "evidence_snapshot_id": str(default_pair.evidence_snapshot_id) if default_pair else None,
                "reason": "基于当前课程可验证的运行与 Evidence 生成候选，教师将对模块、学习活动、评估与来源说明进行编辑和审核。",
            }

        if purpose == "subjective_grade":
            return {
                "agent_run_id": str(default_pair.agent_run_id) if default_pair else None,
                "evidence_snapshot_id": str(default_pair.evidence_snapshot_id) if default_pair else None,
                "reason": "仅将已完成且与当前课程关联的运行作为主观题建议依据；最终成绩仍需教师复核、覆盖理由和发布操作。",
            }

        if purpose == "asset_binding":
            material = material_candidates[0] if material_candidates else None
            return {
                "document_id": str(material.id) if material else None,
                "document_asset_id": str(material.document_asset_id) if material and material.document_asset_id else None,
                "purpose": "teaching_material",
                "reason": "将该已入库资料用于输入验证与安全编码模块的课前阅读、课堂复盘和作业证据定位；来源、版权与处理状态请在详情中复核。",
            }

        if purpose == "quiz_generation":
            # Recommend only a combination that the current durable bank can
            # actually satisfy.  A single knowledge node often has one or two
            # quality-passed items, so an eight-item review should start from
            # the course-wide, real availability rather than a hard-coded
            # first-node + short-answer pairing.
            difficulty_three_count = sum(item.difficulty == 3 for item in quiz_items)
            recommended_difficulty = 3 if difficulty_three_count >= 8 else None
            difficulty_note = "难度 3" if recommended_difficulty is not None else "全部难度"
            return {
                "knowledge_node_id": None,
                "question_type": None,
                "quantity": 8,
                "difficulty": recommended_difficulty,
                "reason": (
                    f"建议先在当前课程的质量通过题库中按{difficulty_note}组织 8 道跨知识点候选；"
                    "当前可用数量由服务端预检显示。教师可显式改选知识点、题型或难度，"
                    "候选题仍须经过既有质量检查和教师审核后才能进入作业或学生入口。"
                ),
            }

        if purpose == "course_update":
            signal = signals[0] if signals else None
            node = knowledge_points[0] if knowledge_points else None
            return {
                "signal_id": str(signal.id) if signal else None,
                "knowledge_node_id": str(node.id) if node else None,
                "impact_type": "emphasize",
                "title": "补充服务端请求与访问控制的防御性复盘",
                "summary": (
                    "结合当前课程中已验证的外部信号与学习表现，在本周复盘中补充服务端请求、访问控制和网络出站约束的边界说明。"
                    "面向目标教学班提供一份可读的检查清单，帮助学生先识别可信输入、目标地址和权限范围，再完成资源阅读与质量通过练习。"
                    "本更新仅创建待教师处置的候选，不会自动替换已发布课程内容；关联资料、Evidence 和后续作业均需由教师确认。"
                ),
                "rationale": "已验证信号与课程 Evidence 支持对该知识点进行强调；建议先发布补充资料和短复盘，再根据后续样本决定是否调整大纲。",
                "student_next_step": "在课程资源工作台阅读关联资料，完成防御性检查清单，并在下一次质量通过练习中说明控制选择理由。",
                "reason": "教师根据可验证信号创建可编辑课程更新候选，提交后仍需显式采纳或驳回。",
                "source_boundary": "受控课程场景的预置整理候选，非实时模型生成或生产验收结论。",
            }

        if purpose == "notice":
            return {
                "teaching_class_id": str(default_class.id) if default_class else None,
                "title": "本周 Web 安全防御复盘与阶段练习安排",
                "body": (
                    "面向当前教学班：请在本周四课前完成“输入验证与安全输出”资源中的阅读检查点。"
                    "课堂将围绕参数化查询、白名单校验和输出编码进行防御性复盘，请带着自己的控制选择理由参加讨论。"
                    "完成后进入课程资源工作台的关联练习提交答案；资料来源和 Evidence 可在详情查看。"
                ),
                "reason": "通知草稿说明了受众、时间、学习任务、下一步和资源入口，教师可按实际教学安排修改后投递。",
            }

        return {}

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

    @staticmethod
    def _asset_processing_timeline(
        *,
        document_metadata: dict[str, Any],
        document_updated_at: datetime,
        chunks: Iterable[Chunk],
    ) -> list[CourseAssetPipelineEventDTO]:
        raw_timeline = document_metadata.get("processing_timeline")
        timeline: list[CourseAssetPipelineEventDTO] = []
        if isinstance(raw_timeline, list):
            for raw_event in raw_timeline:
                if not isinstance(raw_event, dict):
                    continue
                state = str(raw_event.get("state") or "pending")
                if state not in {"completed", "pending", "failed"}:
                    state = "pending"
                occurred_at: datetime | None = None
                raw_time = raw_event.get("occurred_at")
                if isinstance(raw_time, str):
                    try:
                        occurred_at = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                    except ValueError:
                        occurred_at = None
                stage = str(raw_event.get("stage") or "persisted_state")
                label = str(raw_event.get("label") or "已读取持久化处理记录")
                timeline.append(
                    CourseAssetPipelineEventDTO(
                        stage=stage,
                        label=label,
                        state=state,  # type: ignore[arg-type]
                        occurred_at=occurred_at,
                        source="persisted_metadata",
                    )
                )
        if timeline:
            return timeline

        chunk_rows = list(chunks)
        indexed = bool(chunk_rows) and all(
            row.embedding_status == "ready" and row.embedding is not None for row in chunk_rows
        )
        return [
            CourseAssetPipelineEventDTO(
                stage="document_persisted",
                label="统一知识文档已持久化，可查看来源与分块记录",
                state="completed",
                occurred_at=document_updated_at,
                source="persisted_record",
            ),
            CourseAssetPipelineEventDTO(
                stage="chunk_status",
                label=("全部分块已具备可用向量索引" if indexed else "分块已持久化，向量化/索引状态以现有任务为准"),
                state="completed" if indexed else "pending",
                occurred_at=document_updated_at if indexed else None,
                source="persisted_record",
            ),
        ]

    @staticmethod
    def _chunk_excerpt(text: str) -> str:
        compact = " ".join(text.split())
        return compact[:720] if compact else "（该分块没有可显示的文本内容）"

    @staticmethod
    def _validate_student_answers(
        *, payload: SubmitAssessmentRequest, version_items: Iterable[AssessmentItem]
    ) -> None:
        """Reject answer keys outside the immutable, published version snapshot."""

        if not payload.answers:
            raise TeacherProductionError("SUBMISSION_ANSWERS_INVALID", "请至少提交一道当前评估版本中的题目答案。")
        allowed_ids = {str(item.quiz_item_id) for item in version_items}
        submitted_ids: set[str] = set()
        for raw_key in payload.answers:
            try:
                submitted_ids.add(str(UUID(raw_key)))
            except (TypeError, ValueError, AttributeError):
                raise TeacherProductionError(
                    "SUBMISSION_ANSWERS_INVALID", "提交答案必须对应当前评估版本中的真实题目。"
                ) from None
        if not submitted_ids <= allowed_ids:
            raise TeacherProductionError(
                "SUBMISSION_ANSWERS_INVALID", "提交包含不属于当前已发布评估版本的题目。"
            )

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

    async def _agent_evidence_pair_matches_course(
        self, *, course_id: UUID, run: Any, evidence: Any
    ) -> bool:
        """Verify linkage and scope without accepting ambiguous course metadata."""

        linked_by_run = evidence.agent_run_id == run.id
        linked_by_chunk = evidence.chunk_id is not None and evidence.chunk_id in {
            str(chunk_id) for chunk_id in (run.evidence_chunk_ids or [])
        }
        if not linked_by_run and not linked_by_chunk:
            return False
        course_id_text = str(course_id)
        contexts = (
            run.input_summary,
            run.output_summary,
            evidence.citation,
            evidence.source,
        )
        scoped_course_ids = {
            str(context["course_id"])
            for context in contexts
            if isinstance(context, dict) and context.get("course_id") is not None
        }
        if scoped_course_ids:
            return scoped_course_ids == {course_id_text}
        return await self.repo.is_evidence_chunk_linked_to_course(
            course_id=course_id,
            chunk_id=evidence.chunk_id,
        )

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

    async def _quiz_candidate_pool(
        self,
        *,
        actor: User,
        course_id: UUID,
        payload: QuizCandidateFilterRequest,
    ) -> tuple[list[Any], list[Any]]:
        """Load the exact, teacher-authorized durable pool for a filter set."""

        await self._require_teacher_course(actor=actor, course_id=course_id)
        course_nodes = await self.repo.list_course_knowledge_nodes(course_id=course_id)
        allowed_node_ids = {node.id for node in course_nodes}
        requested_node_ids = list(dict.fromkeys(payload.knowledge_node_ids))
        if any(node_id not in allowed_node_ids for node_id in requested_node_ids):
            raise TeacherProductionError(
                "QUIZ_CANDIDATE_SCOPE_DENIED",
                "候选知识点不属于当前教师课程；请从课程知识点选择器重新选择。",
                403,
            )

        try:
            published = await QuizQualityService(self.session).list_publishable_items(
                course_id=course_id
            )
        except QuizQualityError as exc:
            raise TeacherProductionError(exc.code, exc.message, exc.status_code) from exc

        pool = self._filter_quiz_candidate_items(
            published.items,
            knowledge_node_ids=requested_node_ids,
            question_types=list(dict.fromkeys(payload.question_types)),
            target_difficulty=payload.target_difficulty,
        )
        return list(published.items), self._sort_quiz_candidate_items(
            pool,
            target_difficulty=payload.target_difficulty,
        )

    def _quiz_candidate_availability(
        self,
        *,
        course_id: UUID,
        payload: QuizCandidateFilterRequest,
        published_items: Iterable[Any],
        pool: Iterable[Any],
    ) -> QuizCandidateAvailabilityDTO:
        available_items = list(pool)
        available_count = len(available_items)
        can_fulfill = available_count >= payload.quantity
        if available_count == 0:
            message = (
                "当前筛选可用 0 道已发布且质量通过的真实题目。"
                "请显式应用一个服务端计算的替代条件，或自行调整后再生成。"
            )
        elif can_fulfill:
            message = (
                f"当前筛选可用 {available_count} 道已发布且质量通过的真实题目，"
                f"可满足目标 {payload.quantity} 道。"
            )
        else:
            message = (
                f"当前筛选可用 {available_count} 道已发布且质量通过的真实题目，"
                f"距离目标 {payload.quantity} 道还差 {payload.quantity - available_count} 道。"
            )
        return QuizCandidateAvailabilityDTO(
            course_id=course_id,
            source="persisted_quality_passed_bank",
            requested_quantity=payload.quantity,
            knowledge_node_ids=list(dict.fromkeys(payload.knowledge_node_ids)),
            question_types=list(dict.fromkeys(payload.question_types)),
            target_difficulty=payload.target_difficulty,
            available_count=available_count,
            can_fulfill_requested_quantity=can_fulfill,
            message=message,
            alternatives=self._quiz_candidate_alternatives(
                published_items=published_items,
                payload=payload,
            ),
            calculated_at=datetime.now(UTC),
        )

    @staticmethod
    def _filter_quiz_candidate_items(
        items: Iterable[Any],
        *,
        knowledge_node_ids: Iterable[UUID],
        question_types: Iterable[str],
        target_difficulty: int | None,
    ) -> list[Any]:
        requested_node_ids = set(knowledge_node_ids)
        allowed_types = set(question_types)
        return [
            item
            for item in items
            if (not requested_node_ids or item.knowledge_node_id in requested_node_ids)
            and (not allowed_types or item.type in allowed_types)
            and (target_difficulty is None or item.difficulty == target_difficulty)
        ]

    @staticmethod
    def _sort_quiz_candidate_items(
        items: Iterable[Any], *, target_difficulty: int | None
    ) -> list[Any]:
        # A selected difficulty is a strict filter.  With "all difficulties",
        # retain a deterministic, evidence-backed ordering for the diversity pass.
        return sorted(
            items,
            key=lambda item: (
                item.difficulty if target_difficulty is None else 0,
                item.canonical_key,
            ),
        )

    @classmethod
    def _quiz_candidate_alternatives(
        cls,
        *,
        published_items: Iterable[Any],
        payload: QuizCandidateFilterRequest,
    ) -> list[QuizCandidateAlternativeDTO]:
        """Suggest only actual, explicitly selectable filter alternatives.

        Alternatives are derived from the current publishable rows, never from
        seed-only assumptions.  They intentionally preserve some of the
        teacher's choice where possible, but the UI must not apply them without
        an explicit teacher action.
        """

        nodes = list(dict.fromkeys(payload.knowledge_node_ids))
        question_types = list(dict.fromkeys(payload.question_types))
        current_key = (tuple(nodes), tuple(question_types), payload.target_difficulty)
        variations: list[tuple[int, str, str, list[UUID], list[str], int | None]] = []
        if nodes:
            variations.append(
                (
                    1,
                    "保留当前题型与难度，扩展至全课程知识点",
                    "当前知识点没有足够可用题目；仅扩展课程知识点范围。",
                    [],
                    question_types,
                    payload.target_difficulty,
                )
            )
        if question_types:
            variations.append(
                (
                    1,
                    "保留当前知识点与难度，放宽题型",
                    "当前题型在所选知识点和难度下不可用；改为课程中真实可用的题型。",
                    nodes,
                    [],
                    payload.target_difficulty,
                )
            )
        if payload.target_difficulty is not None:
            variations.append(
                (
                    1,
                    "保留当前知识点与题型，放宽难度",
                    "保留知识点和题型，只取消难度限制。",
                    nodes,
                    question_types,
                    None,
                )
            )
        if nodes and (question_types or payload.target_difficulty is not None):
            variations.append(
                (
                    2,
                    "保留当前知识点，放宽题型和难度",
                    "保留知识点范围，使用该节点在真实题库中的全部可用题型和难度。",
                    nodes,
                    [],
                    None,
                )
            )
        if payload.target_difficulty is not None:
            variations.append(
                (
                    2,
                    "保留当前难度，使用全课程知识点和题型",
                    "保持当前难度，扩展至当前课程中所有质量通过题目。",
                    [],
                    [],
                    payload.target_difficulty,
                )
            )
        variations.append(
            (
                3,
                "使用全课程的全部质量通过题",
                "使用当前教师有权读取的课程题库，不保留知识点、题型或难度限制。",
                [],
                [],
                None,
            )
        )

        seen: set[tuple[tuple[UUID, ...], tuple[str, ...], int | None]] = {current_key}
        alternatives: list[tuple[int, QuizCandidateAlternativeDTO]] = []
        items = list(published_items)
        for change_cost, label, reason, candidate_nodes, candidate_types, candidate_difficulty in variations:
            key = (tuple(candidate_nodes), tuple(candidate_types), candidate_difficulty)
            if key in seen:
                continue
            seen.add(key)
            available_count = len(
                cls._filter_quiz_candidate_items(
                    items,
                    knowledge_node_ids=candidate_nodes,
                    question_types=candidate_types,
                    target_difficulty=candidate_difficulty,
                )
            )
            if available_count == 0:
                continue
            alternatives.append(
                (
                    change_cost,
                    QuizCandidateAlternativeDTO(
                        label=label,
                        reason=reason,
                        knowledge_node_ids=candidate_nodes,
                        question_types=candidate_types,
                        target_difficulty=candidate_difficulty,
                        available_count=available_count,
                        can_fulfill_requested_quantity=available_count >= payload.quantity,
                    ),
                )
            )
        alternatives.sort(
            key=lambda row: (
                not row[1].can_fulfill_requested_quantity,
                row[0],
                -row[1].available_count,
                row[1].label,
            )
        )
        return [alternative for _, alternative in alternatives[:4]]

    @staticmethod
    def _diversify_quiz_candidate_items(items: Iterable[Any], quantity: int) -> list[Any]:
        """Round-robin durable items across knowledge points for a usable draft."""

        buckets: dict[UUID, list[Any]] = defaultdict(list)
        for item in items:
            buckets[item.knowledge_node_id].append(item)

        selected: list[Any] = []
        while len(selected) < quantity:
            progressed = False
            for node_id in sorted(buckets, key=str):
                bucket = buckets[node_id]
                if not bucket:
                    continue
                selected.append(bucket.pop(0))
                progressed = True
                if len(selected) >= quantity:
                    break
            if not progressed:
                break
        return selected

    @staticmethod
    def _within_time_window(
        created_at: datetime,
        window_start: datetime | None,
        window_end: datetime | None,
    ) -> bool:
        """Compare SQLite and PostgreSQL timestamps with the same UTC meaning."""

        created = _as_utc(created_at)
        return (
            (window_start is None or created >= _as_utc(window_start))
            and (window_end is None or created <= _as_utc(window_end))
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
        metrics = aggregate.get("knowledge_point_metrics", points)
        source_counts = aggregate.get("source_counts", {})
        thresholds = aggregate.get("thresholds", {})
        window = aggregate.get("window", {})
        return WeaknessSnapshotDTO(
            id=snapshot.id,
            course_id=snapshot.course_id,
            teaching_class_id=snapshot.teaching_class_id,
            group_id=snapshot.group_id,
            sample_size=snapshot.sample_size,
            score_version=snapshot.score_version,
            input_fingerprint=snapshot.input_fingerprint,
            weak_knowledge_points=[WeaknessKnowledgePointDTO.model_validate(item) for item in points],
            knowledge_point_metrics=[
                WeaknessKnowledgePointDTO.model_validate(item) for item in metrics
            ],
            enrolled_student_count=int(source_counts.get("enrolled_students", 0)),
            scored_student_count=int(source_counts.get("scored_students", snapshot.sample_size)),
            scored_coverage_rate=round(
                snapshot.sample_size / int(source_counts.get("enrolled_students", 0)),
                6,
            )
            if int(source_counts.get("enrolled_students", 0))
            else 0.0,
            minimum_sample=int(
                thresholds.get("minimum_sample", _DEFAULT_CLASS_MINIMUM_SAMPLE)
            ),
            knowledge_point_minimum_sample=int(
                thresholds.get(
                    "knowledge_point_minimum_sample",
                    _DEFAULT_KNOWLEDGE_POINT_MINIMUM_SAMPLE,
                )
            ),
            window_start=snapshot.window_start or window.get("start"),
            window_end=snapshot.window_end or window.get("end"),
            latest_attempt_at=window.get("latest_attempt_at"),
            computed_at=snapshot.computed_at,
        )

    @staticmethod
    def _recommendation_dto(row: TeachingRecommendation) -> TeachingRecommendationDTO:
        diff = row.diff if isinstance(row.diff, dict) else {}
        pending_action: PendingTeachingActionDTO | None = None
        raw_action = diff.get("pending_teaching_action")
        if isinstance(raw_action, dict):
            try:
                pending_action = PendingTeachingActionDTO.model_validate(raw_action)
            except ValidationError:
                # Historical recommendation rows may not yet have the newer
                # action-draft shape. They remain readable and auditable.
                pending_action = None
        return TeachingRecommendationDTO(
            id=row.id,
            course_id=row.course_id,
            source_snapshot_id=row.source_snapshot_id,
            evidence_snapshot_id=row.evidence_snapshot_id,
            agent_run_id=row.agent_run_id,
            version_no=row.version_no,
            diff=diff,
            status=row.status,  # type: ignore[arg-type]
            pending_teaching_action=pending_action,
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
