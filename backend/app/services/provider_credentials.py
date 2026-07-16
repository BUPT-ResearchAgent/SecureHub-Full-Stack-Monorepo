# Status: real

"""Authenticated encryption and user-scoped provider credential lifecycle."""

from __future__ import annotations

import base64
import binascii
import hashlib
import os
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.llm.model_catalog import (
    ModelSourceError,
    ProviderModelSource,
    default_model_source,
    model_sources as catalog_model_sources,
    resolve_model_source,
)
from app.llm.provider import get_llm_provider
from app.repositories.identity.provider_credentials import ProviderCredentialRepository


ProviderName = Literal["deepseek", "xfyun"]
_SUPPORTED_PROVIDERS = frozenset({"deepseek", "xfyun"})
_CIPHER_VERSION = b"pc1"


class ProviderCredentialError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class ProviderCredentialCipher:
    """AES-256-GCM wrapper with a server-only master key.

    The encoded value contains a version, random nonce, and ciphertext/tag. No
    plaintext ever reaches persistence or response serialization.
    """

    def __init__(self, master_key: str) -> None:
        try:
            key = base64.urlsafe_b64decode(master_key.encode("ascii"))
        except Exception as exc:
            raise ProviderCredentialError(
                "CREDENTIAL_ENCRYPTION_UNAVAILABLE",
                "provider credential encryption is not configured",
                status_code=503,
            ) from exc
        if len(key) != 32:
            raise ProviderCredentialError(
                "CREDENTIAL_ENCRYPTION_UNAVAILABLE",
                "provider credential encryption is not configured",
                status_code=503,
            )
        self._aead = AESGCM(key)

    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(12)
        ciphertext = self._aead.encrypt(nonce, plaintext.encode("utf-8"), _CIPHER_VERSION)
        return base64.urlsafe_b64encode(_CIPHER_VERSION + nonce + ciphertext).decode("ascii")

    def decrypt(self, encoded: str) -> str:
        try:
            raw = base64.urlsafe_b64decode(encoded.encode("ascii"))
            version, nonce, ciphertext = raw[:3], raw[3:15], raw[15:]
            if version != _CIPHER_VERSION or len(nonce) != 12 or not ciphertext:
                raise ValueError("invalid credential envelope")
            return self._aead.decrypt(nonce, ciphertext, version).decode("utf-8")
        except (InvalidTag, UnicodeDecodeError, ValueError, TypeError, binascii.Error) as exc:
            raise ProviderCredentialError(
                "CREDENTIAL_DECRYPT_FAILED",
                "stored provider credential is unavailable",
                status_code=503,
            ) from exc


def credential_fingerprint(api_key: str) -> str:
    """Return a non-reversible UI-safe fingerprint, never a key substring."""
    return f"sha256:{hashlib.sha256(api_key.encode('utf-8')).hexdigest()[:12]}"


def credential_cipher(settings: Settings) -> ProviderCredentialCipher:
    return ProviderCredentialCipher(settings.PROVIDER_CREDENTIAL_MASTER_KEY)


