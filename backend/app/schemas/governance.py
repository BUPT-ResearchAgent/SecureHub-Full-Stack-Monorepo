# Status: real

"""HTTP DTOs for server-authoritative administrator governance."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class RoleGrantRequest(BaseModel):
    user_id: UUID
    role_code: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=1, max_length=2000)


class RoleRevokeRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class RoleGrantDTO(BaseModel):
    id: UUID
    user_id: UUID
    role_id: UUID
    role_code: str
    granted_by: UUID
    granted_at: datetime
    status: Literal["active", "revoked"]
    reason: str
    revoked_at: datetime | None = None


class AdminUserDTO(BaseModel):
    id: UUID
    display_name: str
    email: str
    product_role: str
    is_active: bool
    governance_roles: list[str]


class AdminUserListDTO(BaseModel):
    items: list[AdminUserDTO]


class CourseResourceGovernanceRequest(BaseModel):
    action: Literal["restrict", "release", "withdraw"]
    reason: str = Field(min_length=1, max_length=2000)


class AdminCourseResourceDTO(BaseModel):
    asset_id: UUID
    course_id: UUID
    course_code: str
    document_id: UUID
    document_title: str
    asset_state: str
    governance_state: Literal["active", "restricted", "withdrawn"]
    reason: str | None = None
    changed_at: datetime | None = None


class AdminCourseResourceListDTO(BaseModel):
    items: list[AdminCourseResourceDTO]


class KpiValueDTO(BaseModel):
    code: str
    definition_version: int
    description: str
    source_relations: list[str]
    time_window: str
    value: int
    calculated_at: datetime


class AdminKpiDashboardDTO(BaseModel):
    items: list[KpiValueDTO]
    calculated_at: datetime
