"""Integration coverage for durable API-risk request auditing."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

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

    monkeypatch.setattr(api_risk_middleware, "get_sessionmaker", lambda: sessions)
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
