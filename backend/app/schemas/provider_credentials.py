# Status: real

"""Wire schemas that never serialize or retain provider API key plaintext."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


ProviderName = Literal["deepseek", "xfyun"]
VerificationStatus = Literal["unverified", "verified", "invalid", "error"]


class ProviderCredentialCreateRequest(BaseModel):
    provider: ProviderName
    name: str = Field(min_length=1, max_length=120)
    api_key: SecretStr
    activate: bool = False

    @field_validator("name")
    @classmethod
    def normalise_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name is required")
        return cleaned

    @field_validator("api_key")
    @classmethod
    def require_key(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("API key is required")
        return value


class ProviderCredentialResponse(BaseModel):
    """Safe projection: ciphertext and plaintext are intentionally absent."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: ProviderName
    name: str
    fingerprint: str = Field(validation_alias="key_fingerprint")
    is_active: bool
    verification_status: VerificationStatus
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ProviderCredentialListResponse(BaseModel):
    items: list[ProviderCredentialResponse] = Field(default_factory=list)
