# Status: real

import pytest

from app.db.seeds._constants import DEMO_USER_ID
from app.db.seeds.seed_demo_user import run as seed_demo_user
from app.repositories.identity.capabilities import UserCapabilityRepository


@pytest.mark.anyio
async def test_user_capabilities_seed_and_update_are_idempotent(sqlite_session) -> None:
    await seed_demo_user(sqlite_session)
    repo = UserCapabilityRepository(sqlite_session)

    initial = await repo.list_by_user(DEMO_USER_ID)
    updated = await repo.upsert_score(
        user_id=DEMO_USER_ID,
        dimension="web_security",
        score=0.72,
        confidence=0.81,
        evidence_count=4,
        metadata={"last_event": "assessment"},
    )
    again = await repo.upsert_score(
        user_id=DEMO_USER_ID,
        dimension="web_security",
        score=0.74,
        confidence=0.83,
        evidence_count=5,
    )
    final = await repo.list_by_user(DEMO_USER_ID)

    assert len(initial) >= 6
    assert updated.id == again.id
    assert again.score == 0.74
    assert again.confidence == 0.83
    assert again.evidence_count == 5
    assert len(final) == len(initial)
