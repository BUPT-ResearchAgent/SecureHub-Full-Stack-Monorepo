# Status: real

"""Password hashing and JWT helpers for SecureHub authentication."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt as _bcrypt
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import Settings

JWT_ALGORITHM = "HS256"

if not hasattr(_bcrypt, "__about__"):
    _bcrypt.__about__ = type("_About", (), {"__version__": getattr(_bcrypt, "__version__", "unknown")})()

if not getattr(_bcrypt.hashpw, "_securehub_passlib_compat", False):
    _bcrypt_hashpw = _bcrypt.hashpw

    def _hashpw_passlib_compat(password: bytes, salt: bytes) -> bytes:
        # passlib 1.7.x probes bcrypt with an over-72-byte secret. bcrypt 5
        # raises instead of applying historical bcrypt truncation, so keep the
        # compatibility local to the hashing backend used by passlib.
        if len(password) > 72:
            password = password[:72]
        return _bcrypt_hashpw(password, salt)

    _hashpw_passlib_compat._securehub_passlib_compat = True  # type: ignore[attr-defined]
    _bcrypt.hashpw = _hashpw_passlib_compat  # type: ignore[assignment]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthTokenError(ValueError):
    """Raised when a bearer token is expired, malformed, or missing a UUID sub."""


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        return False
    return pwd_context.verify(password, hashed_password)


def create_access_token(user_id: UUID, settings: Settings) -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
        "typ": "access",
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expires_at


def decode_access_token(token: str, settings: Settings) -> UUID:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[JWT_ALGORITHM])
        subject = payload.get("sub")
        if not isinstance(subject, str):
            raise AuthTokenError("invalid token subject")
        return UUID(subject)
    except (JWTError, ValueError) as err:
        raise AuthTokenError("invalid or expired token") from err
