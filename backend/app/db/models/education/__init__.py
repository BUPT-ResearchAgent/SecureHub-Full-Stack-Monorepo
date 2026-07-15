# Status: real

"""Education-domain relationship models used by the teacher workspace."""

from app.db.models.education.education_domain import (
    CourseEnrollment,
    CourseTeacherAssignment,
    GovernanceAuditEvent,
    StudentGroup,
    StudentGroupMember,
    TeachingClass,
    TeachingClassTeacher,
)

__all__ = [
    "CourseEnrollment",
    "CourseTeacherAssignment",
    "GovernanceAuditEvent",
    "StudentGroup",
    "StudentGroupMember",
    "TeachingClass",
    "TeachingClassTeacher",
]