class ProviderCredentialService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.repository = ProviderCredentialRepository(session)

    async def list(self, user_id: UUID):
        return await self.repository.list_for_user(user_id)

    async def list_model_sources(
        self,
        user_id: UUID,
    ) -> tuple[list[tuple[ProviderModelSource, bool, bool]], ProviderModelSource]:
        """Return server-owned sources plus selection/key state safe for the UI."""
        selected = await self.current_model_selection(user_id)
        credentials = await self.repository.list_for_user(user_id)
        active_providers = {row.provider for row in credentials if row.is_active}
        sources = [
            (
                source,
                source.provider == selected.provider and source.model == selected.model,
                source.provider in active_providers,
            )
            for source in catalog_model_sources(self.settings)
        ]
        return sources, selected

    async def current_model_selection(self, user_id: UUID) -> ProviderModelSource:
        selection = await self.repository.get_model_selection(user_id)
        if selection is None:
            return default_model_source(self.settings)
        try:
            return resolve_model_source(
                self.settings,
                provider=selection.provider,
                model=selection.model,
            )
        except ModelSourceError as exc:
            raise ProviderCredentialError(
                "MODEL_SOURCE_UNAVAILABLE",
                "selected model source is no longer available",
                status_code=409,
            ) from exc

    async def select_model_source(
        self,
        *,
        user_id: UUID,
        provider: str,
        model: str,
    ) -> ProviderModelSource:
        source = self._model_source(provider=provider, model=model)
        await self.repository.set_model_selection(
            user_id=user_id,
            provider=source.provider,
            model=source.model,
        )
        await self.session.commit()
        return source

    async def verify_model_source(
        self,
        *,
        user_id: UUID,
        provider: str,
        model: str,
    ) -> tuple[ProviderModelSource, str]:
        """Probe the effective user-or-server credential without exposing it."""
        source = self._model_source(provider=provider, model=model)
        credential = await self.repository.get_active(user_id, source.provider)
        api_key = None
        if credential is not None:
            api_key = credential_cipher(self.settings).decrypt(credential.encrypted_key)
        try:
            health = await get_llm_provider(
                source.provider,
                api_key=api_key,
                model=source.model,
            ).health_check()
        except Exception:
            return source, "error"
        return source, health.status

    async def create(
        self,
        *,
        user_id: UUID,
        provider: str,
        name: str,
        api_key: str,
        activate: bool,
    ):
        normalized_provider = self._provider(provider)
        normalized_name = name.strip()
        # API keys are opaque credentials. Only use a stripped copy to reject
        # all-whitespace input; preserve the user-supplied bytes otherwise.
        normalized_key = api_key
        if not normalized_name:
            raise ProviderCredentialError("CREDENTIAL_NAME_INVALID", "credential name is required", status_code=422)
        if not normalized_key.strip():
            raise ProviderCredentialError("CREDENTIAL_KEY_INVALID", "API key is required", status_code=422)
        if len(normalized_key) > 4096:
            raise ProviderCredentialError("CREDENTIAL_KEY_INVALID", "API key is too long", status_code=422)
        row = await self.repository.create(
            user_id=user_id,
            provider=normalized_provider,
            name=normalized_name,
            encrypted_key=credential_cipher(self.settings).encrypt(normalized_key),
            key_fingerprint=credential_fingerprint(normalized_key),
        )
        if activate:
            await self.repository.activate(row)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ProviderCredentialError("CREDENTIAL_NAME_EXISTS", "credential name already exists", status_code=409) from exc
        await self.session.refresh(row)
        return row

    async def activate(self, *, user_id: UUID, credential_id: UUID):
        row = await self._owned_locked(user_id, credential_id)
        await self.repository.activate(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def deactivate(self, *, user_id: UUID, credential_id: UUID):
        row = await self._owned_locked(user_id, credential_id)
        await self.repository.deactivate(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def delete(self, *, user_id: UUID, credential_id: UUID) -> None:
        row = await self._owned_locked(user_id, credential_id)
        await self.repository.delete(row)
        await self.session.commit()

    async def verify(self, *, user_id: UUID, credential_id: UUID):
        row = await self._owned_locked(user_id, credential_id)
        secret = credential_cipher(self.settings).decrypt(row.encrypted_key)
        status = "error"
        verified_at = None
        try:
            source = self._model_source(provider=row.provider, model=None)
            health = await get_llm_provider(
                row.provider,
                api_key=secret,
                model=source.model,
            ).health_check()
            if health.status == "available":
                status = "verified"
                verified_at = datetime.now(timezone.utc)
            elif health.status == "error":
                status = "invalid"
        except Exception:
            # Provider-specific diagnostics might include request details. The
            # durable status is sufficient for users and safe to return.
            status = "error"
        await self.repository.mark_verification(row, status=status, verified_at=verified_at)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def _owned_locked(self, user_id: UUID, credential_id: UUID):
        row = await self.repository.get_owned(credential_id, user_id, lock=True)
        if row is None:
            raise ProviderCredentialError("CREDENTIAL_NOT_FOUND", "provider credential not found", status_code=404)
        return row

    @staticmethod
    def _provider(value: str) -> ProviderName:
        provider = value.strip().lower()
        if provider not in _SUPPORTED_PROVIDERS:
            raise ProviderCredentialError("PROVIDER_UNSUPPORTED", "unsupported provider", status_code=422)
        return provider  # type: ignore[return-value]

    def _model_source(self, *, provider: str, model: str | None) -> ProviderModelSource:
        try:
            return resolve_model_source(self.settings, provider=provider, model=model)
        except ModelSourceError as exc:
            raise ProviderCredentialError(
                "MODEL_SOURCE_UNSUPPORTED",
                "unsupported provider or model",
                status_code=422,
            ) from exc
