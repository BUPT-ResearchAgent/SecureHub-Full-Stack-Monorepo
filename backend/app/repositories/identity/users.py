# Status: real

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from app.db.models.identity.user import User
from app.repositories.base import UUIDPKRepository


class UserRepository(UUIDPKRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list_active(self, *, limit: int = 100, offset: int = 0) -> Sequence[User]:
        stmt = (
            select(User)
            .where(User.is_active.is_(True))
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(
        self,
        *,
        user_id: UUID,
        email: str,
        display_name: str,
        hashed_password: str | None = None,
        is_active: bool = True,
    ) -> User:
        row = User(
            id=user_id,
            email=email,
            display_name=display_name,
            hashed_password=hashed_password,
            is_active=is_active,
        )
        self.session.add(row)
        await self.session.flush()
        return row
