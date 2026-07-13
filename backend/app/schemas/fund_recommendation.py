# Status: real

"""Typed, authenticated fund-recommendation product and workflow DTOs."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FundCourseContext(BaseModel):
    """Optional bounded course hand-off. A course workflow root is never valid here."""

    course_id: UUID | None = None
    knowledge_point_id: UUID | None = None
    model_config = ConfigDict(extra="forbid")


class FundRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(default="根据我的能力画像推荐可核验的网络安全科研机会", min_length=8, max_length=600)
    course_context: FundCourseContext = Field(default_factory=FundCourseContext)
    # S7 has no PresenterMode fallback. The adapter deliberately refuses
    # fixture roots so an unavailable real runtime is visible to the user.
    mode: Literal["real"] = "real"
    provider: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=160)


class FundProfileCapability(BaseModel):
    dimension: str = Field(min_length=1, max_length=120)
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)


class FundProfileSnapshot(BaseModel):
    dimensions: dict[str, Any] = Field(default_factory=dict)
    capabilities: list[FundProfileCapability] = Field(default_factory=list)


class FundRecommendationItem(BaseModel):
    fund_name: str = Field(min_length=1, max_length=240)
    source_name: str = Field(min_length=1, max_length=160)
    source_url: str = Field(min_length=1, max_length=2_000)
    deadline: str = Field(min_length=1, max_length=120)
    level: str = Field(min_length=1, max_length=120)
    direction: str = Field(min_length=1, max_length=240)
    fit_score: float = Field(ge=0.0, le=1.0)
    matched_profile_dimensions: list[str] = Field(min_length=1, max_length=8)
    reason: str = Field(min_length=1, max_length=1_200)
    gaps_or_risks: list[str] = Field(default_factory=list, max_length=8)
    next_action: str = Field(min_length=1, max_length=600)
    evidence_snapshot_ids: list[str] = Field(default_factory=list)


class FundRecommendationResult(BaseModel):
    recommendations: list[FundRecommendationItem] = Field(default_factory=list, max_length=3)
    landscape_summary: str = Field(default="", max_length=1_200)
    profile_dimensions_used: list[str] = Field(default_factory=list, max_length=20)
    evidence_snapshot_ids: list[str] = Field(default_factory=list)
