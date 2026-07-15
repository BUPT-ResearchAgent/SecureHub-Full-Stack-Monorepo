# Status: real

"""JWT authentication endpoints."""

from fastapi import APIRouter

from app.deps import (
    RequiredCurrentUserDep,
    SessionDep,
    SettingsDep,
)
from app.schemas.auth import AuthUser, LoginRequest, PasswordRemediationRequest, RegisterRequest, TokenResponse
from app.schemas.security import PasswordChangeRequest, PasswordComplianceDTO
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


@router.post("/password/remediate", response_model=PasswordComplianceDTO)
async def remediate_password(
    payload: PasswordRemediationRequest,
    session: SessionDep,
    settings: SettingsDep,
) -> PasswordComplianceDTO:
    return await AuthService(session, settings).remediate_password(payload)


@router.get("/me", response_model=AuthUser)
async def me(user: RequiredCurrentUserDep) -> AuthUser:
    return AuthUser(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        role=user.role,
    )


@router.post("/password/change", response_model=PasswordComplianceDTO)
async def change_password(
    payload: PasswordChangeRequest,
    session: SessionDep,
    settings: SettingsDep,
    user: RequiredCurrentUserDep,
) -> PasswordComplianceDTO:
    return await AuthService(session, settings).change_password(user=user, payload=payload)


@router.post("/logout")
async def logout() -> dict[str, bool]:
    return {"ok": True}


__all__ = ["router"]
