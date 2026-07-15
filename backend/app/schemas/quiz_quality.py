# Status: real

"""Typed contracts for the durable WEBSEC-101 quiz bank and its quality gate."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


QuizItemType = Literal["single_choice", "multi_choice", "fill", "short_answer", "code"]
QuizReviewStatus = Literal[
    "draft",
    "pre-generated",
    "curated",
    "codex-reviewed-pending-human",
    "rejected",
    "withdrawn",
]
QuizSourceStatus = Literal["seeded", "curated", "generated", "imported", "legacy-migrated"]


class QuizEvidenceDTO(BaseModel):
    chunk_id: UUID
    citation_label: str | None = None


class QuizQualityStateDTO(BaseModel):
    validator_version: str
    input_fingerprint: str
    result: Literal["pending", "passed", "failed"]
    failure_codes: list[str] = Field(default_factory=list)
    reviewed_at: datetime | None = None


class QuizBankItemDTO(BaseModel):
    id: UUID
    canonical_key: str
    content_version: int = Field(ge=1)
    knowledge_node_id: UUID
    knowledge_node_name: str
    type: QuizItemType
    question: str
    options: list[str] = Field(default_factory=list)
    answer: str
    explanation: str
    difficulty: int = Field(ge=1, le=5)
    review_status: QuizReviewStatus
    source_status: QuizSourceStatus
    evidence: list[QuizEvidenceDTO] = Field(default_factory=list)
    quality: QuizQualityStateDTO | None = None


class QuizBankListDTO(BaseModel):
    course_id: UUID
    course_code: Literal["WEBSEC-101"]
    items: list[QuizBankItemDTO]
    coverage: dict[str, Any]


class PublishedQuizListDTO(BaseModel):
    course_id: UUID
    course_code: Literal["WEBSEC-101"]
    items: list[QuizBankItemDTO]


class QuizQualityFailureSampleDTO(BaseModel):
    quiz_item_id: UUID
    canonical_key: str
    failure_codes: list[str]


class QuizQualityItemResultDTO(QuizQualityStateDTO):
    quiz_item_id: UUID
    canonical_key: str


class QuizQualityRunDTO(BaseModel):
    course_id: UUID
    course_code: Literal["WEBSEC-101"]
    validator_version: str
    input_fingerprint: str
    result: Literal["passed", "failed"]
    rules: dict[str, Any]
    coverage: dict[str, Any]
    type_distribution: dict[str, int]
    items: list[QuizQualityItemResultDTO]
    failure_samples: list[QuizQualityFailureSampleDTO] = Field(default_factory=list)
