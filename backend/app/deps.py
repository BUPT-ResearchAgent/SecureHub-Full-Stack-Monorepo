# Status: real

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.seeds._constants import DEMO_USER_ID
from app.db.session import get_session

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def current_user_id() -> UUID:
    """Demo-mode "current user" — auth has not yet shipped (rule §10 boundaries),
    so every ``/me`` endpoint resolves to the seeded demo student. Returns the
    same UUID ``seed_demo_user`` and ``20260611_0960_seed_agents_skills`` use.
    """
    return DEMO_USER_ID


CurrentUserDep = Annotated[UUID, Depends(current_user_id)]
