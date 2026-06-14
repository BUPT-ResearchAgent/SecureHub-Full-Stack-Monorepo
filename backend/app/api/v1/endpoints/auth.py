# Status: real

"""JWT authentication endpoints."""

from fastapi import APIRouter

from app.deps import (
    RequiredCurrentUserDep,
    SessionDep,
    SettingsDep,
)
from app.schemas.auth import AuthUser, LoginRequest, RegisterRequest, TokenResponse
from app.services.identity.auth_service import AuthService

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    session: SessionDep,
    settings: SettingsDep,
) -> TokenResponse:
    return await AuthService(session, settings).register(payload)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: SessionDep,
    settings: SettingsDep,
) -> TokenResponse:
    return await AuthService(session, settings).login(payload)


@router.get("/me", response_model=AuthUser)
async def me(user: RequiredCurrentUserDep) -> AuthUser:
    return AuthUser(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
    )


@router.post("/logout")
async def logout() -> dict[str, bool]:
    return {"ok": True}


__all__ = ["router"]
