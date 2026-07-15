# Status: real

"""Durable teacher-production state for F1, FG-02, FG-05, and FG-06.

The module deliberately keeps course assets in the existing knowledge asset
layer and keeps generated artefacts in ``generated_resources``.  Its tables
only add governance, assessment, and typed-syllabus state; they do not copy
users, courses, learner profiles, document text, chunks, or vectors.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CourseDocumentBinding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A teacher-scoped binding to an existing unified knowledge document."""

    __tablename__ = "course_document_bindings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','withdrawn','deleted')",
            name="ck_course_document_bindings_status",
        ),
        UniqueConstraint("course_id", "document_id", name="uq_course_document_bindings_course_document"),
    )

    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    bound_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(String(64), nullable=False, server_default="teaching_material")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")


class CourseAssetGovernance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Lifecycle and lineage overlay for a bound source asset, not a new asset store."""

    __tablename__ = "course_asset_governance"
    __table_args__ = (
        CheckConstraint(
            "state IN ('uploading','processing','ready','correction_pending','corrected','withdrawn','deleted')",
            name="ck_course_asset_governance_state",
        ),
        UniqueConstraint("binding_id", "version_no", name="uq_course_asset_governance_binding_version"),
        Index("ix_course_asset_governance_owner_state", "owner_teacher_id", "state"),
    )

    binding_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("course_document_bindings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    document_asset_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_assets.id", ondelete="RESTRICT"), index=True
    )
    current_resource_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("generated_resources.id", ondelete="RESTRICT"), index=True
    )
    owner_teacher_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    state: Mapped[str] = mapped_column(String(24), nullable=False, server_default="processing")
    correction_of_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("course_asset_governance.id", ondelete="RESTRICT"), index=True
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawn_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    reason: Mapped[str | None] = mapped_column(Text)


class QuizReviewDecision(UUIDPrimaryKeyMixin, Base):
    """Human teacher decision; automated T2 validation is never a decision row."""

    __tablename__ = "quiz_review_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('publish','reject','withdraw')", name="ck_quiz_review_decisions_decision"
        ),
        Index("ix_quiz_review_decisions_item_created", "quiz_item_id", "created_at"),
    )

    quiz_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("quiz_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    teacher_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    before_status: Mapped[str] = mapped_column(String(40), nullable=False)
    after_status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ClassWeaknessSnapshot(UUIDPrimaryKeyMixin, Base):
    """Recomputable aggregate of authorized learning facts; never a profile copy."""

    __tablename__ = "class_weakness_snapshots"
    __table_args__ = (
        Index("ix_class_weakness_snapshots_scope", "course_id", "teaching_class_id", "group_id"),
        UniqueConstraint(
            "course_id", "teaching_class_id", "group_id", "input_fingerprint",
            name="uq_class_weakness_snapshots_reproducible_input",
        ),
    )

    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    teaching_class_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("teaching_classes.id", ondelete="RESTRICT"), index=True
    )
    group_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("student_groups.id", ondelete="RESTRICT"), index=True
    )
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    score_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregates: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TeachingRecommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Evidence-linked teacher recommendation awaiting an explicit decision."""

    __tablename__ = "teaching_recommendations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','adopted','rejected','superseded','withdrawn')",
            name="ck_teaching_recommendations_status",
        ),
        UniqueConstraint("course_id", "version_no", name="uq_teaching_recommendations_course_version"),
    )

    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    teaching_class_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("teaching_classes.id", ondelete="RESTRICT"), index=True
    )
    group_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("student_groups.id", ondelete="RESTRICT"), index=True
    )
    source_snapshot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("class_weakness_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    evidence_snapshot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_evidence_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    agent_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="RESTRICT"), index=True
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    diff: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")
    created_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )


class TeachingRecommendationDecision(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "teaching_recommendation_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('adopt','reject','withdraw')",
            name="ck_teaching_recommendation_decisions_decision",
        ),
        Index("ix_teaching_recommendation_decisions_recommendation", "recommendation_id", "created_at"),
    )

    recommendation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("teaching_recommendations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    teacher_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Assessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Logical assessment identity with immutable versions below it."""

    __tablename__ = "assessments"
    __table_args__ = (
        CheckConstraint("kind IN ('assignment','exam')", name="ck_assessments_kind"),
        CheckConstraint(
            "status IN ('draft','published','closed','withdrawn')", name="ck_assessments_status"
        ),
        UniqueConstraint("course_id", "logical_key", name="uq_assessments_course_logical_key"),
    )

    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    owner_teacher_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    logical_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="draft")


class AssessmentVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_versions"
    __table_args__ = (
        CheckConstraint(
            "state IN ('draft','published','withdrawn')", name="ck_assessment_versions_state"
        ),
        UniqueConstraint("assessment_id", "version_no", name="uq_assessment_versions_assessment_version"),
    )

    assessment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("assessments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default="draft")
    created_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssessmentItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "assessment_items"
    __table_args__ = (
        CheckConstraint(
            "grading_mode IN ('objective','subjective')", name="ck_assessment_items_grading_mode"
        ),
        CheckConstraint("points > 0", name="ck_assessment_items_points_positive"),
        UniqueConstraint("assessment_version_id", "position", name="uq_assessment_items_version_position"),
        UniqueConstraint("assessment_version_id", "quiz_item_id", name="uq_assessment_items_version_quiz"),
    )

    assessment_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quiz_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("quiz_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[float] = mapped_column(Float, nullable=False)
    grading_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    question_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class AssessmentAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_assignments"
    __table_args__ = (
        CheckConstraint(
            "target_type IN ('class','group','student')", name="ck_assessment_assignments_target_type"
        ),
        CheckConstraint(
            "status IN ('active','closed','withdrawn')", name="ck_assessment_assignments_status"
        ),
        UniqueConstraint(
            "assessment_version_id", "target_type", "teaching_class_id", "group_id", "student_id",
            name="uq_assessment_assignments_target",
        ),
        Index("ix_assessment_assignments_class_status", "teaching_class_id", "status"),
    )

    assessment_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    teaching_class_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("teaching_classes.id", ondelete="RESTRICT"), index=True
    )
    group_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("student_groups.id", ondelete="RESTRICT"), index=True
    )
    student_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    allow_late: Mapped[bool] = mapped_column(default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active")
    assigned_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(128))


class AssessmentSubmission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_submissions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open','submitted','late','locked')", name="ck_assessment_submissions_status"
        ),
        UniqueConstraint("assignment_id", "student_id", name="uq_assessment_submissions_assignment_student"),
    )

    assignment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment_assignments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    answers: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="open")


class AssessmentGradeDecision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_grade_decisions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','auto_scored','teacher_reviewed','published','withdrawn')",
            name="ck_assessment_grade_decisions_status",
        ),
        CheckConstraint(
            "ai_suggestion_status IN ('not_requested','suggested','rejected')",
            name="ck_assessment_grade_decisions_ai_status",
        ),
        UniqueConstraint("submission_id", name="uq_assessment_grade_decisions_submission"),
    )

    submission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment_submissions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    objective_score: Mapped[float | None] = mapped_column(Float)
    ai_suggested_score: Mapped[float | None] = mapped_column(Float)
    ai_agent_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="RESTRICT"), index=True
    )
    ai_evidence_snapshot_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_evidence_snapshots.id", ondelete="RESTRICT"),
        index=True,
    )
    ai_suggestion_status: Mapped[str] = mapped_column(
        String(24), nullable=False, server_default="not_requested"
    )
    final_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="pending")
    graded_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    override_reason: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CourseSyllabus(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One typed syllabus lineage for one existing course."""

    __tablename__ = "course_syllabuses"
    __table_args__ = (UniqueConstraint("course_id", name="uq_course_syllabuses_course"),)

    course_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    current_published_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "course_syllabus_versions.id",
            ondelete="RESTRICT",
            use_alter=True,
            name="fk_course_syllabuses_current_published_version",
        ),
        index=True,
    )


class CourseSyllabusVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "course_syllabus_versions"
    __table_args__ = (
        CheckConstraint(
            "state IN ('draft','generation_pending','review_pending','published','superseded','withdrawn')",
            name="ck_course_syllabus_versions_state",
        ),
        UniqueConstraint("syllabus_id", "version_no", name="uq_course_syllabus_versions_syllabus_version"),
    )

    syllabus_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("course_syllabuses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    typed_content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    content_schema_version: Mapped[str] = mapped_column(String(32), nullable=False, server_default="syllabus-v1")
    state: Mapped[str] = mapped_column(String(24), nullable=False, server_default="draft")
    generated_from_agent_run_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="RESTRICT"), index=True
    )
    evidence_snapshot_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_evidence_snapshots.id", ondelete="RESTRICT"),
        index=True,
    )
    created_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )


class SyllabusReviewDecision(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "syllabus_review_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approve','reject','withdraw')", name="ck_syllabus_review_decisions_decision"
        ),
        Index("ix_syllabus_review_decisions_version", "version_id", "created_at"),
    )

    version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("course_syllabus_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SyllabusExport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "syllabus_exports"
    __table_args__ = (
        CheckConstraint("format IN ('json','markdown')", name="ck_syllabus_exports_format"),
        CheckConstraint(
            "status IN ('ready','withdrawn','failed')", name="ck_syllabus_exports_status"
        ),
    )

    version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("course_syllabus_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    generated_resource_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("generated_resources.id", ondelete="RESTRICT"), index=True
    )
    storage_object_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("storage_objects.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="ready")
    created_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )


__all__ = [
    "Assessment",
    "AssessmentAssignment",
    "AssessmentGradeDecision",
    "AssessmentItem",
    "AssessmentSubmission",
    "AssessmentVersion",
    "ClassWeaknessSnapshot",
    "CourseAssetGovernance",
    "CourseDocumentBinding",
    "CourseSyllabus",
    "CourseSyllabusVersion",
    "QuizReviewDecision",
    "SyllabusExport",
    "SyllabusReviewDecision",
    "TeachingRecommendation",
    "TeachingRecommendationDecision",
]
