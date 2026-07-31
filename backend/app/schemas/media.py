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
# Older persisted chat messages may still submit the pre-Agent-Plan values.
# The provider service normalizes them to the documented Agent Plan size.
ImageSize = Literal["1024x1024", "2048x2048", "2K"]
VideoSize = Literal["1280x720", "720x1280"]
VideoDuration = Literal["10"]


class EducationalImageGenerateRequest(BaseModel):
    kp_id: str = Field(pattern=r"^[a-z0-9-]{2,64}$")
    prompt: str | None = Field(default=None, min_length=8, max_length=2_000)
    size: ImageSize = "2K"
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


class VideoGenerateRequest(BaseModel):
    prompt: str = Field(min_length=8, max_length=2_000)
    kp_id: str | None = Field(
        default=None,
        pattern=r"^[a-z0-9-]{2,64}$",
    )
    size: VideoSize = "1280x720"
    duration: VideoDuration = "10"
    reference_image_url: str | None = Field(
        default=None,
        min_length=8,
        max_length=2_048,
    )


class VideoGenerateResponse(BaseModel):
    task_id: str
    status: Literal["submitted"] = "submitted"
    provider: Literal["wuyinkeji-omni"] = "wuyinkeji-omni"
    model: str


class VideoStatusResponse(BaseModel):
    task_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    video_url: str | None = None
    object_key: str | None = None
    error_message: str | None = None
    provider: Literal["wuyinkeji-omni"] = "wuyinkeji-omni"
    model: str
    prompt: str
    kp_id: str | None = None
    size: VideoSize
    duration: VideoDuration
    media_type: Literal["video/mp4", "video/webm"] | None = None
    byte_size: int | None = None
    generated_at: str | None = None


__all__ = [
    "EducationalImageGenerateRequest",
    "EducationalImageGenerateResponse",
    "ImageSize",
    "VideoDuration",
    "VideoGenerateRequest",
    "VideoGenerateResponse",
    "VideoSize",
    "VideoStatusResponse",
    "VisualizationType",
]
