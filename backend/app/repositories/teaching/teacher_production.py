# Status: real

"""SQL persistence adapter for the teacher-production domain.

No provider, prompt, or Runtime behaviour lives here.  The repository only
reads and writes rows owned by the T3 tables plus references to existing
course, knowledge, learning, and Runtime authorities.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from app.db.models.collaboration.collaboration import ExternalSignal

from app.db.models.education.education_domain import (
    CourseEnrollment,
    CourseTeacherAssignment,
    StudentGroup,
    StudentGroupMember,
    TeachingClass,
)
from app.db.models.identity.user import User
from app.db.models.knowledge.course import Course
from app.db.models.knowledge.chunk import Chunk
from app.db.models.knowledge.document import Document
from app.db.models.knowledge.document_asset import DocumentAsset
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.db.models.learning.quiz_attempt import QuizAttempt
from app.db.models.learning.quiz_item import QuizItem
from app.db.models.learning.quiz_quality import QuizItemEvidence, QuizQualityReport
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
from app.db.models.workflow_runtime import WorkflowEvidenceSnapshot
from app.db.models.agent.agent_run import AgentRun
from app.repositories.base import BaseRepository


class TeachingProductionRepository(BaseRepository):
    async def get_course(self, course_id: UUID) -> Course | None:
        return await self.session.get(Course, course_id)

    async def list_owned_courses(self, teacher_id: UUID) -> Sequence[Course]:
        result = await self.session.execute(
            select(Course)
            .join(CourseTeacherAssignment, CourseTeacherAssignment.course_id == Course.id)
            .where(
                CourseTeacherAssignment.teacher_id == teacher_id,
                CourseTeacherAssignment.status == "active",
            )
            .order_by(Course.code)
        )
        return result.scalars().unique().all()

    async def has_teacher_course_scope(self, *, teacher_id: UUID, course_id: UUID) -> bool:
        result = await self.session.execute(
            select(CourseTeacherAssignment.id).where(
                CourseTeacherAssignment.teacher_id == teacher_id,
                CourseTeacherAssignment.course_id == course_id,
                CourseTeacherAssignment.status == "active",
            )
        )
        return result.scalar_one_or_none() is not None

    async def count_classes_for_courses(self, course_ids: Sequence[UUID]) -> dict[UUID, int]:
        if not course_ids:
            return {}
        rows = await self.session.execute(
            select(TeachingClass.course_id, func.count(TeachingClass.id))
            .where(TeachingClass.course_id.in_(course_ids), TeachingClass.status == "active")
            .group_by(TeachingClass.course_id)
        )
        return {course_id: int(count) for course_id, count in rows.all()}

    async def count_enrolled_for_courses(self, course_ids: Sequence[UUID]) -> dict[UUID, int]:
        if not course_ids:
            return {}
        rows = await self.session.execute(
            select(CourseEnrollment.course_id, func.count(CourseEnrollment.id))
            .where(CourseEnrollment.course_id.in_(course_ids), CourseEnrollment.status == "enrolled")
            .group_by(CourseEnrollment.course_id)
        )
        return {course_id: int(count) for course_id, count in rows.all()}

    async def list_course_knowledge_nodes(self, *, course_id: UUID) -> Sequence[KnowledgeNode]:
        result = await self.session.execute(
            select(KnowledgeNode)
            .where(KnowledgeNode.course_id == course_id)
            .order_by(KnowledgeNode.level, KnowledgeNode.name, KnowledgeNode.id)
        )
        return result.scalars().all()

    async def list_bindable_documents_for_course(
        self, *, course_id: UUID, course_domain: str
    ) -> Sequence[tuple[Document, DocumentAsset | None]]:
        """List in-domain documents that are not currently active course bindings."""

        statement = (
            select(Document, DocumentAsset)
            .outerjoin(DocumentAsset, DocumentAsset.document_id == Document.id)
            .outerjoin(
                CourseDocumentBinding,
                and_(
                    CourseDocumentBinding.document_id == Document.id,
                    CourseDocumentBinding.course_id == course_id,
                ),
            )
            .where(
                Document.domain == course_domain,
                or_(
                    CourseDocumentBinding.id.is_(None),
                    CourseDocumentBinding.status != "active",
                ),
            )
            .order_by(Document.title, DocumentAsset.id)
        )
        result = await self.session.execute(statement)
        return result.all()

    async def get_document(self, document_id: UUID) -> Document | None:
        return await self.session.get(Document, document_id)

    async def get_document_asset(self, asset_id: UUID) -> DocumentAsset | None:
        return await self.session.get(DocumentAsset, asset_id)

    async def list_document_assets(self, *, document_id: UUID) -> Sequence[DocumentAsset]:
        result = await self.session.execute(
            select(DocumentAsset)
            .where(DocumentAsset.document_id == document_id)
            .order_by(DocumentAsset.created_at, DocumentAsset.id)
        )
        return result.scalars().all()

    async def list_document_chunks(self, *, document_id: UUID) -> Sequence[Chunk]:
        result = await self.session.execute(
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
        )
        return result.scalars().all()

    async def list_knowledge_nodes_by_ids(self, ids: Sequence[UUID]) -> Sequence[KnowledgeNode]:
        if not ids:
            return []
        result = await self.session.execute(
            select(KnowledgeNode)
            .where(KnowledgeNode.id.in_(ids))
            .order_by(KnowledgeNode.name, KnowledgeNode.id)
        )
        return result.scalars().all()

    async def get_binding(self, binding_id: UUID) -> CourseDocumentBinding | None:
        return await self.session.get(CourseDocumentBinding, binding_id)

    async def get_binding_for_course_document(
        self, *, course_id: UUID, document_id: UUID
    ) -> CourseDocumentBinding | None:
        result = await self.session.execute(
            select(CourseDocumentBinding).where(
                CourseDocumentBinding.course_id == course_id,
                CourseDocumentBinding.document_id == document_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_assets_for_course(
        self, *, course_id: UUID, include_deleted: bool = False
    ) -> Sequence[tuple[CourseAssetGovernance, CourseDocumentBinding, Document]]:
        statement = (
            select(CourseAssetGovernance, CourseDocumentBinding, Document)
            .join(CourseDocumentBinding, CourseDocumentBinding.id == CourseAssetGovernance.binding_id)
            .join(Document, Document.id == CourseDocumentBinding.document_id)
            .where(CourseDocumentBinding.course_id == course_id)
            .order_by(CourseAssetGovernance.created_at.desc())
        )
        if not include_deleted:
            statement = statement.where(CourseAssetGovernance.state != "deleted")
        result = await self.session.execute(statement)
        return result.all()

    async def count_ready_assets_for_course(self, *, course_id: UUID) -> int:
        value = await self.session.scalar(
            select(func.count(CourseAssetGovernance.id))
            .join(
                CourseDocumentBinding,
                CourseDocumentBinding.id == CourseAssetGovernance.binding_id,
            )
            .where(
                CourseDocumentBinding.course_id == course_id,
                CourseDocumentBinding.status == "active",
                CourseAssetGovernance.state.in_(("ready", "corrected")),
            )
        )
        return int(value or 0)

    async def get_asset(self, asset_id: UUID) -> CourseAssetGovernance | None:
        return await self.session.get(CourseAssetGovernance, asset_id)

    async def get_asset_context(
        self, asset_id: UUID
    ) -> tuple[CourseAssetGovernance, CourseDocumentBinding, Document] | None:
        result = await self.session.execute(
            select(CourseAssetGovernance, CourseDocumentBinding, Document)
            .join(CourseDocumentBinding, CourseDocumentBinding.id == CourseAssetGovernance.binding_id)
            .join(Document, Document.id == CourseDocumentBinding.document_id)
            .where(CourseAssetGovernance.id == asset_id)
        )
        return result.one_or_none()

    async def get_quiz_for_course(
        self, *, quiz_item_id: UUID, course_id: UUID
    ) -> tuple[QuizItem, KnowledgeNode] | None:
        result = await self.session.execute(
            select(QuizItem, KnowledgeNode)
            .join(KnowledgeNode, KnowledgeNode.id == QuizItem.kp_id)
            .where(QuizItem.id == quiz_item_id, KnowledgeNode.course_id == course_id)
        )
        return result.one_or_none()

    async def latest_quiz_quality(self, quiz_item_id: UUID) -> QuizQualityReport | None:
        result = await self.session.execute(
            select(QuizQualityReport)
            .where(QuizQualityReport.quiz_item_id == quiz_item_id)
            .order_by(QuizQualityReport.reviewed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_student_ids_for_scope(
        self,
        *,
        course_id: UUID,
        teaching_class_id: UUID | None,
        group_id: UUID | None,
    ) -> list[UUID]:
        statement = select(CourseEnrollment.student_id).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.status == "enrolled",
        )
        if teaching_class_id is not None:
            statement = statement.where(CourseEnrollment.teaching_class_id == teaching_class_id)
        if group_id is not None:
            statement = (
                statement.join(StudentGroupMember, StudentGroupMember.student_id == CourseEnrollment.student_id)
                .join(StudentGroup, StudentGroup.id == StudentGroupMember.group_id)
                .where(
                    StudentGroupMember.group_id == group_id,
                    StudentGroupMember.status == "active",
                    StudentGroup.status == "active",
                )
            )
        result = await self.session.execute(statement)
        return list(dict.fromkeys(result.scalars().all()))

    async def get_group(self, group_id: UUID) -> StudentGroup | None:
        return await self.session.get(StudentGroup, group_id)

    async def list_quiz_attempt_contexts(
        self, *, student_ids: Sequence[UUID], course_id: UUID
    ) -> Sequence[tuple[QuizAttempt, QuizItem, KnowledgeNode]]:
        if not student_ids:
            return []
        result = await self.session.execute(
            select(QuizAttempt, QuizItem, KnowledgeNode)
            .join(QuizItem, QuizItem.id == QuizAttempt.quiz_item_id)
            .join(KnowledgeNode, KnowledgeNode.id == QuizItem.kp_id)
            .where(QuizAttempt.user_id.in_(student_ids), KnowledgeNode.course_id == course_id)
            .order_by(QuizAttempt.created_at, QuizAttempt.id)
        )
        return result.all()

    async def get_weakness_snapshot(self, snapshot_id: UUID) -> ClassWeaknessSnapshot | None:
        return await self.session.get(ClassWeaknessSnapshot, snapshot_id)

    async def list_weakness_snapshots(self, *, course_id: UUID) -> Sequence[ClassWeaknessSnapshot]:
        result = await self.session.execute(
            select(ClassWeaknessSnapshot)
            .where(ClassWeaknessSnapshot.course_id == course_id)
            .order_by(ClassWeaknessSnapshot.computed_at.desc(), ClassWeaknessSnapshot.id)
        )
        return result.scalars().all()

    async def get_evidence_snapshot(self, evidence_snapshot_id: UUID) -> WorkflowEvidenceSnapshot | None:
        return await self.session.get(WorkflowEvidenceSnapshot, evidence_snapshot_id)

    async def get_agent_run(self, agent_run_id: UUID) -> AgentRun | None:
        return await self.session.get(AgentRun, agent_run_id)

    async def list_successful_agent_evidence_pairs(
        self,
    ) -> Sequence[tuple[AgentRun, WorkflowEvidenceSnapshot]]:
        """Return durable linked candidates; the service applies course scope."""

        result = await self.session.execute(
            select(AgentRun, WorkflowEvidenceSnapshot)
            .join(WorkflowEvidenceSnapshot, WorkflowEvidenceSnapshot.agent_run_id == AgentRun.id)
            .where(
                AgentRun.status == "succeeded",
                WorkflowEvidenceSnapshot.content_digest.is_not(None),
                WorkflowEvidenceSnapshot.content_digest != "",
            )
            .order_by(AgentRun.finished_at.desc(), AgentRun.id)
        )
        return result.all()

    async def is_evidence_chunk_linked_to_course(
        self, *, course_id: UUID, chunk_id: str | None
    ) -> bool:
        """Verify legacy Evidence scope through durable course-owned links.

        Runtime snapshots retain opaque chunk identifiers for deletion
        resilience.  Only UUID-shaped values can be joined back to a course;
        an opaque legacy ID therefore still needs explicit course metadata.
        """

        if chunk_id is None:
            return False
        try:
            persisted_chunk_id = UUID(str(chunk_id))
        except (TypeError, ValueError):
            return False

        document_binding = await self.session.scalar(
            select(CourseDocumentBinding.id)
            .join(Chunk, Chunk.document_id == CourseDocumentBinding.document_id)
            .where(
                CourseDocumentBinding.course_id == course_id,
                Chunk.id == persisted_chunk_id,
            )
        )
        if document_binding is not None:
            return True

        quiz_evidence = await self.session.scalar(
            select(QuizItemEvidence.id)
            .join(QuizItem, QuizItem.id == QuizItemEvidence.quiz_item_id)
            .join(KnowledgeNode, KnowledgeNode.id == QuizItem.kp_id)
            .where(
                QuizItemEvidence.chunk_id == persisted_chunk_id,
                KnowledgeNode.course_id == course_id,
            )
        )
        return quiz_evidence is not None

    async def list_validated_external_signals(self) -> Sequence[ExternalSignal]:
        result = await self.session.execute(
            select(ExternalSignal)
            .where(ExternalSignal.status == "validated")
            .order_by(ExternalSignal.ingested_at.desc(), ExternalSignal.id)
        )
        return result.scalars().all()

    async def next_recommendation_version(self, course_id: UUID) -> int:
        value = await self.session.scalar(
            select(func.max(TeachingRecommendation.version_no)).where(
                TeachingRecommendation.course_id == course_id
            )
        )
        return int(value or 0) + 1

    async def get_recommendation(self, recommendation_id: UUID) -> TeachingRecommendation | None:
        return await self.session.get(TeachingRecommendation, recommendation_id)

    async def list_recommendations(self, *, course_id: UUID) -> Sequence[TeachingRecommendation]:
        result = await self.session.execute(
            select(TeachingRecommendation)
            .where(TeachingRecommendation.course_id == course_id)
            .order_by(TeachingRecommendation.version_no.desc(), TeachingRecommendation.created_at.desc())
        )
        return result.scalars().all()

    async def get_assessment(self, assessment_id: UUID) -> Assessment | None:
        return await self.session.get(Assessment, assessment_id)

    async def get_assessment_by_logical_key(
        self, *, course_id: UUID, logical_key: str
    ) -> Assessment | None:
        result = await self.session.execute(
            select(Assessment).where(
                Assessment.course_id == course_id, Assessment.logical_key == logical_key
            )
        )
        return result.scalar_one_or_none()

    async def next_assessment_version(self, assessment_id: UUID) -> int:
        value = await self.session.scalar(
            select(func.max(AssessmentVersion.version_no)).where(
                AssessmentVersion.assessment_id == assessment_id
            )
        )
        return int(value or 0) + 1

    async def get_assessment_version(self, version_id: UUID) -> AssessmentVersion | None:
        return await self.session.get(AssessmentVersion, version_id)

    async def get_assessment_version_context(
        self, version_id: UUID
    ) -> tuple[AssessmentVersion, Assessment] | None:
        result = await self.session.execute(
            select(AssessmentVersion, Assessment)
            .join(Assessment, Assessment.id == AssessmentVersion.assessment_id)
            .where(AssessmentVersion.id == version_id)
        )
        return result.one_or_none()

    async def list_assessment_items(self, version_id: UUID) -> Sequence[AssessmentItem]:
        result = await self.session.execute(
            select(AssessmentItem)
            .where(AssessmentItem.assessment_version_id == version_id)
            .order_by(AssessmentItem.position)
        )
        return result.scalars().all()

    async def get_assignment(self, assignment_id: UUID) -> AssessmentAssignment | None:
        return await self.session.get(AssessmentAssignment, assignment_id)

    async def list_course_assignments(
        self, *, course_id: UUID
    ) -> Sequence[tuple[AssessmentAssignment, AssessmentVersion, Assessment]]:
        result = await self.session.execute(
            select(AssessmentAssignment, AssessmentVersion, Assessment)
            .join(AssessmentVersion, AssessmentVersion.id == AssessmentAssignment.assessment_version_id)
            .join(Assessment, Assessment.id == AssessmentVersion.assessment_id)
            .where(Assessment.course_id == course_id)
            .order_by(AssessmentAssignment.created_at.desc(), AssessmentAssignment.id)
        )
        return result.all()

    async def assessment_activity_counts(self, *, course_id: UUID) -> dict[str, int]:
        """Return durable assignment/submission facts for a teacher preflight.

        These counts are explanatory only.  The weakness calculation itself
        continues to use scored ``QuizAttempt`` rows because a valid learning
        attempt can predate a formal assignment publication.
        """

        assignments = await self.list_course_assignments(course_id=course_id)
        assignment_ids = [row[0].id for row in assignments]
        if not assignment_ids:
            return {
                "active_assignment_count": 0,
                "submitted_assignment_count": 0,
                "graded_submission_count": 0,
            }
        submitted_count = await self.session.scalar(
            select(func.count(AssessmentSubmission.id)).where(
                AssessmentSubmission.assignment_id.in_(assignment_ids),
                AssessmentSubmission.status.in_(("submitted", "late")),
            )
        )
        graded_count = await self.session.scalar(
            select(func.count(AssessmentGradeDecision.id))
            .join(
                AssessmentSubmission,
                AssessmentSubmission.id == AssessmentGradeDecision.submission_id,
            )
            .where(AssessmentSubmission.assignment_id.in_(assignment_ids))
        )
        return {
            "active_assignment_count": sum(1 for row in assignments if row[0].status == "active"),
            "submitted_assignment_count": int(submitted_count or 0),
            "graded_submission_count": int(graded_count or 0),
        }

    async def get_assignment_context(
        self, assignment_id: UUID
    ) -> tuple[AssessmentAssignment, AssessmentVersion, Assessment] | None:
        result = await self.session.execute(
            select(AssessmentAssignment, AssessmentVersion, Assessment)
            .join(AssessmentVersion, AssessmentVersion.id == AssessmentAssignment.assessment_version_id)
            .join(Assessment, Assessment.id == AssessmentVersion.assessment_id)
            .where(AssessmentAssignment.id == assignment_id)
        )
        return result.one_or_none()

    async def get_submission(
        self, submission_id: UUID
    ) -> AssessmentSubmission | None:
        return await self.session.get(AssessmentSubmission, submission_id)

    async def get_submission_for_assignment_student(
        self, *, assignment_id: UUID, student_id: UUID
    ) -> AssessmentSubmission | None:
        result = await self.session.execute(
            select(AssessmentSubmission).where(
                AssessmentSubmission.assignment_id == assignment_id,
                AssessmentSubmission.student_id == student_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_submission_context(
        self, submission_id: UUID
    ) -> tuple[AssessmentSubmission, AssessmentAssignment, AssessmentVersion, Assessment] | None:
        result = await self.session.execute(
            select(AssessmentSubmission, AssessmentAssignment, AssessmentVersion, Assessment)
            .join(AssessmentAssignment, AssessmentAssignment.id == AssessmentSubmission.assignment_id)
            .join(AssessmentVersion, AssessmentVersion.id == AssessmentAssignment.assessment_version_id)
            .join(Assessment, Assessment.id == AssessmentVersion.assessment_id)
            .where(AssessmentSubmission.id == submission_id)
        )
        return result.one_or_none()

    async def get_grade_for_submission(self, submission_id: UUID) -> AssessmentGradeDecision | None:
        result = await self.session.execute(
            select(AssessmentGradeDecision).where(
                AssessmentGradeDecision.submission_id == submission_id
            )
        )
        return result.scalar_one_or_none()

    async def list_assignment_submissions(
        self, *, assignment_id: UUID
    ) -> Sequence[tuple[AssessmentSubmission, User, AssessmentGradeDecision | None]]:
        result = await self.session.execute(
            select(AssessmentSubmission, User, AssessmentGradeDecision)
            .join(User, User.id == AssessmentSubmission.student_id)
            .outerjoin(
                AssessmentGradeDecision,
                AssessmentGradeDecision.submission_id == AssessmentSubmission.id,
            )
            .where(AssessmentSubmission.assignment_id == assignment_id)
            .order_by(AssessmentSubmission.submitted_at.desc(), AssessmentSubmission.id)
        )
        return result.all()

    async def get_or_create_syllabus(self, *, course_id: UUID) -> CourseSyllabus | None:
        result = await self.session.execute(
            select(CourseSyllabus).where(CourseSyllabus.course_id == course_id)
        )
        return result.scalar_one_or_none()

    async def next_syllabus_version(self, syllabus_id: UUID) -> int:
        value = await self.session.scalar(
            select(func.max(CourseSyllabusVersion.version_no)).where(
                CourseSyllabusVersion.syllabus_id == syllabus_id
            )
        )
        return int(value or 0) + 1

    async def get_syllabus_version(self, version_id: UUID) -> CourseSyllabusVersion | None:
        return await self.session.get(CourseSyllabusVersion, version_id)

    async def get_syllabus_version_context(
        self, version_id: UUID
    ) -> tuple[CourseSyllabusVersion, CourseSyllabus] | None:
        result = await self.session.execute(
            select(CourseSyllabusVersion, CourseSyllabus)
            .join(CourseSyllabus, CourseSyllabus.id == CourseSyllabusVersion.syllabus_id)
            .where(CourseSyllabusVersion.id == version_id)
        )
        return result.one_or_none()

    async def list_syllabus_versions(self, syllabus_id: UUID) -> Sequence[CourseSyllabusVersion]:
        result = await self.session.execute(
            select(CourseSyllabusVersion)
            .where(CourseSyllabusVersion.syllabus_id == syllabus_id)
            .order_by(CourseSyllabusVersion.version_no.desc())
        )
        return result.scalars().all()

    async def get_export(self, export_id: UUID) -> SyllabusExport | None:
        return await self.session.get(SyllabusExport, export_id)

    async def count_dashboard(self, *, teacher_id: UUID, course_ids: Sequence[UUID]) -> dict[str, int]:
        if not course_ids:
            return {
                "active_students": 0,
                "governed_assets": 0,
                "pending_quiz_reviews": 0,
                "active_assignments": 0,
                "pending_grades": 0,
            }
        active_students = await self.session.scalar(
            select(func.count(CourseEnrollment.id)).where(
                CourseEnrollment.course_id.in_(course_ids), CourseEnrollment.status == "enrolled"
            )
        )
        governed_assets = await self.session.scalar(
            select(func.count(CourseAssetGovernance.id))
            .join(CourseDocumentBinding, CourseDocumentBinding.id == CourseAssetGovernance.binding_id)
            .where(
                CourseDocumentBinding.course_id.in_(course_ids),
                CourseAssetGovernance.state.not_in(("withdrawn", "deleted")),
            )
        )
        pending_quiz_reviews = await self.session.scalar(
            select(func.count(QuizItem.id))
            .join(KnowledgeNode, KnowledgeNode.id == QuizItem.kp_id)
            .where(
                KnowledgeNode.course_id.in_(course_ids),
                QuizItem.review_status.in_(("draft", "pre-generated", "codex-reviewed-pending-human")),
            )
        )
        active_assignments = await self.session.scalar(
            select(func.count(AssessmentAssignment.id))
            .join(AssessmentVersion, AssessmentVersion.id == AssessmentAssignment.assessment_version_id)
            .join(Assessment, Assessment.id == AssessmentVersion.assessment_id)
            .where(Assessment.course_id.in_(course_ids), AssessmentAssignment.status == "active")
        )
        pending_grades = await self.session.scalar(
            select(func.count(AssessmentSubmission.id))
            .join(AssessmentAssignment, AssessmentAssignment.id == AssessmentSubmission.assignment_id)
            .join(AssessmentVersion, AssessmentVersion.id == AssessmentAssignment.assessment_version_id)
            .join(Assessment, Assessment.id == AssessmentVersion.assessment_id)
            .outerjoin(
                AssessmentGradeDecision,
                AssessmentGradeDecision.submission_id == AssessmentSubmission.id,
            )
            .where(
                Assessment.course_id.in_(course_ids),
                AssessmentSubmission.status.in_(("submitted", "late")),
                (AssessmentGradeDecision.id.is_(None))
                | (AssessmentGradeDecision.status.in_(("pending", "auto_scored"))),
            )
        )
        return {
            "active_students": int(active_students or 0),
            "governed_assets": int(governed_assets or 0),
            "pending_quiz_reviews": int(pending_quiz_reviews or 0),
            "active_assignments": int(active_assignments or 0),
            "pending_grades": int(pending_grades or 0),
        }


__all__ = ["TeachingProductionRepository"]
