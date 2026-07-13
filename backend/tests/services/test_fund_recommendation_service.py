"""Focused server-owned profile snapshot checks for S7."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.fund_recommendation import FundRecommendationRequest
from app.services.fund_recommendation_service import FundRecommendationService


class _ScalarRows:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class _Capability:
    def __init__(self, dimension: str, score: float, confidence: float):
        self.dimension = dimension
        self.score = score
        self.confidence = confidence


class _Profile:
    dimensions = {
        "career_goal": "甲方安全工程师",
        "interest_anchors": ["Web 安全"],
        "untrusted_note": "must not enter root input",
    }


class _Session:
    async def get(self, *_args):
        return _Profile()

    async def scalars(self, *_args):
        return _ScalarRows([_Capability("web_security", 0.8, 0.7), _Capability("ai_security", 0.4, 0.6)])


def test_fund_root_payload_reads_only_the_allowlisted_durable_profile() -> None:
    payload = asyncio.run(
        FundRecommendationService(_Session()).prepare_root_input(  # type: ignore[arg-type]
            user_id=uuid4(),
            request=FundRecommendationRequest(),
        )
    )

    assert payload["domain"] == "fund"
    assert payload["profile_snapshot"]["dimensions"] == {
        "career_goal": "甲方安全工程师",
        "interest_anchors": ["Web 安全"],
    }
    assert [item["dimension"] for item in payload["profile_snapshot"]["capabilities"]] == ["web_security", "ai_security"]
    assert "untrusted_note" not in payload["persona_summary"]


def test_fund_request_rejects_a_browser_supplied_user_id_or_fixture_mode() -> None:
    with pytest.raises(ValidationError):
        FundRecommendationRequest.model_validate({"user_id": str(uuid4())})
    with pytest.raises(ValidationError):
        FundRecommendationRequest.model_validate({"mode": "fixture"})
