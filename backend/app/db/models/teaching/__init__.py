# Status: real

"""Teacher production models for governed assets, assessments, and syllabus."""

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
