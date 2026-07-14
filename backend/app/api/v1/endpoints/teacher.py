# Status: real

"""Authenticated teacher-demo context with server-enforced role admission."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.deps import RequiredCurrentUserDep
from app.schemas.auth import AppRole

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


__all__ = ["router"]
