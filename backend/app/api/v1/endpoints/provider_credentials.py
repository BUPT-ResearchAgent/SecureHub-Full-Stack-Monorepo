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
    ProviderModelSelectionRequest,
    ProviderModelSelectionResponse,
    ProviderModelSourceResponse,
    ProviderModelSourceVerifyResponse,
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
    service = _service(session, settings)
    rows = await service.list(user.id)
    sources, selected = await service.list_model_sources(user.id)
    return ProviderCredentialListResponse(
        items=[ProviderCredentialResponse.model_validate(row) for row in rows],
        sources=[
            ProviderModelSourceResponse(
                provider=source.provider,
                model=source.model,
                label=source.label,
                model_label=source.model_label,
                is_selected=is_selected,
                has_active_credential=has_active_credential,
            )
            for source, is_selected, has_active_credential in sources
        ],
        selection=ProviderModelSelectionResponse(
            provider=selected.provider,
            model=selected.model,
            label=selected.label,
            model_label=selected.model_label,
        ),
    )


@router.post("/selection", response_model=ProviderModelSelectionResponse)
async def select_provider_model_source(
    payload: ProviderModelSelectionRequest,
    session: SessionDep,
    settings: SettingsDep,
    user: RequiredCurrentUserDep,
) -> ProviderModelSelectionResponse:
    try:
        selected = await _service(session, settings).select_model_source(
            user_id=user.id,
            provider=payload.provider,
            model=payload.model,
        )
    except ProviderCredentialError as exc:
        _raise(exc)
    return ProviderModelSelectionResponse(
        provider=selected.provider,
        model=selected.model,
        label=selected.label,
        model_label=selected.model_label,
    )


@router.post("/source-verification", response_model=ProviderModelSourceVerifyResponse)
async def verify_provider_model_source(
    payload: ProviderModelSelectionRequest,
    session: SessionDep,
    settings: SettingsDep,
    user: RequiredCurrentUserDep,
) -> ProviderModelSourceVerifyResponse:
    try:
        source, health_status = await _service(session, settings).verify_model_source(
            user_id=user.id,
            provider=payload.provider,
            model=payload.model,
        )
    except ProviderCredentialError as exc:
        _raise(exc)
    return ProviderModelSourceVerifyResponse(
        provider=source.provider,
        model=source.model,
        label=source.label,
        model_label=source.model_label,
        status=health_status,
    )


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
