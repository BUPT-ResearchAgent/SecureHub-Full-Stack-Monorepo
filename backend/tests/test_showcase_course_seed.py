# Status: real

"""Focused evidence for the controlled WEBSEC-101 showcase seed profile."""

from pathlib import Path

from sqlalchemy import select
import pytest

from app.api.v1.endpoints.teaching import course_asset_knowledge_detail, teacher_production_preflight
from app.core.config import get_settings
from app.db.models.agent.agent_run import AgentRun
from app.db.models.education.education_domain import CourseEnrollment
from app.db.models.learning.quiz_item import QuizItem
from app.db.models.knowledge.chunk import Chunk
from app.db.models.knowledge.document import Document
from app.db.models.knowledge.document_asset import DocumentAsset
from app.db.models.resource.generated_resource import GeneratedResource
from app.db.models.teaching.teacher_production import (
    AssessmentAssignment,
    AssessmentGradeDecision,
    AssessmentSubmission,
    ClassWeaknessSnapshot,
)
from app.db.models.workflow_runtime import WorkflowEvidenceSnapshot
from app.db.seeds._constants import COURSE_WEBSEC_ID, DEMO_USER_ID, DEMO_USER_NAME
from app.db.seeds.seed_education_domain import (
    DEMO_COURSE_TEACHER_ID,
    DEMO_TEACHING_CLASS_ID,
)
from app.db.seeds.seed_showcase_course import (
    MANIFEST_VERSION,
    SHOWCASE_LECTURE_ASSET_ID,
    SHOWCASE_LECTURE_DOCUMENT_ID,
    SHOWCASE_LECTURE_OBJECT_KEY,
    SHOWCASE_LECTURE_PATH,
    _parse_args,
    _read_showcase_lecture,
    _require_explicit_opt_in,
    reset,
    run,
    verify,
)
from app.db.models.identity.user import User
from app.services.teaching.teacher_production_service import (
    TeacherProductionError,
    TeacherProductionService,
)


@pytest.mark.parametrize("command", ("seed", "verify", "reset"))
def test_showcase_cli_accepts_each_controlled_command(command: str) -> None:
    assert _parse_args((command,)).command == command


def test_showcase_lecture_path_is_project_relative_and_portable() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    assert SHOWCASE_LECTURE_PATH == (
        repository_root
        / "data"
        / "storage"
        / "course_websec"
        / "curated"
        / "websec-101-defensive-foundations-lecture.md"
    )
    assert SHOWCASE_LECTURE_PATH.is_file()
    assert "\\" not in SHOWCASE_LECTURE_OBJECT_KEY

    content, sections = _read_showcase_lecture()
    assert len(content) >= 900
    assert len(sections) == 7


def test_showcase_seed_requires_opt_in_and_rejects_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECUREHUB_ALLOW_SHOWCASE_SEED", "1")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="production/release"):
            _require_explicit_opt_in()

        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.delenv("SECUREHUB_ALLOW_SHOWCASE_SEED")
        get_settings.cache_clear()
        with pytest.raises(RuntimeError, match="SECUREHUB_ALLOW_SHOWCASE_SEED=1"):
            _require_explicit_opt_in()
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


