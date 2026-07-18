"""Integration coverage for durable API-risk request auditing."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from time import monotonic

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.session as db_session
import app.services.security.api_risk_middleware as api_risk_middleware
from app.core.config import Settings
from app.db.base import Base
from app.db.models.security.account_security import ApiRequestAuditEvent
from app.db.session import get_session
from app.services.security.api_risk_middleware import ApiRiskMiddleware


@pytest.mark.anyio
async def test_api_risk_middleware_persists_redacted_audit_with_one_event_loop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the non-overridden middleware path against a durable test DB."""

    event_loop = asyncio.get_running_loop()
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'api-risk.sqlite'}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(JWT_SECRET="api-risk-integration-test-secret")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    middleware_app = FastAPI()
    middleware_app.add_middleware(ApiRiskMiddleware, enabled=True)

    @middleware_app.get("/api/v1/audit-probe")
    async def audit_probe() -> dict[str, bool]:
        return {"ok": True}

    monkeypatch.setattr(api_risk_middleware, "get_audit_sessionmaker", lambda: sessions)
    monkeypatch.setattr(api_risk_middleware, "get_settings", lambda: settings)

    try:
        assert get_session not in middleware_app.dependency_overrides
        transport = ASGITransport(app=middleware_app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(
                "/api/v1/audit-probe",
                headers={"X-Device-ID": "api-risk-test-device", "X-Request-ID": "api-risk-it-001"},
            )

        assert response.status_code == 200
        assert response.json() == {"ok": True}

        async with sessions() as session:
            audit = (await session.execute(select(ApiRequestAuditEvent))).scalar_one()

        assert audit.route_template == "/api/v1/audit-probe"
        assert audit.method == "GET"
        assert audit.outcome_status == 200
        assert audit.correlation_id == "api-risk-it-001"
        assert audit.ip_hash and audit.ip_hash != "127.0.0.1"
        assert audit.device_hash and audit.device_hash != "api-risk-test-device"
        assert asyncio.get_running_loop() is event_loop
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_api_risk_middleware_skips_independent_audit_for_overridden_http_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep isolated HTTP contracts from opening an unrelated audit session."""

    event_loop = asyncio.get_running_loop()
    middleware_app = FastAPI()
    middleware_app.add_middleware(ApiRiskMiddleware, enabled=True)

    @middleware_app.get("/api/v1/isolated-probe")
    async def isolated_probe() -> dict[str, bool]:
        return {"ok": True}

    async def isolated_get_session() -> AsyncIterator[None]:
        yield None

    sessionmaker_calls = 0

    def unexpected_sessionmaker() -> object:
        nonlocal sessionmaker_calls
        sessionmaker_calls += 1
        raise AssertionError("isolated HTTP request must not open an audit session")

    monkeypatch.setattr(api_risk_middleware, "get_audit_sessionmaker", unexpected_sessionmaker)
    had_previous_override = get_session in middleware_app.dependency_overrides
    previous_override = middleware_app.dependency_overrides.get(get_session)
    middleware_app.dependency_overrides[get_session] = isolated_get_session
    try:
        transport = ASGITransport(app=middleware_app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/isolated-probe")

        assert response.status_code == 200
        assert response.json() == {"ok": True}
        assert sessionmaker_calls == 0
        assert asyncio.get_running_loop() is event_loop
    finally:
        if had_previous_override:
            middleware_app.dependency_overrides[get_session] = previous_override
        else:
            middleware_app.dependency_overrides.pop(get_session, None)


@pytest.mark.anyio
async def test_api_risk_outcome_update_waits_for_handler_session_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A handler connection must be released before the post-response audit write."""

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'api-risk-pool.sqlite'}",
        pool_size=1,
        max_overflow=0,
        pool_timeout=0.1,
    )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(JWT_SECRET="api-risk-pool-test-secret")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    middleware_app = FastAPI()
    middleware_app.add_middleware(ApiRiskMiddleware, enabled=True)

    @middleware_app.get("/api/v1/session-probe")
    async def session_probe(
        session: AsyncSession = Depends(get_session),
    ) -> dict[str, int]:
        count = int(await session.scalar(select(func.count(ApiRequestAuditEvent.id))) or 0)
        return {"audit_count": count}

    monkeypatch.setattr(api_risk_middleware, "get_audit_sessionmaker", lambda: sessions)
    monkeypatch.setattr(db_session, "get_sessionmaker", lambda: sessions)
    monkeypatch.setattr(api_risk_middleware, "get_settings", lambda: settings)

    try:
        transport = ASGITransport(app=middleware_app)
        started = monotonic()
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            responses = await asyncio.gather(
                client.get("/api/v1/session-probe", headers={"X-Request-ID": "pool-a"}),
                client.get("/api/v1/session-probe", headers={"X-Request-ID": "pool-b"}),
            )
        elapsed = monotonic() - started

        assert [response.status_code for response in responses] == [200, 200]
        assert elapsed < 1.0
        async with sessions() as session:
            audits = list(
                (
                    await session.execute(
                        select(ApiRequestAuditEvent).order_by(ApiRequestAuditEvent.correlation_id)
                    )
                )
                .scalars()
                .all()
            )
        assert [audit.correlation_id for audit in audits] == ["pool-a", "pool-b"]
        assert [audit.outcome_status for audit in audits] == [200, 200]
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_api_risk_outcome_updates_use_bounded_parallelism(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active = 0
    peak = 0

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, _exc_type, _exc, _traceback) -> None:
            return None

        async def commit(self) -> None:
            return None

    class FakeSecurityService:
        def __init__(self, _session) -> None:
            pass

        async def complete_request_audit(self, *, audit_id, outcome_status) -> None:
            nonlocal active, peak
            assert audit_id is not None and outcome_status == 200
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.02)
            active -= 1

    settings = Settings(
        JWT_SECRET="api-risk-parallel-test-secret",
        API_RISK_AUDIT_MAX_CONCURRENCY=3,
    )
    monkeypatch.setattr(api_risk_middleware, "get_settings", lambda: settings)
    monkeypatch.setattr(api_risk_middleware, "get_audit_sessionmaker", lambda: FakeSession)
    monkeypatch.setattr(api_risk_middleware, "SecurityGovernanceService", FakeSecurityService)
    middleware = ApiRiskMiddleware(FastAPI())

    from uuid import uuid4

    await asyncio.gather(
        *(middleware._complete_audit(uuid4(), 200) for _ in range(8))
    )

    assert peak == 3
