# Status: real

"""Authenticated API for a user's encrypted DeepSeek/XFYUN key pool."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from app.deps import RequiredCurrentUserDep, SessionDep, SettingsDep
from app.schemas.provider_credentials import (
    ProviderCredentialCreateRequest,
    ProviderCredentialListResponse,
    ProviderCredentialResponse,
)
from app.services.provider_credentials import ProviderCredentialError, ProviderCredentialService


router = APIRouter(prefix="/provider-credentials")


def _service(session: SessionDep, settings: SettingsDep) -> ProviderCredentialService:
    return ProviderCredentialService(session, settings)


def _raise(error: ProviderCredentialError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": str(error)},
    ) from error


@router.get("", response_model=ProviderCredentialListResponse)
async def list_provider_credentials(
    session: SessionDep,
    settings: SettingsDep,
    user: RequiredCurrentUserDep,
) -> ProviderCredentialListResponse:
    rows = await _service(session, settings).list(user.id)
    return ProviderCredentialListResponse(items=[ProviderCredentialResponse.model_validate(row) for row in rows])


@router.post("", response_model=ProviderCredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_provider_credential(
    payload: ProviderCredentialCreateRequest,
    session: SessionDep,
    settings: SettingsDep,
    user: RequiredCurrentUserDep,
) -> ProviderCredentialResponse:
    try:
        row = await _service(session, settings).create(
            user_id=user.id,
            provider=payload.provider,
            name=payload.name,
            api_key=payload.api_key.get_secret_value(),
            activate=payload.activate,
        )
    except ProviderCredentialError as exc:
        _raise(exc)
    return ProviderCredentialResponse.model_validate(row)


@router.post("/{credential_id}/activate", response_model=ProviderCredentialResponse)
async def activate_provider_credential(
    credential_id: UUID,
    session: SessionDep,
    settings: SettingsDep,
    user: RequiredCurrentUserDep,
) -> ProviderCredentialResponse:
    try:
        row = await _service(session, settings).activate(user_id=user.id, credential_id=credential_id)
    except ProviderCredentialError as exc:
        _raise(exc)
    return ProviderCredentialResponse.model_validate(row)


@router.post("/{credential_id}/deactivate", response_model=ProviderCredentialResponse)
async def deactivate_provider_credential(
    credential_id: UUID,
    session: SessionDep,
    settings: SettingsDep,
    user: RequiredCurrentUserDep,
) -> ProviderCredentialResponse:
    try:
        row = await _service(session, settings).deactivate(user_id=user.id, credential_id=credential_id)
    except ProviderCredentialError as exc:
        _raise(exc)
    return ProviderCredentialResponse.model_validate(row)


@router.post("/{credential_id}/verify", response_model=ProviderCredentialResponse)
async def verify_provider_credential(
    credential_id: UUID,
    session: SessionDep,
    settings: SettingsDep,
    user: RequiredCurrentUserDep,
) -> ProviderCredentialResponse:
    try:
        row = await _service(session, settings).verify(user_id=user.id, credential_id=credential_id)
    except ProviderCredentialError as exc:
        _raise(exc)
    return ProviderCredentialResponse.model_validate(row)


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider_credential(
    credential_id: UUID,
    session: SessionDep,
    settings: SettingsDep,
    user: RequiredCurrentUserDep,
) -> Response:
    try:
        await _service(session, settings).delete(user_id=user.id, credential_id=credential_id)
    except ProviderCredentialError as exc:
        _raise(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
