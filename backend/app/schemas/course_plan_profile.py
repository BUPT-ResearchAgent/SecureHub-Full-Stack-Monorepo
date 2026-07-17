# Status: real

"""Bounded server-owned learner profile projection for course planning.

The durable ``UserProfile`` contains a flexible JSON document.  A learning
path root must not copy that document into its input or prompt: browser-owned
fields and arbitrary values would otherwise become replayable workflow state.
This module classifies only the small, course-relevant subset into fixed
categories.  The resulting snapshot is safe to persist with a root and to
reuse after a worker restart.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


CoursePlanKnowledgeBand = Literal["foundation", "intermediate", "advanced"]
CoursePlanTargetDirection = Literal[
    "web_defense",
    "application_security",
    "secure_backend",
    "general_security",
]
CoursePlanModality = Literal["doc", "lab", "video", "quiz", "ppt", "mindmap", "readings"]
CoursePlanWeakPointFocus = Literal[
    "general_gap",
    "assessment_gap",
    "sql_injection",
    "ssrf",
    "deserialization",
    "xss",
    "authentication",
]
CoursePlanRationaleCode = Literal[
    "foundation_reinforcement",
    "advanced_acceleration",
    "web_defense_goal",
    "application_security_goal",
    "secure_backend_goal",
    "general_security_goal",
    "document_preference",
    "lab_preference",
    "video_preference",
    "quiz_preference",
    "presentation_preference",
    "mindmap_preference",
    "readings_preference",
    "general_gap_reinforcement",
    "assessment_gap_reinforcement",
    "known_weak_point_reinforcement",
]


_MODALITY_ORDER: tuple[CoursePlanModality, ...] = (
    "doc",
    "lab",
    "video",
    "quiz",
    "ppt",
    "mindmap",
    "readings",
)
_MODALITY_ALIASES: dict[str, CoursePlanModality] = {
    "doc": "doc",
    "document": "doc",
    "lab": "lab",
    "hands_on_lab": "lab",
    "video": "video",
    "quiz": "quiz",
    "ppt": "ppt",
    "slide": "ppt",
    "mindmap": "mindmap",
    "readings": "readings",
    "reading": "readings",
}


class CoursePlanProfileSnapshot(BaseModel):
    """A typed, non-sensitive projection that the planning server owns."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    base_knowledge: CoursePlanKnowledgeBand | None = None
    target_direction: CoursePlanTargetDirection | None = None
    preferred_modality: tuple[CoursePlanModality, ...] = Field(default_factory=tuple)
    weak_point_focus: CoursePlanWeakPointFocus | None = None

    @classmethod
    def from_dimensions(cls, dimensions: Mapping[str, Any] | None) -> "CoursePlanProfileSnapshot":
        """Classify persisted dimensions without retaining raw profile values."""
        values = dimensions if isinstance(dimensions, Mapping) else {}
        return cls(
            base_knowledge=_knowledge_band(values.get("base_knowledge")),
            target_direction=_target_direction(values.get("target_direction")),
            preferred_modality=_modalities(values.get("preferred_modality")),
            weak_point_focus=_weak_point_focus(values.get("weak_points")),
        )

    def compact_payload(self) -> dict[str, Any]:
        """Return the only projection representation suitable for root storage."""
        payload = self.model_dump(mode="json", exclude_none=True)
        if not payload.get("preferred_modality"):
            payload.pop("preferred_modality", None)
        return payload

    def prompt_summary(self) -> str:
        """Render a bounded server-generated prompt summary, never raw JSONB."""
        return json.dumps(self.compact_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def rationale_codes(self) -> tuple[CoursePlanRationaleCode, ...]:
        """Expose stable reason codes instead of profile text to downstream nodes."""
        codes: list[CoursePlanRationaleCode] = []
        if self.base_knowledge == "foundation":
            codes.append("foundation_reinforcement")
        elif self.base_knowledge == "advanced":
            codes.append("advanced_acceleration")

        target_code: dict[CoursePlanTargetDirection, CoursePlanRationaleCode] = {
            "web_defense": "web_defense_goal",
            "application_security": "application_security_goal",
            "secure_backend": "secure_backend_goal",
            "general_security": "general_security_goal",
        }
        if self.target_direction is not None:
            codes.append(target_code[self.target_direction])

        modality_code: dict[CoursePlanModality, CoursePlanRationaleCode] = {
            "doc": "document_preference",
            "lab": "lab_preference",
            "video": "video_preference",
            "quiz": "quiz_preference",
            "ppt": "presentation_preference",
            "mindmap": "mindmap_preference",
            "readings": "readings_preference",
        }
        if self.preferred_modality:
            codes.append(modality_code[self.preferred_modality[0]])

        if self.weak_point_focus == "general_gap":
            codes.append("general_gap_reinforcement")
        elif self.weak_point_focus == "assessment_gap":
            codes.append("assessment_gap_reinforcement")
        elif self.weak_point_focus is not None:
            codes.append("known_weak_point_reinforcement")
        return tuple(codes)


def _normalised_text(value: Any) -> str:
    return value.strip().lower() if isinstance(value, str) else ""


def _string_values(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(item for item in value if isinstance(item, str) and item.strip())
    return ()


def _knowledge_band(value: Any) -> CoursePlanKnowledgeBand | None:
    text = _normalised_text(value)
    if not text:
        return None
    if any(token in text for token in ("advanced", "expert", "senior")):
        return "advanced"
    if any(token in text for token in ("intermediate", "mid-level", "midlevel")):
        return "intermediate"
    return "foundation"


def _target_direction(value: Any) -> CoursePlanTargetDirection | None:
    text = _normalised_text(value)
    if not text:
        return None
    if "application-security" in text or "application security" in text or "appsec" in text:
        return "application_security"
    if "backend" in text or "server" in text:
        return "secure_backend"
    if "web-defense" in text or "web defense" in text or "web-security" in text or "web security" in text:
        return "web_defense"
    return "general_security"


def _modalities(value: Any) -> tuple[CoursePlanModality, ...]:
    selected: set[CoursePlanModality] = set()
    for raw in _string_values(value):
        canonical = _MODALITY_ALIASES.get(raw.strip().lower())
        if canonical is not None:
            selected.add(canonical)
    return tuple(item for item in _MODALITY_ORDER if item in selected)


def _weak_point_focus(value: Any) -> CoursePlanWeakPointFocus | None:
    text = " ".join(item.lower() for item in _string_values(value))
    if not text:
        return None
    if "assessment" in text or "quiz" in text:
        return "assessment_gap"
    if "sql" in text or "injection" in text:
        return "sql_injection"
    if "ssrf" in text:
        return "ssrf"
    if "deserial" in text:
        return "deserialization"
    if "xss" in text or "cross-site scripting" in text:
        return "xss"
    if "auth" in text or "session" in text:
        return "authentication"
    return "general_gap"


__all__ = [
    "CoursePlanKnowledgeBand",
    "CoursePlanModality",
    "CoursePlanProfileSnapshot",
    "CoursePlanRationaleCode",
    "CoursePlanTargetDirection",
    "CoursePlanWeakPointFocus",
]
