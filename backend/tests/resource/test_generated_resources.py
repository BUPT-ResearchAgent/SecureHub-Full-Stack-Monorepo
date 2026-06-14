# Status: real

import pytest

from app.db.seeds._constants import COURSE_WEBSEC_ID, DEMO_USER_ID, node_id, stable_id
from app.db.seeds.seed_course_websec import run as seed_course_websec
from app.db.seeds.seed_demo_user import run as seed_demo_user
from app.repositories.resource.generated_resources import GeneratedResourceRepository


@pytest.mark.anyio
async def test_generated_resources_store_evidence_and_object_key(sqlite_session) -> None:
    await seed_demo_user(sqlite_session)
    await seed_course_websec(sqlite_session)

    repo = GeneratedResourceRepository(sqlite_session)
    resource = await repo.create(
        resource_id=stable_id("generated:course_doc:sql-injection:test"),
        user_id=DEMO_USER_ID,
        course_id=COURSE_WEBSEC_ID,
        kp_id=node_id("sql-injection"),
        resource_type="course_doc",
        title="SQL 注入基础讲解",
        content={"outline": ["原理", "风险", "防御"]},
        object_key="generated/course_websec/sql-injection-doc.md",
        evidence_chunk_ids=[str(stable_id("chunk:websec:sql-injection:000"))],
        quality_score=0.91,
        metadata={"source": "test"},
    )
    await sqlite_session.commit()

    rows = await repo.list_by_user_course(
        user_id=DEMO_USER_ID,
        course_id=COURSE_WEBSEC_ID,
        resource_type="course_doc",
    )

    assert rows == [resource]
    assert rows[0].object_key
    assert rows[0].evidence_chunk_ids
    assert rows[0].status == "ready"
