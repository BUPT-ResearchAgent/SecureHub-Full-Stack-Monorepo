# Status: real

"""DTOs for T5 account remediation and redacted API-risk governance."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PasswordPolicyCreateRequest(BaseModel):
    rules: dict[str, Any]
    note: str | None = Field(default=None, max_length=2000)


class PasswordPolicyActivateRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class PasswordPolicyDTO(BaseModel):
    id: UUID
    version_no: int
    rules: dict[str, Any]
    status: Literal["draft", "active", "retired"]
    activated_at: datetime | None = None
    retired_at: datetime | None = None
    note: str | None = None


class PasswordComplianceDTO(BaseModel):
    user_id: UUID
    evaluated_policy_version: int
    required_policy_version: int
    status: Literal["compliant", "remediation_required", "remediated", "temporarily_exempt"]
    remediation_due_at: datetime | None = None
    last_notified_at: datetime | None = None
    remediated_at: datetime | None = None
    exemption_expires_at: datetime | None = None
    notification_pending: bool
    login_allowed: bool


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    reason: str = Field(default="用户完成密码整改", min_length=1, max_length=2000)


class PasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)
    reason: str = Field(min_length=1, max_length=2000)


class PasswordExemptionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    expires_in_hours: int = Field(default=24, ge=1, le=24)


class ApiRiskRuleCreateRequest(BaseModel):
    code: str = Field(min_length=3, max_length=96, pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    scope: Literal["user", "ip", "device", "api"]
    predicate: dict[str, Any] = Field(default_factory=dict)
    threshold: int = Field(ge=1, le=100000)
    window_seconds: int = Field(default=60, ge=1, le=86_400)
    action: Literal["alert", "throttle", "block"]

    @field_validator("predicate")
    @classmethod
    def validate_predicate(cls, value: dict[str, Any]) -> dict[str, Any]:
        allowed = {"route_template", "route_prefix", "method"}
        unexpected = set(value) - allowed
        if unexpected:
            raise ValueError(f"不支持的风险规则字段: {', '.join(sorted(unexpected))}")
        for key in ("route_template", "route_prefix", "method"):
            if key in value and (not isinstance(value[key], str) or len(value[key]) > 256):
                raise ValueError(f"{key} 必须是长度不超过 256 的字符串")
        if isinstance(value.get("method"), str):
            value = {**value, "method": value["method"].upper()}
        return value


class ApiRiskRuleActivateRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class ApiRiskRuleDTO(BaseModel):
    id: UUID
    code: str
    version_no: int
    scope: Literal["user", "ip", "device", "api"]
    predicate: dict[str, Any]
    threshold: int
    window_seconds: int
    action: Literal["alert", "throttle", "block"]
    status: Literal["draft", "active", "retired"]
    activated_at: datetime | None = None


class ApiRiskActionDTO(BaseModel):
    id: UUID
    action: Literal["alert", "throttle", "block", "release", "review"]
    actor_user_id: UUID | None = None
    reason: str
    result: Literal["automatic", "succeeded", "false_positive", "false_negative", "confirmed"]
    created_at: datetime


class ApiRiskEventDTO(BaseModel):
    id: UUID
    request_audit_id: UUID
    rule_id: UUID | None = None
    baseline_version: str | None = None
    severity: Literal["low", "medium", "high", "critical"]
    explanation: dict[str, Any]
    decision: Literal["allow", "throttle", "block", "released"]
    status: Literal["observed", "alerted", "mitigated", "released", "false_positive"]
    opened_at: datetime
    actions: list[ApiRiskActionDTO] = Field(default_factory=list)


class ApiRiskEventListDTO(BaseModel):
    items: list[ApiRiskEventDTO]


class ApiRiskReleaseRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class ApiRiskReviewRequest(BaseModel):
    disposition: Literal["false_positive", "false_negative", "confirmed"]
    reason: str = Field(min_length=1, max_length=2000)
