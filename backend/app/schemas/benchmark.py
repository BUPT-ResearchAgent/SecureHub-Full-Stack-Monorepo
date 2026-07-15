# Status: real

"""HTTP contracts for frozen, reproducible benchmark runs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class BenchmarkDatasetDTO(BaseModel):
    id: UUID
    kind: Literal["content_relevance", "api_misuse", "fairness"]
    semantic_version: str
    manifest_hash: str
    label_schema_version: str
    source_note: str
    status: Literal["draft", "frozen", "retired"]
    frozen_at: datetime | None = None


class BenchmarkDatasetListDTO(BaseModel):
    items: list[BenchmarkDatasetDTO]


class BenchmarkRunRequest(BaseModel):
    formula_version: str = Field(default="binary-confusion-v1", min_length=3, max_length=64)
    thresholds: dict[str, float] = Field(default_factory=dict)


class BenchmarkCaseResultDTO(BaseModel):
    case_key: str
    expected_label: str
    predicted_label: str
    decision: Literal["tp", "tn", "fp", "fn", "not_scored"]
    failure_reason: str | None = None
    redacted_payload_reference: str


class BenchmarkRunDTO(BaseModel):
    id: UUID
    dataset_version_id: UUID
    dataset_kind: Literal["content_relevance", "api_misuse", "fairness"]
    dataset_version: str
    formula_version: str
    thresholds: dict[str, Any]
    code_revision: str
    config_fingerprint: str
    status: Literal["queued", "running", "completed", "failed", "rejected"]
    summary: dict[str, Any]
    failure_code: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    cases: list[BenchmarkCaseResultDTO] = Field(default_factory=list)
