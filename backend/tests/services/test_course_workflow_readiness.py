# Status: real

"""Readiness preflight tests for direct durable workflow starts."""

from __future__ import annotations

import pytest

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
