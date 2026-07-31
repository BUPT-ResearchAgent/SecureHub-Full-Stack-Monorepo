# Status: real

"""Educational media generation infrastructure.

The package is deliberately a service boundary, not a tenth Agent. Existing
Agents may produce prompts or storyboards while this layer owns provider I/O
and durable binary storage.
"""

from app.services.media.volcengine_image_service import (
    GeneratedImageAsset,
    MediaConfigurationError,
    MediaProviderError,
    VolcengineImageService,
)

__all__ = [
    "GeneratedImageAsset",
    "MediaConfigurationError",
    "MediaProviderError",
    "VolcengineImageService",
]
