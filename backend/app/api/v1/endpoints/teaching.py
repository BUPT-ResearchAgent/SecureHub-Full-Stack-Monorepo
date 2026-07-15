# Status: real

"""HTTP adapters for the T3 teacher production state machines."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.deps import RequiredCurrentUserDep, SessionDep
from app.schemas.syllabus import (
    CreateSyllabusVersionRequest,
    GenerateSyllabusVersionRequest,
    SyllabusDiffDTO,
    SyllabusExportDTO,
    SyllabusExportRequest,
    SyllabusReviewRequest,
    SyllabusVersionDTO,
    SyllabusVersionListDTO,
)
from app.schemas.teacher_production import (
    AssessmentAssignmentDTO,
    AssessmentCreateRequest,
    AssessmentDTO,
    AssessmentSubmissionDTO,
    AssessmentVersionCreateRequest,
    AssessmentVersionDTO,
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
    TeacherAssignmentListDTO,
    TeacherAssessmentSubmissionListDTO,
    TeacherCourseListDTO,
    TeacherDashboardDTO,
    TeachingRecommendationDTO,
    TeachingRecommendationDecisionRequest,
    TeachingRecommendationListDTO,
    WeaknessSnapshotDTO,
    WeaknessSnapshotListDTO,
    WeaknessSnapshotRequest,
    AssignmentCreateRequest,
)
from app.services.teaching.teacher_production_service import (
    TeacherProductionError,
    TeacherProductionService,
)


router = APIRouter()


def _raise_domain_error(exc: TeacherProductionError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    ) from exc


@router.get("/teacher/production/dashboard", response_model=TeacherDashboardDTO)
async def teacher_production_dashboard(
    session: SessionDep, user: RequiredCurrentUserDep
) -> TeacherDashboardDTO:
    try:
        return await TeacherProductionService(session).dashboard(actor=user)
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.get("/teacher/production/courses", response_model=TeacherCourseListDTO)
async def teacher_production_courses(
    session: SessionDep, user: RequiredCurrentUserDep
) -> TeacherCourseListDTO:
    try:
        return await TeacherProductionService(session).list_owned_courses(actor=user)
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.get("/teacher/production/courses/{course_id}/assets", response_model=CourseAssetListDTO)
async def list_course_assets(
    course_id: UUID,
    session: SessionDep,
    user: RequiredCurrentUserDep,
    include_deleted: bool = Query(default=False),
) -> CourseAssetListDTO:
    try:
        return await TeacherProductionService(session).list_assets(
            actor=user, course_id=course_id, include_deleted=include_deleted
        )
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teacher/production/courses/{course_id}/assets",
    response_model=CourseAssetDTO,
    status_code=201,
)
async def bind_course_asset(
    course_id: UUID,
    payload: BindCourseDocumentRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> CourseAssetDTO:
    try:
        result = await TeacherProductionService(session).bind_document(
            actor=user, course_id=course_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post("/teacher/production/assets/{asset_id}/correct", response_model=CourseAssetDTO)
async def correct_course_asset(
    asset_id: UUID,
    payload: CorrectCourseAssetRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> CourseAssetDTO:
    try:
        result = await TeacherProductionService(session).correct_asset(
            actor=user, asset_id=asset_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post("/teacher/production/assets/{asset_id}/withdraw", response_model=CourseAssetDTO)
async def withdraw_course_asset(
    asset_id: UUID,
    payload: AssetLifecycleRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> CourseAssetDTO:
    try:
        result = await TeacherProductionService(session).withdraw_asset(
            actor=user, asset_id=asset_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post("/teacher/production/assets/{asset_id}/delete", response_model=CourseAssetDTO)
async def delete_course_asset(
    asset_id: UUID,
    payload: AssetLifecycleRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> CourseAssetDTO:
    try:
        result = await TeacherProductionService(session).delete_asset(
            actor=user, asset_id=asset_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post("/teacher/production/assets/{asset_id}/restore", response_model=CourseAssetDTO)
async def restore_course_asset(
    asset_id: UUID,
    payload: AssetLifecycleRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> CourseAssetDTO:
    try:
        result = await TeacherProductionService(session).restore_asset(
            actor=user, asset_id=asset_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teacher/production/courses/{course_id}/quiz-items/{quiz_item_id}/review",
    response_model=QuizReviewDecisionDTO,
)
async def review_course_quiz_item(
    course_id: UUID,
    quiz_item_id: UUID,
    payload: QuizReviewRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> QuizReviewDecisionDTO:
    try:
        result = await TeacherProductionService(session).review_quiz(
            actor=user, course_id=course_id, quiz_item_id=quiz_item_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teacher/production/courses/{course_id}/weakness-snapshots",
    response_model=WeaknessSnapshotDTO,
)
async def create_weakness_snapshot(
    course_id: UUID,
    payload: WeaknessSnapshotRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> WeaknessSnapshotDTO:
    try:
        result = await TeacherProductionService(session).compute_weakness_snapshot(
            actor=user, course_id=course_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.get(
    "/teacher/production/courses/{course_id}/weakness-snapshots",
    response_model=WeaknessSnapshotListDTO,
)
async def list_weakness_snapshots(
    course_id: UUID,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> WeaknessSnapshotListDTO:
    try:
        return await TeacherProductionService(session).list_weakness_snapshots(
            actor=user, course_id=course_id
        )
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teacher/production/courses/{course_id}/teaching-recommendations",
    response_model=TeachingRecommendationDTO,
    status_code=201,
)
async def create_teaching_recommendation(
    course_id: UUID,
    payload: CreateTeachingRecommendationRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> TeachingRecommendationDTO:
    try:
        result = await TeacherProductionService(session).create_teaching_recommendation(
            actor=user, course_id=course_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.get(
    "/teacher/production/courses/{course_id}/teaching-recommendations",
    response_model=TeachingRecommendationListDTO,
)
async def list_teaching_recommendations(
    course_id: UUID,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> TeachingRecommendationListDTO:
    try:
        return await TeacherProductionService(session).list_teaching_recommendations(
            actor=user, course_id=course_id
        )
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teacher/production/teaching-recommendations/{recommendation_id}/decision",
    response_model=TeachingRecommendationDTO,
)
async def decide_teaching_recommendation(
    recommendation_id: UUID,
    payload: TeachingRecommendationDecisionRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> TeachingRecommendationDTO:
    try:
        result = await TeacherProductionService(session).decide_teaching_recommendation(
            actor=user, recommendation_id=recommendation_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.get(
    "/teacher/production/courses/{course_id}/assignments",
    response_model=TeacherAssignmentListDTO,
)
async def list_course_assignments(
    course_id: UUID,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> TeacherAssignmentListDTO:
    try:
        return await TeacherProductionService(session).list_course_assignments(
            actor=user, course_id=course_id
        )
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teacher/production/courses/{course_id}/assessments",
    response_model=AssessmentDTO,
    status_code=201,
)
async def create_course_assessment(
    course_id: UUID,
    payload: AssessmentCreateRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> AssessmentDTO:
    try:
        result = await TeacherProductionService(session).create_assessment(
            actor=user, course_id=course_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teacher/production/assessments/{assessment_id}/versions",
    response_model=AssessmentVersionDTO,
    status_code=201,
)
async def create_assessment_version(
    assessment_id: UUID,
    payload: AssessmentVersionCreateRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> AssessmentVersionDTO:
    try:
        result = await TeacherProductionService(session).create_assessment_version(
            actor=user, assessment_id=assessment_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teacher/production/assessment-versions/{version_id}/assignments",
    response_model=AssessmentAssignmentDTO,
    status_code=201,
)
async def assign_assessment_version(
    version_id: UUID,
    payload: AssignmentCreateRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> AssessmentAssignmentDTO:
    try:
        result = await TeacherProductionService(session).assign_assessment(
            actor=user, version_id=version_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teaching/assessment-assignments/{assignment_id}/submit",
    response_model=AssessmentSubmissionDTO,
)
async def submit_assessment_assignment(
    assignment_id: UUID,
    payload: SubmitAssessmentRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> AssessmentSubmissionDTO:
    try:
        result = await TeacherProductionService(session).submit_assessment(
            actor=user, assignment_id=assignment_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.get(
    "/teacher/production/assessment-assignments/{assignment_id}/submissions",
    response_model=TeacherAssessmentSubmissionListDTO,
)
async def list_assignment_submissions(
    assignment_id: UUID,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> TeacherAssessmentSubmissionListDTO:
    try:
        return await TeacherProductionService(session).list_assignment_submissions(
            actor=user, assignment_id=assignment_id
        )
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teacher/production/assessment-submissions/{submission_id}/score-objective",
    response_model=ObjectiveScoreDTO,
)
async def score_objective_submission(
    submission_id: UUID,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> ObjectiveScoreDTO:
    try:
        result = await TeacherProductionService(session).score_objective_submission(
            actor=user, submission_id=submission_id
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teacher/production/assessment-submissions/{submission_id}/subjective-suggestion",
    response_model=GradeDecisionDTO,
)
async def record_subjective_suggestion(
    submission_id: UUID,
    payload: RecordSubjectiveSuggestionRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> GradeDecisionDTO:
    try:
        result = await TeacherProductionService(session).record_subjective_suggestion(
            actor=user, submission_id=submission_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teacher/production/assessment-submissions/{submission_id}/override",
    response_model=GradeDecisionDTO,
)
async def override_submission_grade(
    submission_id: UUID,
    payload: GradeOverrideRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> GradeDecisionDTO:
    try:
        result = await TeacherProductionService(session).override_grade(
            actor=user, submission_id=submission_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teacher/production/assessment-submissions/{submission_id}/publish",
    response_model=GradeDecisionDTO,
)
async def publish_submission_grade(
    submission_id: UUID,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> GradeDecisionDTO:
    try:
        result = await TeacherProductionService(session).publish_grade(
            actor=user, submission_id=submission_id
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teacher/production/assessment-submissions/{submission_id}/withdraw",
    response_model=GradeDecisionDTO,
)
async def withdraw_submission_grade(
    submission_id: UUID,
    payload: AssetLifecycleRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> GradeDecisionDTO:
    try:
        result = await TeacherProductionService(session).withdraw_grade(
            actor=user, submission_id=submission_id, reason=payload.reason
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.get(
    "/teaching/assessment-assignments/{assignment_id}/result",
    response_model=StudentPublishedResultDTO,
)
async def student_published_assessment_result(
    assignment_id: UUID,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> StudentPublishedResultDTO:
    try:
        return await TeacherProductionService(session).get_student_published_result(
            actor=user, assignment_id=assignment_id
        )
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.get(
    "/teacher/production/courses/{course_id}/syllabus/versions",
    response_model=SyllabusVersionListDTO,
)
async def list_syllabus_versions(
    course_id: UUID,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> SyllabusVersionListDTO:
    try:
        return await TeacherProductionService(session).list_syllabus_versions(
            actor=user, course_id=course_id
        )
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teacher/production/courses/{course_id}/syllabus/versions",
    response_model=SyllabusVersionDTO,
    status_code=201,
)
async def create_syllabus_version(
    course_id: UUID,
    payload: CreateSyllabusVersionRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> SyllabusVersionDTO:
    try:
        result = await TeacherProductionService(session).create_syllabus_version(
            actor=user, course_id=course_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teacher/production/courses/{course_id}/syllabus/generate",
    response_model=SyllabusVersionDTO,
    status_code=201,
)
async def generate_syllabus_version(
    course_id: UUID,
    payload: GenerateSyllabusVersionRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> SyllabusVersionDTO:
    try:
        result = await TeacherProductionService(session).generate_syllabus_version(
            actor=user, course_id=course_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teacher/production/syllabus/versions/{version_id}/review",
    response_model=SyllabusVersionDTO,
)
async def review_syllabus_version(
    version_id: UUID,
    payload: SyllabusReviewRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> SyllabusVersionDTO:
    try:
        result = await TeacherProductionService(session).review_syllabus_version(
            actor=user, version_id=version_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.get(
    "/teacher/production/syllabus/versions/{version_id}/diff",
    response_model=SyllabusDiffDTO,
)
async def compare_syllabus_versions(
    version_id: UUID,
    session: SessionDep,
    user: RequiredCurrentUserDep,
    from_version_id: UUID | None = Query(default=None),
) -> SyllabusDiffDTO:
    try:
        return await TeacherProductionService(session).compare_syllabus_versions(
            actor=user, from_version_id=from_version_id, to_version_id=version_id
        )
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.get(
    "/teacher/production/syllabus/versions/{version_id}/preview",
    response_model=SyllabusVersionDTO,
)
async def preview_syllabus_version(
    version_id: UUID,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> SyllabusVersionDTO:
    try:
        return await TeacherProductionService(session).preview_syllabus_version(actor=user, version_id=version_id)
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teacher/production/syllabus/versions/{version_id}/export",
    response_model=SyllabusExportDTO,
)
async def export_syllabus_version(
    version_id: UUID,
    payload: SyllabusExportRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> SyllabusExportDTO:
    try:
        result = await TeacherProductionService(session).export_syllabus_version(
            actor=user, version_id=version_id, payload=payload
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.post(
    "/teacher/production/syllabus/versions/{version_id}/rollback",
    response_model=SyllabusVersionDTO,
)
async def rollback_published_syllabus(
    version_id: UUID,
    payload: AssetLifecycleRequest,
    session: SessionDep,
    user: RequiredCurrentUserDep,
) -> SyllabusVersionDTO:
    try:
        result = await TeacherProductionService(session).rollback_published_syllabus(
            actor=user, version_id=version_id, reason=payload.reason
        )
        await session.commit()
        return result
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


@router.get("/teaching/courses/{course_id}/syllabus", response_model=SyllabusVersionDTO)
async def student_published_syllabus(
    course_id: UUID, session: SessionDep, user: RequiredCurrentUserDep
) -> SyllabusVersionDTO:
    try:
        return await TeacherProductionService(session).get_student_published_syllabus(
            actor=user, course_id=course_id
        )
    except TeacherProductionError as exc:
        await session.rollback()
        _raise_domain_error(exc)


__all__ = ["router"]
