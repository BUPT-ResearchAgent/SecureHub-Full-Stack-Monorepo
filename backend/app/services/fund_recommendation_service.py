# Status: real

"""Authenticated root-input preparation for ``fund_recommendation_v1``."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.identity.user_capability import UserCapability
from app.db.models.identity.user_profile import UserProfile
from app.schemas.fund_recommendation import FundProfileCapability, FundProfileSnapshot, FundRecommendationRequest


_PROFILE_KEYS = frozenset(
    {
        "knowledge_basis",
        "cognitive_style",
        "easy_mistakes",
        "learning_pace",
        "interest_anchors",
        "career_goal",
        "base_knowledge",
        "preferred_modality",
        "time_budget",
        "target_direction",
        "motivation",
    }
)


class FundRecommendationService:
    """Reads the single durable profile/capability source before creating a root.

    The resulting snapshot is bounded and attached to the immutable root input
    by an authenticated product adapter. It is not a second profile table and
    callers cannot submit or replace it.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def prepare_root_input(
        self,
        *,
        user_id: UUID,
        request: FundRecommendationRequest,
    ) -> dict[str, Any]:
        profile = await self.session.get(UserProfile, user_id)
        raw_dimensions = dict(profile.dimensions or {}) if profile is not None else {}
        dimensions = {
            key: value
            for key, value in raw_dimensions.items()
            if isinstance(key, str) and key in _PROFILE_KEYS
        }
        capabilities = [
            FundProfileCapability(
                dimension=str(row.dimension),
                score=max(0.0, min(1.0, float(row.score))),
                confidence=max(0.0, min(1.0, float(row.confidence))),
            )
            for row in (
                await self.session.scalars(
                    select(UserCapability)
                    .where(UserCapability.user_id == user_id)
                    .order_by(UserCapability.dimension)
                )
            ).all()
        ]
        snapshot = FundProfileSnapshot(dimensions=dimensions, capabilities=capabilities)
        profile_summary = json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))[:800]
        return {
            "query": request.query,
            "domain": "fund",
            "course_context": request.course_context.model_dump(mode="json"),
            "profile_snapshot": snapshot.model_dump(mode="json"),
            "persona_summary": profile_summary,
        }


__all__ = ["FundRecommendationService"]
