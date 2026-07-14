# Status: real

"""Persistence operations for user-owned encrypted provider credentials."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.identity.provider_credential import ProviderCredential
from app.repositories.base import BaseRepository


class ProviderCredentialRepository(BaseRepository):
    """Owns ``provider_credentials`` and enforces user-scoped access."""

    async def list_for_user(self, user_id: UUID) -> list[ProviderCredential]:
        rows = await self.session.scalars(
            select(ProviderCredential)
            .where(ProviderCredential.user_id == user_id)
            .order_by(ProviderCredential.provider.asc(), ProviderCredential.created_at.desc())
        )
        return list(rows)

    async def get_owned(self, credential_id: UUID, user_id: UUID, *, lock: bool = False) -> ProviderCredential | None:
        statement = select(ProviderCredential).where(
            ProviderCredential.id == credential_id,
            ProviderCredential.user_id == user_id,
        )
        if lock:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def get_active(self, user_id: UUID, provider: str) -> ProviderCredential | None:
        return await self.session.scalar(
            select(ProviderCredential).where(
                ProviderCredential.user_id == user_id,
                ProviderCredential.provider == provider,
                ProviderCredential.is_active.is_(True),
            )
        )

    async def create(
        self,
        *,
        user_id: UUID,
        provider: str,
        name: str,
        encrypted_key: str,
        key_fingerprint: str,
    ) -> ProviderCredential:
        row = ProviderCredential(
            id=uuid4(),
            user_id=user_id,
            provider=provider,
            name=name,
            encrypted_key=encrypted_key,
            key_fingerprint=key_fingerprint,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def activate(self, credential: ProviderCredential) -> ProviderCredential:
        """Switch active key in a single transaction-owned unit of work."""
        # Lock this user's provider rows before clearing/setting the unique
        # active marker so concurrent switches serialize instead of racing.
        await self.session.execute(
            select(ProviderCredential.id)
            .where(
                ProviderCredential.user_id == credential.user_id,
                ProviderCredential.provider == credential.provider,
            )
            .with_for_update()
        )
        await self.session.execute(
            update(ProviderCredential)
            .where(
                ProviderCredential.user_id == credential.user_id,
                ProviderCredential.provider == credential.provider,
                ProviderCredential.id != credential.id,
                ProviderCredential.is_active.is_(True),
            )
            .values(is_active=False)
        )
        credential.is_active = True
        await self.session.flush()
        return credential

    async def deactivate(self, credential: ProviderCredential) -> ProviderCredential:
        credential.is_active = False
        await self.session.flush()
        return credential

    async def mark_verification(self, credential: ProviderCredential, *, status: str, verified_at: datetime | None) -> ProviderCredential:
        credential.verification_status = status
        credential.verified_at = verified_at
        await self.session.flush()
        return credential

    async def delete(self, credential: ProviderCredential) -> None:
        await self.session.delete(credential)
        await self.session.flush()
