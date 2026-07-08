# Status: real

from __future__ import annotations


class EmbeddingError(Exception):
    """Base class for embedding-domain failures."""


class EmbeddingConfigurationError(EmbeddingError):
    """Invalid or missing local configuration."""


class EmbeddingAuthenticationError(EmbeddingError):
    """Provider authentication or authorization failed."""


class EmbeddingRateLimitError(EmbeddingError):
    """Provider returned a rate-limit response."""


class EmbeddingProviderError(EmbeddingError):
    """Provider/network failure that is not an input or schema problem."""


class EmbeddingResponseError(EmbeddingError):
    """Provider response shape is invalid."""


class EmbeddingDimensionError(EmbeddingResponseError):
    """Provider returned vectors with a dimension different from the contract."""


class EmbeddingInputError(EmbeddingError, ValueError):
    """Caller supplied invalid embedding input."""
