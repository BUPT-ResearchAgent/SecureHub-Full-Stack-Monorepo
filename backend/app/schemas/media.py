# Status: real

"""Request/response contracts for educational media infrastructure."""

from typing import Literal

from pydantic import BaseModel, Field


VisualizationType = Literal[
    "architecture",
    "attack-defense",
    "checklist",
    "flowchart",
    "matrix",
    "sequence",
]
ImageSize = Literal["1024x1024", "2048x2048", "2K"]


class EducationalImageGenerateRequest(BaseModel):
    kp_id: str = Field(pattern=r"^[a-z0-9-]{2,64}$")
    prompt: str | None = Field(default=None, min_length=8, max_length=2_000)
    size: ImageSize = "1024x1024"
    visualization_type: VisualizationType | None = None


class EducationalImageGenerateResponse(BaseModel):
    image_url: str
    object_key: str
    prompt_used: str
    model: str
    provider: Literal["volcengine-ark"]
    source: Literal["live"] = "live"
    kp_id: str
    media_type: str
    byte_size: int


__all__ = [
    "EducationalImageGenerateRequest",
    "EducationalImageGenerateResponse",
    "ImageSize",
    "VisualizationType",
]
