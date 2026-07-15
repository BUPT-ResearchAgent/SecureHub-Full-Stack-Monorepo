# Status: real

"""Whole-site redacted request-audit and risk-disposition middleware.

This middleware never persists Authorization, Cookie, password, token, raw
payload, complete IP address, or raw device value.  It only constructs the
``RedactedRequestObservation`` boundary accepted by the T5 service.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Awaitable, Callable
from uuid import UUID

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.auth.security import AuthTokenError, decode_access_token
from app.core.config import get_settings
from app.db.session import get_session, get_sessionmaker
from app.services.security.security_service import (
    RedactedRequestObservation,
    SecurityGovernanceService,
    opaque_identifier_hash,
    request_size_bucket,
)

_UUID_SEGMENT = re.compile(r"(?<=/)[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}(?=/|$)")
_NUMERIC_SEGMENT = re.compile(r"(?<=/)\d{4,}(?=/|$)")
_SAFE_CORRELATION = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class ApiRiskMiddleware(BaseHTTPMiddleware):
    """Apply T5 API-risk controls before every versioned API handler."""

    def __init__(self, app: ASGIApp, *, enabled: bool = True) -> None:
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not self.enabled or not request.url.path.startswith("/api/v1/"):
            return await call_next(request)
        # Dependency-overridden isolated HTTP tests own their session lifecycle.
        # They may intentionally create only a subset of tables, so opening an
        # unrelated production session here would be both unsafe and misleading.
        if get_session in request.app.dependency_overrides:
            return await call_next(request)

        try:
            observation = self._observation(request)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": {
                        "code": "REQUEST_AUDIT_REDACTION_FAILED",
                        "message": "请求审计元数据无法安全脱敏。",
                    }
                },
            )

        try:
            async with get_sessionmaker()() as session:
                service = SecurityGovernanceService(session)
                decision = await service.observe_redacted_request(observation)
                await session.commit()
        except SQLAlchemyError:
            # Fail closed when persisted risk controls are configured but the
            # security schema/store is unavailable.  No request contents are
            # included in this response or any fallback log.
            return JSONResponse(
                status_code=503,
                content={
                    "detail": {
                        "code": "REQUEST_AUDIT_REDACTION_FAILED",
                        "message": "安全审计存储暂不可用，请稍后重试。",
                    }
                },
            )

        if decision.decision in {"throttle", "block"}:
            status_code = 429 if decision.decision == "throttle" else 403
            await self._complete_audit(decision.audit_id, status_code)
            return JSONResponse(
                status_code=status_code,
                headers={"Retry-After": "60"} if decision.decision == "throttle" else None,
                content={
                    "detail": {
                        "code": "API_RISK_RATE_LIMITED"
                        if decision.decision == "throttle"
                        else "API_RISK_EVENT_BLOCKED",
                        "message": "请求触发了可解释的 API 风险处置。",
                        "risk_event_id": str(decision.risk_event_id) if decision.risk_event_id else None,
                    }
                },
            )

        response = await call_next(request)
        await self._complete_audit(decision.audit_id, response.status_code)
        return response

    @staticmethod
    def _canonical_route(path: str) -> str:
        route = _UUID_SEGMENT.sub("{id}", path)
        return _NUMERIC_SEGMENT.sub("{id}", route)

    def _observation(self, request: Request) -> RedactedRequestObservation:
        settings = get_settings()
        auth_header = request.headers.get("authorization", "")
        actor_user_id: UUID | None = None
        if auth_header.lower().startswith("bearer "):
            # The credential is used transiently only to identify the actor;
            # it is never added to an observation, exception, log, or table.
            try:
                actor_user_id = decode_access_token(auth_header[7:].strip(), settings)
            except AuthTokenError:
                actor_user_id = None
        raw_device = request.headers.get("x-device-id")
        raw_ip = request.client.host if request.client else None
        correlation = request.headers.get("x-request-id")
        if correlation and not _SAFE_CORRELATION.fullmatch(correlation):
            correlation = None
        try:
            content_length = int(request.headers.get("content-length", "0"))
        except ValueError as exc:
            raise ValueError("invalid content length") from exc
        if content_length < 0:
            raise ValueError("negative content length")
        now = datetime.now(UTC)
        return RedactedRequestObservation(
            route_template=self._canonical_route(request.url.path),
            method=request.method.upper(),
            actor_user_id=actor_user_id,
            ip_hash=opaque_identifier_hash(raw_ip, secret=settings.JWT_SECRET),
            device_hash=opaque_identifier_hash(raw_device, secret=settings.JWT_SECRET),
            rate_bucket=now.strftime("%Y%m%d%H%M"),
            request_size_bucket=request_size_bucket(content_length),
            correlation_id=correlation,
        )

    @staticmethod
    async def _complete_audit(audit_id: UUID, outcome_status: int) -> None:
        try:
            async with get_sessionmaker()() as session:
                await SecurityGovernanceService(session).complete_request_audit(
                    audit_id=audit_id, outcome_status=outcome_status
                )
                await session.commit()
        except SQLAlchemyError:
            # The decision row is already durable; status refresh failure must
            # not expose request data or turn a completed response into success.
            return
