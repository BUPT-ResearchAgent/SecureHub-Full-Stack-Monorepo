# Status: real

"""Registration, login, and current-user lookup for JWT authentication."""

from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import (
    AuthTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.core.config import Settings
from app.db.models.identity.user import User
from app.repositories.identity.capabilities import UserCapabilityRepository
from app.repositories.identity.profiles import UserProfileRepository
from app.repositories.identity.users import UserRepository
from app.schemas.auth import AuthUser, LoginRequest, RegisterRequest, TokenResponse

DEFAULT_CAPABILITY_DIMENSIONS = (
    "web_security",
    "crypto",
    "reverse",
    "binary_exploitation",
    "ai_security",
    "system_security",
    "network_security",
    "engineering_practice",
    "academic_writing",
)


def _auth_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def _to_auth_user(user: User) -> AuthUser:
    return AuthUser(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
    )


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings):
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)
        self.profiles = UserProfileRepository(session)
        self.capabilities = UserCapabilityRepository(session)

    async def register(self, payload: RegisterRequest) -> TokenResponse:
        email = payload.email.strip().lower()
        display_name = payload.display_name.strip()

        self._validate_password_strength(payload.password)

        if await self.users.get_by_email(email) is not None:
            raise _auth_error(status.HTTP_409_CONFLICT, "EMAIL_EXISTS", "该邮箱已注册")

        try:
            user = await self.users.create(
                user_id=uuid4(),
                email=email,
                display_name=display_name,
                hashed_password=hash_password(payload.password),
                is_active=True,
            )
            await self.profiles.upsert(user_id=user.id, dimensions={})
            for dimension in DEFAULT_CAPABILITY_DIMENSIONS:
                await self.capabilities.upsert_score(
                    user_id=user.id,
                    dimension=dimension,
                    score=0.0,
                    confidence=0.0,
                    evidence_count=0,
                    metadata={"source": "auth_register_default"},
                )
            await self.session.commit()
        except IntegrityError as err:
            await self.session.rollback()
            raise _auth_error(status.HTTP_409_CONFLICT, "EMAIL_EXISTS", "该邮箱已注册") from err

        return self._token_response(user)

    async def login(self, payload: LoginRequest) -> TokenResponse:
        email = payload.email.strip().lower()
        user = await self.users.get_by_email(email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise _auth_error(
                status.HTTP_401_UNAUTHORIZED,
                "INVALID_CREDENTIALS",
                "账号或密码错误",
            )
        if not user.is_active:
            raise _auth_error(status.HTTP_403_FORBIDDEN, "USER_DISABLED", "账号已停用")
        return self._token_response(user)

    async def get_current_user(self, token: str) -> User:
        try:
            user_id = decode_access_token(token, self.settings)
        except AuthTokenError as err:
            raise _auth_error(status.HTTP_401_UNAUTHORIZED, "INVALID_TOKEN", "认证已失效") from err

        user = await self.users.get_by_id(user_id)
        if user is None:
            raise _auth_error(status.HTTP_401_UNAUTHORIZED, "INVALID_TOKEN", "认证已失效")
        if not user.is_active:
            raise _auth_error(status.HTTP_403_FORBIDDEN, "USER_DISABLED", "账号已停用")
        return user

    def _token_response(self, user: User) -> TokenResponse:
        token, expires_at = create_access_token(user.id, self.settings)
        return TokenResponse(
            access_token=token,
            expires_at=expires_at,
            user=_to_auth_user(user),
        )

    @staticmethod
    def _validate_password_strength(password: str) -> None:
        has_upper = any(ch.isupper() for ch in password)
        has_lower = any(ch.islower() for ch in password)
        has_digit = any(ch.isdigit() for ch in password)
        has_symbol = any(not ch.isalnum() for ch in password)
        if (
            len(password) < 8
            or len(password.encode("utf-8")) > 72
            or not (has_upper and has_lower and has_digit and has_symbol)
        ):
            raise _auth_error(
                status.HTTP_400_BAD_REQUEST,
                "PASSWORD_WEAK",
                "密码强度不足",
            )
