# Status: partial-real

"""Bounded, persistent retrieval support for the WEBSEC-101 showcase seed.

The controlled index is intentionally separate from the configured production
embedding profile.  It exists only for the explicit local / competition /
authorised-test WEBSEC-101 seed and is never a substitute for a live provider
or a production index.
"""

from __future__ import annotations

from app.core.config import Settings
from app.llm.embeddings.fixture import DeterministicFixtureEmbeddingProvider


CONTROLLED_SHOWCASE_EMBEDDING_PROFILE = (
    "controlled-showcase-fixture:websec-101:1024:dense:v1"
)
_DISALLOWED_ENVIRONMENTS = {"production", "prod", "release"}


def is_controlled_showcase_index_allowed(settings: Settings, *, domain: str) -> bool:
    """Return whether the explicit local WEBSEC-101 index may be consumed.

    This narrow guard is deliberately duplicated at write and read boundaries:
    controlled demo vectors must never become a transparent fallback for a
    production Qwen-backed retrieval index.
    """

    return (
        domain == "course_websec"
        and settings.APP_ENV.strip().lower() not in _DISALLOWED_ENVIRONMENTS
    )


def controlled_showcase_embedding_provider(
    settings: Settings,
) -> DeterministicFixtureEmbeddingProvider:
    """Create the deterministic provider used by the persisted showcase index."""

    return DeterministicFixtureEmbeddingProvider(
        dimension=settings.EMBEDDING_DIM,
        profile=CONTROLLED_SHOWCASE_EMBEDDING_PROFILE,
    )


__all__ = [
    "CONTROLLED_SHOWCASE_EMBEDDING_PROFILE",
    "controlled_showcase_embedding_provider",
    "is_controlled_showcase_index_allowed",
]
