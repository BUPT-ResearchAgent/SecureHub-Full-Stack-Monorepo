# Status: real

"""Whole-site redacted request-audit and risk-disposition middleware.

This middleware never persists Authorization, Cookie, password, token, raw
payload, complete IP address, or raw device value.  It only constructs the
``RedactedRequestObservation`` boundary accepted by the T5 service.
"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from time import monotonic
from uuid import UUID

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.auth.security import AuthTokenError, decode_access_token
from app.core.config import get_settings
from app.db.session import get_audit_sessionmaker, get_session
from app.db.models.security.account_security import ApiRiskRule
from app.services.security.security_service import (
    RedactedRequestObservation,
    SecurityGovernanceService,
    opaque_identifier_hash,
    request_size_bucket,
)

_UUID_SEGMENT = re.compile(r"(?<=/)[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}(?=/|$)")
_NUMERIC_SEGMENT = re.compile(r"(?<=/)\d{4,}(?=/|$)")
_SAFE_CORRELATION = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class ApiRiskMiddleware:
    """Apply T5 API-risk controls before every versioned API handler.

    A pure ASGI boundary is required here.  ``BaseHTTPMiddleware.call_next``
    can return while a FastAPI yield dependency still owns its DB connection;
    opening the outcome-update session at that point can exhaust the shared
    pool under concurrent DB-backed requests.  Waiting for the downstream ASGI
    app to return guarantees dependency cleanup before the second audit write.
    """

    def __init__(self, app: ASGIApp, *, enabled: bool = True) -> None:
        self.app = app
        self.enabled = enabled
        settings = get_settings()
        # Admission and outcome writes use their own bounded pool.  Both sides
        # are capped so a burst remains finite without serialising every
        # keep-alive connection behind a single post-response transaction.
        self._admission_semaphore = asyncio.Semaphore(
            settings.API_RISK_AUDIT_MAX_CONCURRENCY
        )
        self._completion_semaphore = asyncio.Semaphore(
            settings.API_RISK_AUDIT_MAX_CONCURRENCY
        )
        self._rule_cache_lock = asyncio.Lock()
        self._rule_cache: tuple[ApiRiskRule, ...] = ()
        self._rule_cache_expires_at = 0.0

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope, receive=receive)
        if not self.enabled or not request.url.path.startswith("/api/v1/"):
            await self.app(scope, receive, send)
            return
        # Dependency-overridden isolated HTTP tests own their session lifecycle.
        # They may intentionally create only a subset of tables, so opening an
        # unrelated production session here would be both unsafe and misleading.
        if get_session in request.app.dependency_overrides:
            await self.app(scope, receive, send)
            return

        try:
            observation = self._observation(request)
        except ValueError:
            response = JSONResponse(
                status_code=400,
                content={
                    "detail": {
                        "code": "REQUEST_AUDIT_REDACTION_FAILED",
                        "message": "请求审计元数据无法安全脱敏。",
                    }
                },
            )
            await response(scope, receive, send)
            return

        try:
            active_rules = await self._active_rules()
            # Keep the durable admission audit ahead of the handler while
            # reserving the domain pool for requests that already passed it.
            async with self._admission_semaphore:
                async with get_audit_sessionmaker()() as session:
                    service = SecurityGovernanceService(session)
                    decision = await service.observe_redacted_request(
                        observation,
                        active_rules=active_rules,
                    )
                    await session.commit()
        except SQLAlchemyError:
            # Fail closed when persisted risk controls are configured but the
            # security schema/store is unavailable.  No request contents are
            # included in this response or any fallback log.
            response = JSONResponse(
                status_code=503,
                content={
                    "detail": {
                        "code": "REQUEST_AUDIT_REDACTION_FAILED",
                        "message": "安全审计存储暂不可用，请稍后重试。",
                    }
                },
            )
            await response(scope, receive, send)
            return

        if decision.decision in {"throttle", "block"}:
            status_code = 429 if decision.decision == "throttle" else 403
            await self._complete_audit(decision.audit_id, status_code)
            response = JSONResponse(
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
            await response(scope, receive, send)
            return

        outcome_status = 0

        async def send_with_outcome(message: Message) -> None:
            nonlocal outcome_status
            if message["type"] == "http.response.start":
                outcome_status = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_with_outcome)
        finally:
            # The downstream ASGI call has returned, so FastAPI yield
            # dependencies have released handler-owned DB connections.
            if (
                200 <= outcome_status < 300
                and request.method.upper() == "POST"
                and "/api-risk/rules" in request.url.path
            ):
                self._rule_cache_expires_at = 0.0
            if outcome_status:
                await self._complete_audit(decision.audit_id, outcome_status)

    async def _active_rules(
        self,
    ) -> tuple[ApiRiskRule, ...]:
        now = monotonic()
        if now < self._rule_cache_expires_at:
            return self._rule_cache
        async with self._rule_cache_lock:
            now = monotonic()
            if now < self._rule_cache_expires_at:
                return self._rule_cache
            # Open a session only for the cache owner. Concurrent waiters do
            # not occupy audit-pool connections while the cache lock is held.
            async with get_audit_sessionmaker()() as session:
                self._rule_cache = tuple(
                    await SecurityGovernanceService(session).active_request_rules()
                )
            # Coalesce a concurrent request wave without delaying a successful
            # rule mutation: rule-management responses invalidate immediately.
            self._rule_cache_expires_at = now + 0.25
            return self._rule_cache

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

    async def _complete_audit(self, audit_id: UUID, outcome_status: int) -> None:
        async with self._completion_semaphore:
            try:
                async with get_audit_sessionmaker()() as session:
                    await SecurityGovernanceService(session).complete_request_audit(
                        audit_id=audit_id, outcome_status=outcome_status
                    )
                    await session.commit()
            except SQLAlchemyError:
                # The decision row is already durable; status refresh failure must
                # not expose request data or turn a completed response into success.
                return