@pytest.mark.anyio
async def test_showcase_seed_is_idempotent_consumable_and_profile_scoped(sqlite_session) -> None:
    first = await run(sqlite_session)
    second = await run(sqlite_session)
    verification = await verify(sqlite_session)

    assert first["manifest_version"] == MANIFEST_VERSION
    assert verification["manifest_version"] == MANIFEST_VERSION
    assert first["verification"]["valid"] is True
    assert verification["valid"] is True
    assert second["created"]["students"] == 0
    assert verification["counts"] == {
        "students": 32,
        "demo_course_learners": 1,
        "scenario_learners": 33,
        "classes": 2,
        "enrollments": 32,
        "groups": 4,
        "publishable_questions": 36,
        "scored_students": 33,
        "agent_evidence_pairs": 6,
        "resources": 11,
        "lineage_versions": 3,
        "path_versions": 33,
        "path_candidates": 1,
        "resource_recommendations": 2,
        "assignments": 3,
        "submitted_or_late": 26,
        "demo_assessment_drafts": 1,
        "snapshots": 4,
        "recommendations": 2,
        "syllabus_versions": 2,
        "notices": 2,
        "course_updates": 2,
        "assets": 3,
        "lecture_chunks": 7,
    }

    lecture_document = await sqlite_session.get(Document, SHOWCASE_LECTURE_DOCUMENT_ID)
    lecture_asset = await sqlite_session.get(DocumentAsset, SHOWCASE_LECTURE_ASSET_ID)
    lecture_chunks = list(
        (await sqlite_session.execute(
            select(Chunk).where(Chunk.document_id == SHOWCASE_LECTURE_DOCUMENT_ID)
        )).scalars()
    )
    assert lecture_document is not None and lecture_document.metadata_["processing_mode"] == "preprocessed_seed"
    assert lecture_asset is not None and lecture_asset.size_bytes and lecture_asset.size_bytes > 900
    assert len(lecture_chunks) == 7
    assert all(chunk.metadata_["kp_ids"] and chunk.metadata_["chapter"] for chunk in lecture_chunks)

    publishable = list(
        (
            await sqlite_session.execute(
                select(QuizItem).where(QuizItem.review_status == "curated")
            )
        ).scalars()
    )
    assert len(publishable) == 36
    assert {row.type for row in publishable} >= {
        "single_choice",
        "multi_choice",
        "short_answer",
        "fill",
    }
    assert len(
        list(
            (
                await sqlite_session.execute(
                    select(CourseEnrollment).where(CourseEnrollment.status == "enrolled")
                )
            ).scalars()
        )
    ) >= 32
    assert len(
        list(
            (
                await sqlite_session.execute(
                    select(AgentRun).where(AgentRun.status == "succeeded")
                )
            ).scalars()
        )
    ) >= 6
    assert len(
        list((await sqlite_session.execute(select(WorkflowEvidenceSnapshot))).scalars())
    ) >= 6
    resources = list((await sqlite_session.execute(select(GeneratedResource))).scalars())
    assert {row.resource_type for row in resources} == {
        "doc",
        "ppt",
        "mindmap",
        "quiz",
        "lab",
        "readings",
        "video",
    }
    assert sum(
        row.parent_resource_id is not None
        and row.lineage_root_id is not None
        and row.version > 1
        for row in resources
    ) >= 3
    assert len(list((await sqlite_session.execute(select(AssessmentAssignment))).scalars())) == 3
    assert len(
        [
            row
            for row in (await sqlite_session.execute(select(AssessmentSubmission))).scalars()
            if row.status in {"submitted", "late"}
        ]
    ) >= 24
    assert {row.status for row in (await sqlite_session.execute(select(AssessmentGradeDecision))).scalars()} >= {
        "pending",
        "published",
        "teacher_reviewed",
        "withdrawn",
    }
    assert len(list((await sqlite_session.execute(select(ClassWeaknessSnapshot))).scalars())) == 4

    reset_counts = await reset(sqlite_session)
    remaining_quizzes = list((await sqlite_session.execute(select(QuizItem))).scalars())
    after_reset = await verify(sqlite_session)
    assert reset_counts["students"] == 32
    demo_after_reset = await sqlite_session.get(User, DEMO_USER_ID)
    assert demo_after_reset is not None
    assert demo_after_reset.display_name == DEMO_USER_NAME
    assert len(remaining_quizzes) == 21  # Base WEBSEC-101 seed remains intact.
    assert after_reset["valid"] is False


@pytest.mark.anyio
async def test_showcase_preflight_reads_persisted_course_dependencies(sqlite_session) -> None:
    await run(sqlite_session)
    teacher = await sqlite_session.get(User, DEMO_COURSE_TEACHER_ID)
    assert teacher is not None

    result = await teacher_production_preflight(
        course_id=COURSE_WEBSEC_ID,
        session=sqlite_session,
        user=teacher,
        teaching_class_id=DEMO_TEACHING_CLASS_ID,
        minimum_scored_students=10,
    )
    assert result.enrolled_student_count >= 16
    assert result.scored_student_count >= 16
    assert result.publishable_quiz_count == 36
    assert result.successful_agent_evidence_pair_count == 6
    assert result.ready_governed_asset_count == 3
    assert result.weakness_snapshot_count == 2
    assert all(action.ready for action in result.actions)

    student = await sqlite_session.scalar(
        select(User).where(User.role == "student").order_by(User.email)
    )
    assert student is not None
    with pytest.raises(TeacherProductionError) as denied:
        await TeacherProductionService(sqlite_session).preflight_course_work(
            actor=student,
            course_id=COURSE_WEBSEC_ID,
            teaching_class_id=DEMO_TEACHING_CLASS_ID,
        )
    assert denied.value.code == "TEACHER_ROLE_REQUIRED"


@pytest.mark.anyio
async def test_showcase_lecture_detail_reads_persisted_assets_chunks_and_scope(sqlite_session) -> None:
    await run(sqlite_session)
    teacher = await sqlite_session.get(User, DEMO_COURSE_TEACHER_ID)
    student = await sqlite_session.scalar(
        select(User).where(User.role == "student").order_by(User.email)
    )
    assert teacher is not None and student is not None

    service = TeacherProductionService(sqlite_session)
    assets = await service.list_assets(actor=teacher, course_id=COURSE_WEBSEC_ID, include_deleted=True)
    lecture = next(item for item in assets.items if item.document_id == SHOWCASE_LECTURE_DOCUMENT_ID)
    detail = await course_asset_knowledge_detail(
        asset_id=lecture.id,
        session=sqlite_session,
        user=teacher,
    )
    assert detail.asset.id == lecture.id
    assert detail.processing_mode == "preprocessed_seed"
    assert detail.chunk_count == 7
    assert detail.pending_index_chunk_count == 7
    assert detail.chapter_count == 7
    assert detail.processing_timeline[-1].state == "pending"
    assert detail.chunks[0].knowledge_points
    assert "实时" in detail.source_boundary

    with pytest.raises(TeacherProductionError) as denied:
        await service.get_asset_knowledge_detail(actor=student, asset_id=lecture.id)
    assert denied.value.code == "TEACHER_ROLE_REQUIRED"
