# Status: real

"""Authenticated teacher-demo context with server-enforced role admission."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.deps import RequiredCurrentUserDep, SessionDep
from app.schemas.auth import AppRole
from app.schemas.quiz_quality import QuizBankListDTO, QuizQualityRunDTO
from app.services.learning.quiz_quality_service import QuizQualityError, QuizQualityService

router = APIRouter(prefix="/teacher")

_MODULES_BY_ROLE: dict[str, tuple[str, ...]] = {
    "course_teacher": ("dashboard", "courses", "materials", "quiz-bank", "assignments", "students", "notices", "profile"),
    "research_mentor": ("dashboard", "students", "research", "notices", "profile"),
    "career_mentor": ("dashboard", "students", "career-mentoring", "notices", "profile"),
    "hybrid": ("dashboard", "courses", "materials", "quiz-bank", "assignments", "students", "research", "career-mentoring", "notices", "profile"),
}


class TeacherDemoContext(BaseModel):
    role: AppRole
    display_name: str
    allowed_modules: list[str]
    is_demo_account: bool


@router.get("/context", response_model=TeacherDemoContext)
async def teacher_context(user: RequiredCurrentUserDep) -> TeacherDemoContext:
    allowed_modules = _MODULES_BY_ROLE.get(user.role)
    if allowed_modules is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "TEACHER_ROLE_REQUIRED", "message": "当前账号不是教师演示身份"},
        )
    return TeacherDemoContext(
        role=user.role,  # type: ignore[arg-type]
        display_name=user.display_name,
        allowed_modules=list(allowed_modules),
        is_demo_account=user.email.endswith("@securehub.local"),
    )


def _raise_quiz_quality_error(exc: QuizQualityError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    ) from exc


@router.get("/quiz-bank/websec", response_model=QuizBankListDTO)
async def get_websec_quiz_bank(
    user: RequiredCurrentUserDep,
    session: SessionDep,
) -> QuizBankListDTO:
    """Return the durable, teacher-scoped WEBSEC-101 bank and quality state."""

    try:
        return await QuizQualityService(session).list_teacher_bank(actor=user)
    except QuizQualityError as exc:
        _raise_quiz_quality_error(exc)


@router.post("/quiz-bank/websec/validate", response_model=QuizQualityRunDTO)
async def validate_websec_quiz_bank(
    user: RequiredCurrentUserDep,
    session: SessionDep,
) -> QuizQualityRunDTO:
    """Persist a reproducible rule-based quality report; not a human approval."""

    try:
        result = await QuizQualityService(session).validate_for_teacher(actor=user)
        await session.commit()
        return result
    except QuizQualityError as exc:
        await session.rollback()
        _raise_quiz_quality_error(exc)
    except Exception:
        await session.rollback()
        raise


__all__ = ["router"]
