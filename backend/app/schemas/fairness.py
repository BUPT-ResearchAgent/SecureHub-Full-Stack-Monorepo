# Status: real

"""HTTP contracts for consent-gated fairness monitoring."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class FairnessPolicyCreateRequest(BaseModel):
    code: str = Field(min_length=3, max_length=96, pattern=r"^[a-z0-9][a-z0-9-]*$")
    version_no: int = Field(ge=1)
    purpose: str = Field(min_length=8, max_length=1000)
    allowed_group_keys: list[str] = Field(min_length=1, max_length=2)
    minimum_sample: int = Field(ge=2, le=10000)
    pass_score: float = Field(ge=0, le=100000)
    retention_days: int = Field(ge=1, le=3650)
    thresholds: dict[str, float] = Field(default_factory=dict)

    @field_validator("allowed_group_keys")
    @classmethod
    def normalize_keys(cls, value: list[str]) -> list[str]:
        return sorted({item.strip() for item in value if item.strip()})


class FairnessPolicyDTO(BaseModel):
    id: UUID
    code: str
    version_no: int
    purpose: str
    allowed_group_keys: list[str]
    minimum_sample: int
    pass_score: float
    retention_days: int
    thresholds: dict[str, Any]
    status: Literal["draft", "active", "retired"]
    activated_at: datetime | None = None


class FairnessConsentRequest(BaseModel):
    policy_id: UUID
    scope: str = Field(default="assessment_fairness", min_length=3, max_length=64)
    expires_at: datetime


class FairnessConsentDTO(BaseModel):
    id: UUID
    policy_id: UUID
    user_id: UUID
    scope: str
    status: Literal["granted", "withdrawn", "expired"]
    granted_at: datetime
    withdrawn_at: datetime | None = None
    expires_at: datetime


class FairnessConsentWithdrawRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class FairnessGroupAssignmentRequest(BaseModel):
    user_id: UUID
    group_key: str = Field(min_length=1, max_length=64)
    minimal_group_value: str = Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9_-]+$")
    expires_at: datetime
    reason: str = Field(min_length=1, max_length=500)


class FairnessGroupAssignmentDTO(BaseModel):
    id: UUID
    user_id: UUID
    policy_id: UUID
    group_key: str
    minimal_group_value: str
    expires_at: datetime


class FairnessMetricRunRequest(BaseModel):
    assessment_ids: list[UUID] = Field(min_length=1, max_length=500)
    formula_version: str = Field(default="fairness-aggregate-v1", min_length=3, max_length=64)


class FairnessMetricCellDTO(BaseModel):
    id: UUID
    group_key: str
    group_value: str
    sample_size: int
    mean_score: float
    pass_rate: float
    accuracy: float | None = None
    fpr: float | None = None
    fnr: float | None = None
    equal_opportunity_delta: float | None = None
    confidence_interval: dict[str, Any]
    limitations: dict[str, Any]


class FairnessAlertDTO(BaseModel):
    id: UUID
    metric_cell_id: UUID
    alert_kind: str
    severity: Literal["low", "medium", "high"]
    explanation: dict[str, Any]
    status: Literal["open", "under_review", "resolved", "dismissed"]
    opened_at: datetime
    resolved_at: datetime | None = None


class FairnessMetricRunDTO(BaseModel):
    id: UUID
    policy_id: UUID
    policy_version: str
    assessment_scope: dict[str, Any]
    dataset_fingerprint: str
    formula_version: str
    status: Literal["pending", "completed", "insufficient_sample", "rejected"]
    rejection_code: str | None = None
    limitations: dict[str, Any]
    sample_size: int
    started_at: datetime
    finished_at: datetime | None = None
    cells: list[FairnessMetricCellDTO] = Field(default_factory=list)
    alerts: list[FairnessAlertDTO] = Field(default_factory=list)


class FairnessDashboardDTO(BaseModel):
    items: list[FairnessMetricRunDTO]
    calculated_at: datetime
    visibility: Literal["administrator_only"] = "administrator_only"
    policy_note: str


class FairnessReviewRequest(BaseModel):
    status: Literal["under_review", "resolved", "dismissed"]
    reason: str = Field(min_length=1, max_length=1000)
    outcome_note: str | None = Field(default=None, max_length=1000)


class FairnessReviewDTO(BaseModel):
    id: UUID
    alert_id: UUID
    reviewer_id: UUID
    status: Literal["under_review", "resolved", "dismissed"]
    reason: str
    outcome_note: str | None = None
    reviewed_at: datetime


class FairnessAppealCreateRequest(BaseModel):
    grade_decision_id: UUID
    reason: str = Field(min_length=1, max_length=1000)


class FairnessAppealResolveRequest(BaseModel):
    status: Literal["reviewing", "resolved", "closed"]
    response_note: str = Field(min_length=1, max_length=1000)


class FairnessAppealDTO(BaseModel):
    id: UUID
    grade_decision_id: UUID
    appellant_user_id: UUID
    reason: str
    status: Literal["submitted", "reviewing", "resolved", "closed"]
    reviewer_id: UUID | None = None
    response_note: str | None = None
    submitted_at: datetime
    reviewed_at: datetime | None = None


class FairnessAppealListDTO(BaseModel):
    items: list[FairnessAppealDTO]


class AppealableGradeDTO(BaseModel):
    grade_decision_id: UUID
    submission_id: UUID
    final_score: float
    published_at: datetime | None = None


class AppealableGradeListDTO(BaseModel):
    items: list[AppealableGradeDTO]
