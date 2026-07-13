# Status: real

from uuid import uuid4

import pytest

from app.db.seeds._constants import (
    COURSE_WEBSEC_ID,
    DEMO_USER_ID,
    LEGACY_SMOKE_COURSE_WEBSEC_ID,
    node_id,
)
from app.repositories.knowledge.courses import CourseRepository
from app.db.seeds.seed_course_websec import run as seed_course_websec
from app.db.seeds.seed_demo_user import run as seed_demo_user
from app.repositories.identity.capabilities import UserCapabilityRepository
from app.repositories.resource.generated_resources import GeneratedResourceRepository
from app.services.course_catalog_service import CourseCatalogService


@pytest.mark.anyio
async def test_course_catalog_graph_coverage_and_personalised_path(sqlite_session) -> None:
    await seed_demo_user(sqlite_session)
    await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    service = CourseCatalogService(sqlite_session)
    catalog = await service.list_catalog(user_id=DEMO_USER_ID)
    detail = await service.get_detail(course_id=COURSE_WEBSEC_ID, user_id=DEMO_USER_ID)
    graph = await service.get_graph(course_id=COURSE_WEBSEC_ID, user_id=DEMO_USER_ID)
    foundation_path = await service.get_path(course_id=COURSE_WEBSEC_ID, user_id=DEMO_USER_ID)

    assert [item.code for item in catalog] == ["WEBSEC-101"]
    assert detail.chapter_count == 5
    assert detail.knowledge_point_count == 17
    assert detail.core_coverage_percent >= 80
    assert all(chapter.coverage_percent >= 80 for chapter in detail.chapters)
    assert {"owasp", "portswigger", "mineru"} <= set(detail.source_platforms)
    assert len(graph.nodes) == 17
    assert len(graph.edges) == 39
    assert foundation_path.strategy == "foundation_first"
    assert foundation_path.nodes[0].title == "HTTP / HTTPS 协议基础"

    capabilities = UserCapabilityRepository(sqlite_session)
    await capabilities.upsert_score(
        user_id=DEMO_USER_ID,
        dimension="web_security",
        score=0.9,
        confidence=0.9,
        evidence_count=8,
    )
    accelerated_path = await service.get_path(course_id=COURSE_WEBSEC_ID, user_id=DEMO_USER_ID)

    assert accelerated_path.strategy == "accelerated_prerequisite_route"
    assert accelerated_path.nodes[0].knowledge_point_id == foundation_path.nodes[0].knowledge_point_id
    assert accelerated_path.nodes[1].knowledge_point_id != foundation_path.nodes[1].knowledge_point_id
    assert "user_capabilities.web_security=0.90" in accelerated_path.explanation


@pytest.mark.anyio
async def test_course_progress_is_idempotent_and_uses_capability_metadata(sqlite_session) -> None:
    await seed_demo_user(sqlite_session)
    await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    service = CourseCatalogService(sqlite_session)
    http_id = node_id("http-basics")
    first = await service.record_completion(
        course_id=COURSE_WEBSEC_ID,
        user_id=DEMO_USER_ID,
        knowledge_point_id=http_id,
        activity_type="resource",
        activity_id="resource-root-1",
    )
    duplicate = await service.record_completion(
        course_id=COURSE_WEBSEC_ID,
        user_id=DEMO_USER_ID,
        knowledge_point_id=http_id,
        activity_type="resource",
        activity_id="resource-root-1",
    )
    await sqlite_session.commit()

    persisted = await service.get_progress(course_id=COURSE_WEBSEC_ID, user_id=DEMO_USER_ID)
    capability = await UserCapabilityRepository(sqlite_session).get(DEMO_USER_ID, "web_security")
    payload = capability.metadata_["course_progress"]["WEBSEC-101"]

    assert first.progress_percent == duplicate.progress_percent == persisted.progress_percent
    assert persisted.completed_knowledge_point_ids == [http_id]
    assert persisted.next_knowledge_point_id is not None
    assert len(payload["activities"]) == 1
    assert payload["activities"][0]["activity_id"] == "resource-root-1"


@pytest.mark.anyio
async def test_catalog_resource_count_comes_from_generated_resources(sqlite_session) -> None:
    await seed_demo_user(sqlite_session)
    await seed_course_websec(sqlite_session)
    await CourseRepository(sqlite_session).create(
        course_id=LEGACY_SMOKE_COURSE_WEBSEC_ID,
        code="course_websec_intro",
        title="Historical smoke course",
    )
    resource_repository = GeneratedResourceRepository(sqlite_session)
    await resource_repository.create(
        resource_id=uuid4(),
        user_id=DEMO_USER_ID,
        course_id=LEGACY_SMOKE_COURSE_WEBSEC_ID,
        kp_id=node_id("sql-injection"),
        resource_type="doc",
        title="SQL injection evidence-backed guide",
        content={"body": "Generated from a durable resource workflow."},
        evidence_chunk_ids=[],
        quality_score=0.9,
        status="active",
    )
    await sqlite_session.commit()

    detail = await CourseCatalogService(sqlite_session).get_detail(
        course_id=COURSE_WEBSEC_ID,
        user_id=DEMO_USER_ID,
    )
    sql_injection = next(point for point in detail.knowledge_points if point.slug == "sql-injection")

    assert detail.resource_count == 1
    assert sql_injection.resource_count == 1
