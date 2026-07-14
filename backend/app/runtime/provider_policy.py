# Status: real

"""Explicit real-provider policy, rate limiting and circuit state.

The policy never returns ``fixture`` for a real root.  Spark is the production
demonstration primary and DeepSeek is its transparent real fallback.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from time import monotonic
from typing import Callable

from app.runtime.contracts import ExecutionMode


class ProviderPolicyError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ProviderRoute:
    primary: str
    fallback: str | None
    policy_version: str = "spark-primary-deepseek-fallback-v1"


@dataclass(slots=True)
class _CircuitState:
    failures: deque[float] = field(default_factory=deque)
    open_until: float = 0.0


class ProviderCircuitBreaker:
    """Small process-local protection; durable calls still remain the audit truth."""

    def __init__(self, *, failure_threshold: int = 3, window_seconds: float = 60.0, cooldown_seconds: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self._states: dict[str, _CircuitState] = {}

    def allow(self, provider: str) -> bool:
        state = self._states.get(provider)
        return state is None or monotonic() >= state.open_until

    def record_success(self, provider: str) -> None:
        state = self._states.setdefault(provider, _CircuitState())
        state.failures.clear()
        state.open_until = 0.0

    def record_failure(self, provider: str) -> None:
        now = monotonic()
        state = self._states.setdefault(provider, _CircuitState())
        state.failures.append(now)
        while state.failures and now - state.failures[0] > self.window_seconds:
            state.failures.popleft()
        if len(state.failures) >= self.failure_threshold:
            state.open_until = now + self.cooldown_seconds


class ProviderRateLimiter:
    """Conservative in-process limiter used before a billable provider call."""

    def __init__(self, *, max_calls: int = 30, window_seconds: float = 60.0) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[str, deque[float]] = {}

    def allow(self, provider: str) -> bool:
        now = monotonic()
        calls = self._calls.setdefault(provider, deque())
        while calls and now - calls[0] > self.window_seconds:
            calls.popleft()
        if len(calls) >= self.max_calls:
            return False
        calls.append(now)
        return True


class ProviderPolicy:
    def __init__(
        self,
        *,
        routes: dict[str, str | None] | None = None,
        circuit_breaker: ProviderCircuitBreaker | None = None,
        rate_limiter: ProviderRateLimiter | None = None,
    ) -> None:
        self.routes = routes or {"xfyun": "deepseek", "deepseek": "xfyun"}
        self.circuit_breaker = circuit_breaker or ProviderCircuitBreaker()
        self.rate_limiter = rate_limiter or ProviderRateLimiter()

    def route_for(self, *, mode: ExecutionMode, requested_provider: str | None) -> ProviderRoute:
        primary = str(requested_provider or "xfyun").strip().lower()
        if mode == ExecutionMode.FIXTURE:
            return ProviderRoute("fixture", None, "fixture-v1")
        if primary not in self.routes:
            raise ProviderPolicyError(f"unknown real provider: {primary}")
        fallback = self.routes.get(primary)
        if fallback == "fixture":
            raise ProviderPolicyError("real provider policy cannot route to fixture")
        return ProviderRoute(primary, fallback)

    def can_call(self, provider: str) -> str | None:
        if provider == "fixture":
            return None
        if not self.circuit_breaker.allow(provider):
            return "CIRCUIT_OPEN"
        if not self.rate_limiter.allow(provider):
            return "RATE_LIMITED"
        return None

    def record_success(self, provider: str) -> None:
        if provider != "fixture":
            self.circuit_breaker.record_success(provider)

    def record_failure(self, provider: str) -> None:
        if provider != "fixture":
            self.circuit_breaker.record_failure(provider)


ProviderResolver = Callable[[str], object]


__all__ = [
    "ProviderCircuitBreaker",
    "ProviderPolicy",
    "ProviderPolicyError",
    "ProviderRateLimiter",
    "ProviderRoute",
]
