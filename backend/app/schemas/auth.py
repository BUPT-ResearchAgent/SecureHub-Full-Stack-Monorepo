# Status: real

"""Pydantic schemas for JWT-based authentication."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def _validate_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 255 or "@" not in email:
        raise ValueError("邮箱格式错误")
    local, _, domain = email.partition("@")
    if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise ValueError("邮箱格式错误")
    return email


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email(value)

    @field_validator("display_name")
    @classmethod
    def trim_display_name(cls, value: str) -> str:
        display_name = value.strip()
        if not display_name:
            raise ValueError("显示名称不能为空")
        return display_name


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email(value)


class AuthUser(BaseModel):
    id: UUID
    email: str
    display_name: str
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    user: AuthUser
