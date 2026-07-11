"""Opt-in HTTP smoke for durable SecureHub workflow roots.

The script never sends a request without ``--confirm-live``.  Its output is
limited to IDs, statuses, counts and sanitised error codes so it can be kept as
an operational record without exposing prompts, generated content or secrets.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from collections.abc import Callable
import json
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener
from uuid import UUID, uuid4


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


API_PREFIX = "/api/v1"
DEFAULT_PROVIDER = "xfyun"
DEFAULT_MODE = "real"
PRODUCT_WORKFLOWS = (
    "profile_build_v1",
    "course_plan_v1",
    "tutor_routing_v1",
    "assessment_update_v1",
    "resource_generate_v1",
)
ALLOWED_EVENTS = frozenset({"progress", "evidence", "token", "artifact", "trace", "done", "error"})
DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"
DEMO_COURSE_ID = "00000000-0000-0000-0000-000000000101"
DEMO_KP_ID = "00000000-0000-0000-0000-000000000201"
DEMO_EMAIL = "demo-student@securehub.local"
DEMO_PASSWORD = "SecureHub@2026"
_URL_OPENER = build_opener(ProxyHandler({}))


class SmokeFailure(RuntimeError):
    """An actionable failure whose message is safe to print."""

    def __init__(self, code: str, message: str, *, root_run_id: str | None = None) -> None:
        self.code = code
        self.message = message
        self.root_run_id = root_run_id
        super().__init__(message)


def validate_confirmation(confirm_live: bool) -> None:
    if not confirm_live:
        raise SmokeFailure(
            "LIVE_CONFIRMATION_REQUIRED",
            "pass --confirm-live before this script sends any HTTP request",
        )


def _open_url(request: Request, *, timeout: float):
    return _URL_OPENER.open(request, timeout=timeout)


def _base_url(value: str) -> str:
    return value.rstrip("/")


def _finish_sse_event(
    *, event_name: str | None, event_id: int | None, data_lines: list[str]
) -> dict[str, Any] | None:
    if event_name is None:
        return None
    if event_name not in ALLOWED_EVENTS:
        raise SmokeFailure("SSE_EVENT_INVALID", f"unsupported event type: {event_name}")
    try:
        payload = json.loads("\n".join(data_lines) or "{}")
    except json.JSONDecodeError as exc:
        raise SmokeFailure("SSE_PAYLOAD_INVALID", "SSE payload was not JSON") from exc
    if not isinstance(payload, dict) or event_id is None or event_id < 1:
        raise SmokeFailure("SSE_CURSOR_INVALID", "SSE event lacked a positive id")
    sequence = payload.get("sequence")
    if sequence is not None and int(sequence) != event_id:
        raise SmokeFailure("SSE_CURSOR_MISMATCH", "SSE id did not match envelope sequence")
    payload["event"] = event_name
    payload["sequence"] = event_id
    return payload


def parse_sse_text(text: str) -> list[dict[str, Any]]:
    """Parse a complete SSE response without network I/O."""
    events: list[dict[str, Any]] = []
    event_name: str | None = None
    event_id: int | None = None
    data_lines: list[str] = []
    for raw_line in text.splitlines() + [""]:
        line = raw_line.rstrip("\r")
        if not line:
            event = _finish_sse_event(event_name=event_name, event_id=event_id, data_lines=data_lines)
            if event is not None:
                events.append(event)
            event_name, event_id, data_lines = None, None, []
        elif line.startswith(":"):
            continue
        elif line.startswith("event:"):
            event_name = line[6:].strip()
        elif line.startswith("id:"):
            try:
                event_id = int(line[3:].strip())
            except ValueError as exc:
                raise SmokeFailure("SSE_CURSOR_INVALID", "SSE id was not an integer") from exc
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    return events


class _SSEDecoder:
    def __init__(self) -> None:
        self.event_name: str | None = None
        self.event_id: int | None = None
        self.data_lines: list[str] = []

    def feed(self, raw_line: str) -> dict[str, Any] | None:
        line = raw_line.rstrip("\r\n")
        if not line:
            event = _finish_sse_event(
                event_name=self.event_name,
                event_id=self.event_id,
                data_lines=self.data_lines,
            )
            self.event_name, self.event_id, self.data_lines = None, None, []
            return event
        if line.startswith(":"):
            return None
        if line.startswith("event:"):
            self.event_name = line[6:].strip()
        elif line.startswith("id:"):
            try:
                self.event_id = int(line[3:].strip())
            except ValueError as exc:
                raise SmokeFailure("SSE_CURSOR_INVALID", "SSE id was not an integer") from exc
        elif line.startswith("data:"):
            self.data_lines.append(line[5:].lstrip())
        return None


def _request_json(
    base_url: str,
    method: str,
    path: str,
    *,
    timeout: float,
    expected_status: int,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    request_headers = {"Accept": "application/json", **(headers or {})}
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    request = Request(f"{_base_url(base_url)}{path}", data=data, headers=request_headers, method=method)
    try:
        with _open_url(request, timeout=timeout) as response:
            status_code = response.status
            raw = response.read()
    except HTTPError as exc:
        code = "HTTP_ERROR"
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("detail", {})
            if isinstance(detail, dict):
                code = str(detail.get("code") or code)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            pass
        raise SmokeFailure(f"HTTP_{exc.code}_{code}", "HTTP request failed") from exc
    except (OSError, URLError) as exc:
        raise SmokeFailure("HTTP_UNAVAILABLE", "backend HTTP endpoint was unavailable") from exc
    if status_code != expected_status:
        raise SmokeFailure("HTTP_STATUS_UNEXPECTED", f"expected {expected_status}, got {status_code}")
    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SmokeFailure("HTTP_JSON_INVALID", "HTTP response was not JSON") from exc
    if not isinstance(result, dict):
        raise SmokeFailure("HTTP_JSON_INVALID", "HTTP response was not an object")
    return result


def _request_sse(
    base_url: str,
    path: str,
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    request = Request(
        f"{_base_url(base_url)}{path}",
        headers={"Accept": "text/event-stream", **(headers or {})},
        method="GET",
    )
    decoder = _SSEDecoder()
    events: list[dict[str, Any]] = []
    try:
        with _open_url(request, timeout=timeout) as response:
            while raw_line := response.readline():
                event = decoder.feed(raw_line.decode("utf-8"))
                if event is None:
                    continue
                events.append(event)
                if on_event is not None:
                    on_event(event)
                if event["event"] in {"done", "error"}:
                    break
    except HTTPError as exc:
        raise SmokeFailure(f"HTTP_{exc.code}_SSE", "SSE endpoint rejected the request") from exc
    except (OSError, UnicodeDecodeError, URLError) as exc:
        raise SmokeFailure("SSE_UNAVAILABLE", "SSE stream could not be read") from exc
    if not events or events[-1]["event"] not in {"done", "error"}:
        raise SmokeFailure("SSE_TERMINAL_MISSING", "SSE stream ended before a terminal envelope")
    return events


def authenticate_demo(base_url: str, *, timeout: float) -> dict[str, str]:
    """Get the seeded demo user's token without ever printing its value."""
    response = _request_json(
        base_url,
        "POST",
        f"{API_PREFIX}/auth/login",
        timeout=timeout,
        expected_status=200,
        payload={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    token = response.get("access_token")
    if not isinstance(token, str) or not token:
        raise SmokeFailure("AUTH_TOKEN_MISSING", "demo login did not return an access token")
    return {"Authorization": f"Bearer {token}"}


def _workflow_input(workflow: str) -> tuple[str | None, dict[str, Any]]:
    if workflow == "profile_build_v1":
        return None, {"message": "Build a web-security learning persona", "domain": "course_websec"}
    if workflow == "course_plan_v1":
        return DEMO_COURSE_ID, {"query": "Build a SQL injection learning path", "domain": "course_websec"}
    if workflow == "tutor_routing_v1":
        return DEMO_COURSE_ID, {"question": "Why are parameterized queries safer?", "domain": "course_websec"}
    if workflow == "assessment_update_v1":
        return DEMO_COURSE_ID, {"answers": [], "domain": "course_websec"}
    if workflow == "resource_generate_v1":
        return DEMO_COURSE_ID, {
            "resource_type": "doc",
            "kp_id": DEMO_KP_ID,
            "query": "Generate a concise SQL injection learning document",
            "domain": "course_websec",
        }
    if workflow == "course_learning_full_v1":
        return DEMO_COURSE_ID, {
            "kp_id": DEMO_KP_ID,
            "query": "Generate a parallel SQL injection resource pack",
            "domain": "course_websec",
        }
    raise SmokeFailure("WORKFLOW_INVALID", f"unsupported smoke workflow: {workflow}")


def _start_payload(workflow: str, *, mode: str, provider: str, model: str | None) -> dict[str, Any]:
    course_id, input_payload = _workflow_input(workflow)
    return {
        "workflow": workflow,
        "user_id": DEMO_USER_ID,
        "course_id": course_id,
        "input": input_payload,
        "mode": mode,
        "provider": "fixture" if mode == "fixture" else provider,
        "model": "fixture-v1" if mode == "fixture" else model,
        "stream": True,
    }


def _validate_events(
    events: list[dict[str, Any]], status: dict[str, Any], *, mode: str, expect_cancel: bool
) -> None:
    sequences = [int(event["sequence"]) for event in events]
    if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
        raise SmokeFailure("SSE_SEQUENCE_INVALID", "SSE sequence was not strictly monotonic")
    if any(event.get("mode") != mode for event in events):
        raise SmokeFailure("SSE_MODE_INVALID", "SSE envelope mode drifted from the requested mode")
    terminal = events[-1]
    if expect_cancel:
        if terminal["event"] != "done" or terminal.get("payload", {}).get("status") != "cancelled":
            raise SmokeFailure("CANCEL_TERMINAL_INVALID", "cancelled root did not emit done/cancelled")
        if status.get("status") != "cancelled":
            raise SmokeFailure("CANCEL_STATUS_INVALID", "status API did not converge to cancelled")
        return
    if terminal["event"] == "error":
        code = terminal.get("payload", {}).get("code") or "WORKFLOW_FAILED"
        raise SmokeFailure(f"WORKFLOW_{code}", "workflow emitted a terminal error")
    if terminal.get("payload", {}).get("status") != "succeeded" or status.get("status") != "succeeded":
        raise SmokeFailure("SUCCESS_TERMINAL_INVALID", "workflow did not converge to succeeded")
    required = {"progress", "evidence", "trace", "done"}
    observed = {event["event"] for event in events}
    if not required.issubset(observed):
        raise SmokeFailure("SSE_EVENTS_MISSING", f"missing events: {sorted(required - observed)}")


async def _verify_db_alignment(run_id: str) -> dict[str, Any]:
    """Optional local DB verification for an API process using the same DB URL."""
    from sqlalchemy import select

    from app.db.models.agent.agent_run import AgentRun
    from app.db.models.workflow_runtime import WorkflowProviderCall, WorkflowRun
    from app.db.session import get_sessionmaker

    root_id = UUID(run_id)
    async with get_sessionmaker()() as session:
        root = await session.get(WorkflowRun, root_id)
        children = list(
            (await session.execute(select(AgentRun).where(AgentRun.workflow_run_id == root_id))).scalars().all()
        )
        calls = list(
            (await session.execute(select(WorkflowProviderCall).where(WorkflowProviderCall.workflow_run_id == root_id))).scalars().all()
        )
    if root is None:
        raise SmokeFailure("DB_ROOT_MISSING", "workflow root was not visible in the configured database", root_run_id=run_id)
    if not children or not calls:
        raise SmokeFailure("DB_CORRELATION_MISSING", "agent runs or provider calls were missing", root_run_id=run_id)
    return {
        "agent_run_ids": sorted(str(row.id) for row in children),
        "provider_call_ids": sorted(str(row.id) for row in calls),
        "provider_calls": len(calls),
        "workflow_status": str(root.status),
    }


def run_workflow(
    base_url: str,
    *,
    auth_headers: dict[str, str],
    workflow: str,
    mode: str,
    provider: str,
    model: str | None,
    timeout: float,
    cancel_after_first_token: bool,
    expect_fallback: bool,
    verify_db: bool,
) -> dict[str, Any]:
    start = _request_json(
        base_url,
        "POST",
        f"{API_PREFIX}/workflow-runs",
        timeout=timeout,
        expected_status=202,
        payload=_start_payload(workflow, mode=mode, provider=provider, model=model),
        headers={**auth_headers, "Idempotency-Key": f"wave456-smoke-{uuid4()}"},
    )
    run_id = str(start.get("run_id") or "")
    if not run_id:
        raise SmokeFailure("ROOT_ID_MISSING", "start response omitted durable root id")

    cancel_sent = False

    def cancel_on_token(event: dict[str, Any]) -> None:
        nonlocal cancel_sent
        if not cancel_after_first_token or cancel_sent or event["event"] != "token":
            return
        _request_json(
            base_url,
            "POST",
            f"{API_PREFIX}/workflow-runs/{run_id}/cancel",
            timeout=timeout,
            expected_status=200,
            headers=auth_headers,
        )
        cancel_sent = True

    try:
        events = _request_sse(
            base_url,
            f"{API_PREFIX}/workflow-runs/{run_id}/events",
            timeout=timeout,
            headers=auth_headers,
            on_event=cancel_on_token,
        )
        status = _request_json(
            base_url,
            "GET",
            f"{API_PREFIX}/workflow-runs/{run_id}",
            timeout=timeout,
            expected_status=200,
            headers=auth_headers,
        )
        _validate_events(events, status, mode=mode, expect_cancel=cancel_after_first_token)
        replay = _request_sse(
            base_url,
            f"{API_PREFIX}/workflow-runs/{run_id}/events",
            timeout=timeout,
            headers={**auth_headers, "Last-Event-ID": "0"},
        )
        if [event["sequence"] for event in events] != [event["sequence"] for event in replay]:
            raise SmokeFailure("SSE_REPLAY_MISMATCH", "PostgreSQL replay did not reproduce the ordered stream")
        switches = [
            event
            for event in events
            if event["event"] == "trace" and isinstance(event.get("payload", {}).get("provider_switch"), dict)
        ]
        if expect_fallback and not switches:
            raise SmokeFailure("FALLBACK_NOT_OBSERVED", "expected a transparent provider replacement trace")
        actual_providers = sorted(
            {
                str(event.get("actual_provider"))
                for event in events
                if event.get("actual_provider") is not None
            }
        )
        if mode == "real" and "fixture" in actual_providers:
            raise SmokeFailure("REAL_FIXTURE_LEAK", "real root exposed a fixture provider")
        result: dict[str, Any] = {
            "root_run_id": run_id,
            "workflow": workflow,
            "status": status.get("status"),
            "mode": mode,
            "requested_provider": start.get("requested_provider"),
            "actual_provider": status.get("actual_provider"),
            "event_counts": dict(Counter(event["event"] for event in events)),
            "event_count": len(events),
            "replay_event_count": len(replay),
            "child_run_count": status.get("child_run_count"),
            "provider_switches": len(switches),
        }
        if verify_db:
            result["database"] = asyncio.run(_verify_db_alignment(run_id))
        return result
    except SmokeFailure as exc:
        raise SmokeFailure(exc.code, exc.message, root_run_id=run_id) from exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Opt-in durable workflow smoke")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument("--workflow", default="course_learning_full_v1")
    parser.add_argument("--all-product-paths", action="store_true")
    parser.add_argument("--mode", choices=("real", "fixture"), default=DEFAULT_MODE)
    parser.add_argument("--provider", default=DEFAULT_PROVIDER)
    parser.add_argument("--model", default=None)
    parser.add_argument("--cancel-after-first-token", action="store_true")
    parser.add_argument("--expect-fallback", action="store_true")
    parser.add_argument("--verify-db", action="store_true")
    parser.add_argument("--confirm-live", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        validate_confirmation(args.confirm_live)
        if args.timeout_seconds <= 0:
            raise SmokeFailure("TIMEOUT_INVALID", "timeout must be positive")
        auth_headers = authenticate_demo(args.base_url, timeout=args.timeout_seconds)
        workflows = PRODUCT_WORKFLOWS if args.all_product_paths else (args.workflow,)
        if args.all_product_paths and args.cancel_after_first_token:
            raise SmokeFailure("ARGUMENT_CONFLICT", "cancel smoke supports one workflow per invocation")
        results = [
            run_workflow(
                args.base_url,
                auth_headers=auth_headers,
                workflow=workflow,
                mode=args.mode,
                provider=args.provider,
                model=args.model,
                timeout=args.timeout_seconds,
                cancel_after_first_token=args.cancel_after_first_token,
                expect_fallback=args.expect_fallback,
                verify_db=args.verify_db,
            )
            for workflow in workflows
        ]
        print(json.dumps({"ok": True, "results": results}, ensure_ascii=False, sort_keys=True))
        return 0
    except SmokeFailure as exc:
        result: dict[str, Any] = {"ok": False, "error_code": exc.code, "message": exc.message}
        if exc.root_run_id:
            result["root_run_id"] = exc.root_run_id
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
