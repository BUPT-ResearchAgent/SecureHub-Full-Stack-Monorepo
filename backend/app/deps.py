# Status: real

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models.identity.user import User
from app.db.seeds._constants import DEMO_USER_ID
from app.db.session import get_session
from app.services.identity.auth_service import AuthService

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]

_optional_bearer = HTTPBearer(auto_error=False)


async def required_current_user(
    session: SessionDep,
    settings: SettingsDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_optional_bearer)
    ],
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_REQUIRED", "message": "请先登录"},
        )
    return await AuthService(session, settings).get_current_user(credentials.credentials)


async def required_current_user_id(
    user: Annotated[User, Depends(required_current_user)],
) -> UUID:
    return user.id


async def current_user(
    session: SessionDep,
    settings: SettingsDep,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_optional_bearer)
    ],
) -> User | None:
    """JWT-backed user when present; None keeps demo fallback endpoints alive."""
    if credentials is None:
        return None
    return await AuthService(session, settings).get_current_user(credentials.credentials)


async def current_user_id(user: Annotated[User | None, Depends(current_user)]) -> UUID:
    """Real JWT user id when a token is supplied; otherwise seeded demo user.

    Existing P0 demo endpoints still support no-token calls. New auth endpoints
    use RequiredCurrentUserDep / RequiredCurrentUserIdDep and do not fall back.
    """
    if user is not None:
        return user.id
    return DEMO_USER_ID


CurrentUserDep = Annotated[UUID, Depends(current_user_id)]
CurrentUserObjectDep = Annotated[User | None, Depends(current_user)]
RequiredCurrentUserDep = Annotated[User, Depends(required_current_user)]
RequiredCurrentUserIdDep = Annotated[UUID, Depends(required_current_user_id)]
