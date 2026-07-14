# Status: real

"""Static input/output metadata for the fixed production Skill catalog.

These models are not an execution API. RuntimeEngine resolves them into a
SkillDefinition and SkillExecutor owns every real or fixture invocation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SkillInput(BaseModel):
    user_id: str
    query: str
    domain: str = "course_websec"


class SkillOutput(BaseModel):
    content: str = ""
    evidence_chunk_ids: list[str] = Field(default_factory=list)
    quality_score: float = 0.0


__all__ = ["SkillInput", "SkillOutput"]
