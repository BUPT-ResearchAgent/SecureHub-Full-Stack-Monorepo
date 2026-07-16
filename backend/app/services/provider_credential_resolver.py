# Status: real

"""Per-call credential resolver for the canonical RuntimeEngine path."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.llm.provider import BaseLLMProvider, get_llm_provider
from app.repositories.identity.provider_credentials import ProviderCredentialRepository
from app.services.provider_credentials import ProviderCredentialError, credential_cipher


class ProviderCredentialResolver:
    """Resolve a root-frozen credential ID without changing global settings."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession] | None = None) -> None:
        self.sessionmaker = sessionmaker or get_sessionmaker()

    async def resolve(
        self,
        *,
        provider: str,
        user_id: UUID | str | None,
        credential_id: UUID | str | None,
        model: str | None = None,
    ) -> BaseLLMProvider:
        # No user credential was selected at root creation: retain the server
        # environment-variable fallback exactly as before.
        if credential_id is None:
            return get_llm_provider(provider, model=model)
        if user_id is None:
            raise ProviderCredentialError("CREDENTIAL_NOT_FOUND", "provider credential not found", status_code=503)
        try:
            parsed_user_id = UUID(str(user_id))
            parsed_credential_id = UUID(str(credential_id))
        except ValueError as exc:
            raise ProviderCredentialError("CREDENTIAL_NOT_FOUND", "provider credential not found", status_code=503) from exc
        async with self.sessionmaker() as session:
            row = await ProviderCredentialRepository(session).get_owned(parsed_credential_id, parsed_user_id)
            if row is None or row.provider != provider:
                # Do not silently route a root that selected a user key to a
                # server/global key if the frozen credential was deleted.
                raise ProviderCredentialError("CREDENTIAL_NOT_FOUND", "provider credential is unavailable", status_code=503)
            secret = credential_cipher(get_settings()).decrypt(row.encrypted_key)
        return get_llm_provider(provider, api_key=secret, model=model)
