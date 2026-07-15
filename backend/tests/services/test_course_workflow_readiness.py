# Status: real

"""Readiness preflight tests for direct durable workflow starts."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.db.models.knowledge.course import Course
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.db.seeds._constants import COURSE_CRYPTO_ID, COURSE_WEBSEC_ID
from app.services.workflow_application_service import WorkflowApplicationError, WorkflowApplicationService


@pytest.mark.anyio
async def test_preview_and_unknown_course_are_rejected_before_root_creation() -> None:
    preview_input = {"course_id": str(COURSE_CRYPTO_ID), "domain": "course_websec"}
    with pytest.raises(WorkflowApplicationError) as preview_error:
        await WorkflowApplicationService._preflight_course_content(
            workflow_name="resource_generate_v1",
            validated_input=preview_input,
        )
    assert preview_error.value.code == "COURSE_CONTENT_NOT_READY"
    assert preview_error.value.status_code == 409
    # No canonicalisation or other write-side preparation occurs on rejection.
    assert preview_input == {"course_id": str(COURSE_CRYPTO_ID), "domain": "course_websec"}

    unknown_input = {"course_id": "00000000-0000-0000-0000-000000009999"}
    with pytest.raises(WorkflowApplicationError) as unknown_error:
        await WorkflowApplicationService._preflight_course_content(
            workflow_name="course_plan_v1",
            validated_input=unknown_input,
        )
    assert unknown_error.value.code == "COURSE_NOT_FOUND"
    assert unknown_error.value.status_code == 404


@pytest.mark.anyio
async def test_ready_course_is_canonicalised_only_after_readiness_passes() -> None:
    payload = {"course_id": "web-security-foundation", "domain": "untrusted"}
    await WorkflowApplicationService._preflight_course_content(
        workflow_name="tutor_routing_v3",
        validated_input=payload,
    )
    assert payload == {"course_id": str(COURSE_WEBSEC_ID), "domain": "course_websec"}


@pytest.mark.anyio
async def test_resource_topic_is_rewritten_from_server_owned_knowledge_node(sqlite_session) -> None:
    node_id = uuid4()
    sqlite_session.add(
        Course(
            id=COURSE_WEBSEC_ID,
            code="WEBSEC-READINESS-TEST",
            title="Web security readiness test",
            domain="course_websec",
        )
    )
    sqlite_session.add(
        KnowledgeNode(
            id=node_id,
            course_id=COURSE_WEBSEC_ID,
            domain="course_websec",
            name="SQL 注入原理",
            description="SQL injection scope",
            node_type="concept",
            metadata_={},
        )
    )
    await sqlite_session.flush()

    payload = {
        "course_id": str(COURSE_WEBSEC_ID),
        "domain": "course_websec",
        "kp_id": str(node_id),
        "resource_type": "ppt",
        "query": "Regenerate ppt: ppt: Generate ppt resource",
        "options": {"retry_source_resource_id": str(uuid4())},
    }
    await WorkflowApplicationService._canonicalise_resource_topic(
        sqlite_session,
        workflow_name="resource_generate_v1",
        validated_input=payload,
    )

    assert payload["query"].startswith('Regenerate ppt course resource for knowledge point "SQL 注入原理"')
    assert "Use only evidence relevant to this knowledge point" in payload["query"]


@pytest.mark.anyio
async def test_resource_topic_rejects_cross_course_node_and_keeps_kp_less_compatibility(sqlite_session) -> None:
    cross_course_node_id = uuid4()
    sqlite_session.add(
        KnowledgeNode(
            id=cross_course_node_id,
            course_id=uuid4(),
            domain="course_websec",
            name="Cross-course node",
            description=None,
            node_type="concept",
            metadata_={},
        )
    )
    await sqlite_session.flush()
    cross_course = {
        "course_id": str(COURSE_WEBSEC_ID),
        "domain": "course_websec",
        "kp_id": str(cross_course_node_id),
        "resource_type": "ppt",
        "query": "untrusted",
        "options": {},
    }

    with pytest.raises(WorkflowApplicationError) as error:
        await WorkflowApplicationService._canonicalise_resource_topic(
            sqlite_session,
            workflow_name="resource_generate_v1",
            validated_input=cross_course,
        )
    assert error.value.code == "KNOWLEDGE_POINT_NOT_FOUND"
    assert error.value.status_code == 404

    no_kp = {
        "course_id": str(COURSE_WEBSEC_ID),
        "domain": "course_websec",
        "kp_id": None,
        "resource_type": "ppt",
        "query": "Keep generic compatibility",
        "options": {},
    }
    await WorkflowApplicationService._canonicalise_resource_topic(
        sqlite_session,
        workflow_name="resource_generate_v1",
        validated_input=no_kp,
    )
    assert no_kp["query"] == "Keep generic compatibility"
