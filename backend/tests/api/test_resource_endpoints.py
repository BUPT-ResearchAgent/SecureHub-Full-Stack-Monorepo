# Status: real

"""Focused authorization and lineage checks for generated-resource reads."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.api.v1 import api
from app.api.v1.endpoints import resources
from app.schemas.agent_control import WorkflowRunStartResponse
from app.schemas.resource import GeneratedResourceRetryRequest


OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_ID = UUID("00000000-0000-0000-0000-000000000002")
COURSE_ID = UUID("00000000-0000-0000-0000-000000000101")


def _row(*, user_id: UUID | None = OWNER_ID) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        resource_type="doc",
        title="SQL injection course note",
        user_id=user_id,
        course_id=COURSE_ID,
        kp_id=uuid4(),
        agent_run_id=uuid4(),
        workflow_run_id=uuid4(),
        step_attempt_id=uuid4(),
        content={"schema_version": "v1", "output": {"markdown": "# Safe SQL"}},
        object_key="resources/doc.json",
        evidence_chunk_ids=[],
        quality_score=0.91,
        status="active",
        metadata_={},
        created_at=now,
        updated_at=now,
    )


class _Repo:
    row = _row()
    list_calls: list[dict[str, object]] = []

    def __init__(self, _session: object) -> None:
        pass

    async def get_by_id(self, _resource_id: UUID) -> SimpleNamespace | None:
        return self.row

    async def list_by_user_course(self, **kwargs: object) -> list[SimpleNamespace]:
        self.list_calls.append(kwargs)
        return [self.row]


@pytest.mark.anyio
async def test_resource_reads_are_scoped_to_current_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(resources, "GeneratedResourceRepository", _Repo)
    _Repo.row = _row(user_id=OWNER_ID)
    _Repo.list_calls.clear()

    listed = await resources.list_resources(
        session=object(),
        current_user_id=OWNER_ID,
        course_id=COURSE_ID,
        resource_type=None,
        limit=50,
        offset=0,
    )
    assert listed.total == 1
    assert _Repo.list_calls[-1]["user_id"] == OWNER_ID

    resource = await resources.get_resource(_Repo.row.id, session=object(), current_user_id=OWNER_ID)
    assert resource.id == _Repo.row.id

    with pytest.raises(HTTPException) as error:
        await resources.get_resource(_Repo.row.id, session=object(), current_user_id=OTHER_ID)
    assert error.value.status_code == 404


@pytest.mark.anyio
async def test_shared_course_resource_read_requires_active_enrollment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(resources, "GeneratedResourceRepository", _Repo)
    _Repo.row = _row(user_id=None)

    async def enrolled(*_args: object, **_kwargs: object) -> bool:
        return True

    monkeypatch.setattr(resources, "_has_active_course_enrollment", enrolled)
    shared = await resources.get_resource(_Repo.row.id, session=object(), current_user_id=OTHER_ID)
    assert shared.id == _Repo.row.id

    async def not_enrolled(*_args: object, **_kwargs: object) -> bool:
        return False

    monkeypatch.setattr(resources, "_has_active_course_enrollment", not_enrolled)
    with pytest.raises(HTTPException) as error:
        await resources.get_resource(_Repo.row.id, session=object(), current_user_id=OTHER_ID)
    assert error.value.status_code == 404


@pytest.mark.anyio
async def test_resource_retry_creates_a_new_owned_root_with_parent_lineage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(resources, "GeneratedResourceRepository", _Repo)
    _Repo.row = _row(user_id=OWNER_ID)
    captured: dict[str, object] = {}

    async def start_product(*args: object, **kwargs: object) -> WorkflowRunStartResponse:
        captured.update(kwargs)
        run_id = uuid4()
        return WorkflowRunStartResponse(
            run_id=run_id,
            workflow="resource_generate_v1",
            status="queued",
            events_url=f"/api/v1/workflow-runs/{run_id}/events",
            cancel_url=f"/api/v1/workflow-runs/{run_id}/cancel",
            mode="real",
        )

    monkeypatch.setattr(resources, "start_product_workflow", start_product)
    monkeypatch.setattr(resources, "_service", lambda _request: object())
    response = await resources.retry_resource(
        _Repo.row.id,
        GeneratedResourceRetryRequest(),
        request=object(),  # type: ignore[arg-type]
        session=object(),
        current_user_id=OWNER_ID,
        idempotency_key="resource-retry",
    )

    assert response.status_code == 202
    assert captured["workflow"] == "resource_generate_v1"
    assert captured["course_id"] == COURSE_ID
    assert captured["idempotency_key"] == "resource-retry"
    payload = captured["input_payload"]
    assert isinstance(payload, dict)
    assert payload["resource_type"] == "doc"
    assert payload["options"]["parent_resource_id"] == str(_Repo.row.id)
    assert payload["options"]["retry_source_workflow_run_id"] == str(_Repo.row.workflow_run_id)


def test_resources_router_is_registered_once() -> None:
    paths = {route.path for route in api.api_router.routes}
    assert "/resources" in paths
    assert "/resources/{resource_id}" in paths
    assert "/resources/{resource_id}/retry" in paths
