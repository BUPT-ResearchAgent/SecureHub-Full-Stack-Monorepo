# Status: real

"""Typed API contracts for durable teaching classes, rosters, and groups."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TeachingClassDTO(BaseModel):
    id: UUID
    course_id: UUID
    code: str
    name: str
    status: Literal["active", "archived"]
    student_count: int = Field(ge=0)


class TeachingClassListDTO(BaseModel):
    items: list[TeachingClassDTO]


class RosterStudentDTO(BaseModel):
    id: UUID
    display_name: str
    enrollment_status: Literal["enrolled", "dropped", "completed"]
    enrolled_at: datetime


class TeachingClassRosterDTO(BaseModel):
    teaching_class: TeachingClassDTO
    students: list[RosterStudentDTO]


class StudentGroupMemberDTO(BaseModel):
    id: UUID
    student_id: UUID
    display_name: str
    status: Literal["active", "removed"]
    changed_at: datetime


class StudentGroupDTO(BaseModel):
    id: UUID
    teaching_class_id: UUID
    name: str
    status: Literal["active", "archived"]
    members: list[StudentGroupMemberDTO]


class StudentGroupListDTO(BaseModel):
    teaching_class: TeachingClassDTO
    items: list[StudentGroupDTO]


class CreateStudentGroupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("分组名称不能为空")
        return name


class ChangeStudentGroupMemberRequest(BaseModel):
    student_id: UUID
    action: Literal["add", "remove"]
    reason: str | None = Field(default=None, max_length=500)
