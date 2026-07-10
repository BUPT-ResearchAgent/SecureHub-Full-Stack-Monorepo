# Status: real

"""Reproducible, opt-in HTTP smoke for the Agent Run real workflow.

The script intentionally keeps the paid boundary explicit: without
``--confirm-live`` it performs no network or database work.  It reports only
identifiers, counts, statuses, and error codes; model content is never printed.
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
from urllib.request import Request, ProxyHandler, build_opener
from uuid import UUID

# Make the documented ``python scripts/<file>.py`` invocation resolve the
# backend package; module execution already has the correct import root.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.models.agent.agent_run import AgentRun
from app.db.seeds._constants import COURSE_WEBSEC_ID, DEMO_USER_ID
from app.db.session import get_sessionmaker
from app.runtime.workflows.course_learning_minimal import WORKFLOW_NAME
from sqlalchemy import select


API_PREFIX = "/api/v1"
EXPECTED_MODEL = "deepseek-v4-pro"
EXPECTED_PROVIDER = "deepseek"
EXPECTED_MODE = "real"
EXPECTED_AGENTS = (
    "career_planner",
    "task_orchestrator",
    "doc_archivist",
    "competition_advisor",
    "outcome_evaluator",
)
ALLOWED_EVENTS = frozenset(
    {"progress", "evidence", "token", "artifact", "trace", "done", "error"}
)
_URL_OPENER = build_opener(ProxyHandler({}))


class SmokeFailure(RuntimeError):
    """An actionable, safe-to-print smoke failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _open_url(request: Request, *, timeout: float):
    """Use direct local HTTP so machine proxy settings cannot turn localhost into 502."""
    return _URL_OPENER.open(request, timeout=timeout)


def validate_confirmation(confirm_live: bool) -> None:
    if not confirm_live:
        raise SmokeFailure(
            "LIVE_CONFIRMATION_REQUIRED",
            "pass --confirm-live to enable real HTTP smoke; no request was sent",
        )


def _as_string(value: Any) -> str:
    return str(value) if value is not None else ""


def _finish_sse_event(
    *,
    event_name: str | None,
    event_id: int | None,
    data_lines: list[str],
) -> dict[str, Any] | None:
    if event_name is None:
        return None
    if event_name not in ALLOWED_EVENTS:
        raise SmokeFailure("SSE_EVENT_INVALID", f"unsupported SSE event type: {event_name}")
    try:
        payload = json.loads("\n".join(data_lines) or "{}")
    except json.JSONDecodeError as exc:
        raise SmokeFailure("SSE_PAYLOAD_INVALID", "SSE data is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise SmokeFailure("SSE_PAYLOAD_INVALID", "SSE data must be a JSON object")
    payload_event_id = payload.get("event_id")
    if event_id is not None and payload_event_id is not None:
        if int(payload_event_id) != event_id:
            raise SmokeFailure("SSE_CURSOR_MISMATCH", "SSE id and payload event_id differ")
    resolved_event_id = event_id if event_id is not None else payload_event_id
    if resolved_event_id is None or int(resolved_event_id) < 1:
        raise SmokeFailure("SSE_CURSOR_MISSING", "SSE event has no positive event_id")
    payload["event"] = event_name
    payload["event_id"] = int(resolved_event_id)
    return payload


def parse_sse_text(text: str) -> list[dict[str, Any]]:
    """Parse a complete SSE response without performing I/O."""
    events: list[dict[str, Any]] = []
    event_name: str | None = None
    event_id: int | None = None
    data_lines: list[str] = []
    for raw_line in text.splitlines() + [""]:
        line = raw_line.rstrip("\r")
        if not line:
            event = _finish_sse_event(
                event_name=event_name,
                event_id=event_id,
                data_lines=data_lines,
            )
            if event is not None:
                events.append(event)
            event_name = None
            event_id = None
            data_lines = []
        elif line.startswith(":"):
            continue
        elif line.startswith("event:"):
            event_name = line[6:].strip()
        elif line.startswith("id:"):
            try:
                event_id = int(line[3:].strip())
            except ValueError as exc:
                raise SmokeFailure("SSE_CURSOR_INVALID", "SSE id is not an integer") from exc
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    return events


class _SSEDecoder:
    def __init__(self) -> None:
        self.event_name: str | None = None
        self.event_id: int | None = None
        self.data_lines: list[str] = []

    def feed(self, line: str) -> dict[str, Any] | None:
        line = line.rstrip("\r\n")
        if not line:
            event = _finish_sse_event(
                event_name=self.event_name,
                event_id=self.event_id,
                data_lines=self.data_lines,
            )
            self.event_name = None
            self.event_id = None
            self.data_lines = []
            return event
        if line.startswith(":"):
            return None
        if line.startswith("event:"):
            self.event_name = line[6:].strip()
        elif line.startswith("id:"):
            try:
                self.event_id = int(line[3:].strip())
            except ValueError as exc:
                raise SmokeFailure("SSE_CURSOR_INVALID", "SSE id is not an integer") from exc
        elif line.startswith("data:"):
            self.data_lines.append(line[5:].lstrip())
        return None


def validate_real_start(body: dict[str, Any]) -> None:
    if (
        body.get("mode") != EXPECTED_MODE
        or body.get("provider") != EXPECTED_PROVIDER
        or body.get("model") != EXPECTED_MODEL
        or body.get("workflow") != WORKFLOW_NAME
    ):
        raise SmokeFailure(
            "REAL_START_IDENTITY_INVALID",
            "start response did not identify real/deepseek/deepseek-v4-pro",
        )


def _event_ids(events: list[dict[str, Any]]) -> list[int]:
    ids = [int(event["event_id"]) for event in events]
    if ids != sorted(ids) or len(set(ids)) != len(ids):
        raise SmokeFailure("SSE_CURSOR_NOT_MONOTONIC", "SSE event_id is not strictly monotonic")
    return ids


def validate_success_events(
    events: list[dict[str, Any]],
    status: dict[str, Any],
    *,
    expected_mode: str = EXPECTED_MODE,
) -> set[str]:
    """Validate the success contract and return evidence IDs from SSE."""
    _event_ids(events)
    terminal_errors = [event for event in events if event["event"] == "error"]
    if terminal_errors:
        code = str(terminal_errors[-1].get("code") or "WORKFLOW_FAILED")
        raise SmokeFailure(
            f"REAL_WORKFLOW_{code}",
            "real workflow emitted a terminal error before success",
        )
    event_types = {event["event"] for event in events}
    required = {"progress", "evidence", "token", "trace", "done"}
    if not required.issubset(event_types):
        raise SmokeFailure(
            "SSE_REQUIRED_EVENTS_MISSING",
            f"SSE is missing required event types: {sorted(required - event_types)}",
        )
    done = [event for event in events if event["event"] == "done"]
    if len(done) != 1 or done[0].get("status") != "succeeded":
        raise SmokeFailure("SUCCESS_TERMINAL_INVALID", "success smoke did not end with done/succeeded")
    if status.get("status") != "succeeded" or status.get("mode") != expected_mode:
        raise SmokeFailure("STATUS_NOT_SUCCEEDED", "status API did not report real succeeded")
    if status.get("child_run_count") != 5 or len(status.get("child_runs", [])) != 5:
        raise SmokeFailure("CHILD_COUNT_INVALID", "status API did not report five child runs")
    children = status["child_runs"]
    if any(
        child.get("persistence") != "agent_runs" or child.get("status") != "succeeded"
        for child in children
    ):
        raise SmokeFailure("CHILD_PERSISTENCE_INVALID", "a real child was not persisted as agent_runs")
    traces = [event for event in events if event["event"] == "trace"]
    if len(traces) != 5 or [event.get("agent_name") for event in traces] != list(EXPECTED_AGENTS):
        raise SmokeFailure("TRACE_CHAIN_INVALID", "trace chain does not match the fixed five-agent order")
    trace_ids = {str(event.get("agent_run_id")) for event in traces}
    child_ids = {str(child.get("agent_run_id")) for child in children}
    if "None" in trace_ids or trace_ids != child_ids:
        raise SmokeFailure("TRACE_UUID_MISMATCH", "API child UUIDs and SSE trace UUIDs differ")
    if any(event.get("mode") != expected_mode for event in events):
        raise SmokeFailure("EVENT_MODE_INVALID", "success SSE contains a non-real event label")
    evidence_ids = {
        str(chunk["chunk_id"])
        for event in events
        if event["event"] == "evidence"
        for chunk in event.get("chunks", [])
        if isinstance(chunk, dict) and chunk.get("chunk_id")
    }
    if len(evidence_ids) < 3:
        raise SmokeFailure("EVIDENCE_IDS_MISSING", "success SSE exposed fewer than three evidence IDs")
    if any(event["event"] == "artifact" for event in events):
        raise SmokeFailure("UNEXPECTED_ARTIFACT", "artifact was emitted without generated_resources persistence")
    return evidence_ids


def validate_cancel_events(
    events: list[dict[str, Any]],
    status: dict[str, Any],
    *,
    cancel_cursor: int,
) -> None:
    _event_ids(events)
    if status.get("status") != "cancelled":
        raise SmokeFailure("CANCEL_TERMINAL_INVALID", "cancel smoke did not converge to cancelled")
    if not any(event["event"] == "token" for event in events):
        raise SmokeFailure("CANCEL_TOKEN_NOT_OBSERVED", "cancel smoke did not observe a token before cancel")
    done = [event for event in events if event["event"] == "done"]
    if len(done) != 1 or done[0].get("status") != "cancelled":
        raise SmokeFailure("CANCEL_DONE_INVALID", "cancel smoke did not emit done/cancelled")
    if any(
        int(event["event_id"]) > cancel_cursor and event["event"] in {"token", "artifact"}
        for event in events
    ):
        raise SmokeFailure("CANCEL_STREAM_LEAK", "token or artifact appeared after cancel cursor")


def _base_url(value: str) -> str:
    return value.rstrip("/")


def _request_json(
    base_url: str,
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float,
    expected_status: int,
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request_headers = {"Accept": "application/json", **(headers or {})}
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    request = Request(
        f"{_base_url(base_url)}{path}",
        data=data,
        headers=request_headers,
        method=method,
    )
    try:
        with _open_url(request, timeout=timeout) as response:
            status = response.status
            raw = response.read()
    except HTTPError as exc:
        code = "HTTP_ERROR"
        try:
            body = json.loads(exc.read().decode("utf-8"))
            detail = body.get("detail", {}) if isinstance(body, dict) else {}
            if isinstance(detail, dict):
                code = str(detail.get("code") or code)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            pass
        raise SmokeFailure(f"HTTP_{exc.code}_{code}", "HTTP request failed") from exc
    except (OSError, URLError) as exc:
        raise SmokeFailure("HTTP_UNAVAILABLE", "HTTP request could not reach the local backend") from exc
    if status != expected_status:
        raise SmokeFailure(
            f"HTTP_STATUS_{status}",
            f"expected HTTP {expected_status}, received {status}",
        )
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SmokeFailure("HTTP_JSON_INVALID", "HTTP response was not valid JSON") from exc
    if not isinstance(body, dict):
        raise SmokeFailure("HTTP_JSON_INVALID", "HTTP response was not a JSON object")
    return body


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
    events: list[dict[str, Any]] = []
    decoder = _SSEDecoder()
    try:
        with _open_url(request, timeout=timeout) as response:
            while True:
                raw_line = response.readline()
                if not raw_line:
                    break
                event = decoder.feed(raw_line.decode("utf-8"))
                if event is None:
                    continue
                events.append(event)
                if on_event is not None:
                    on_event(event)
                if event["event"] in {"done", "error"}:
                    break
    except HTTPError as exc:
        raise SmokeFailure(f"HTTP_{exc.code}_SSE_ERROR", "SSE request failed") from exc
    except (OSError, UnicodeDecodeError, URLError) as exc:
        raise SmokeFailure("SSE_UNAVAILABLE", "SSE stream could not be read") from exc
    if not events:
        raise SmokeFailure("SSE_EMPTY", "SSE stream returned no events")
    if events[-1]["event"] not in {"done", "error"}:
        raise SmokeFailure("SSE_TERMINAL_MISSING", "SSE stream ended without a terminal event")
    return events


def _start_payload() -> dict[str, Any]:
    return {
        "workflow": WORKFLOW_NAME,
        "user_id": str(DEMO_USER_ID),
        "course_id": str(COURSE_WEBSEC_ID),
        "topic": "SQL 注入",
        "goal": "生成证据驱动学习闭环",
        "mode": EXPECTED_MODE,
        "provider": EXPECTED_PROVIDER,
        "stream": True,
    }


def _manifest(base_url: str, timeout: float) -> dict[str, Any]:
    body = _request_json(
        base_url,
        "GET",
        f"{API_PREFIX}/agents/manifest",
        timeout=timeout,
        expected_status=200,
    )
    if body.get("total") != 9 or len(body.get("agents", [])) != 9:
        raise SmokeFailure("MANIFEST_COUNT_INVALID", "manifest did not return exactly nine agents")
    return body


def _start(base_url: str, timeout: float) -> dict[str, Any]:
    body = _request_json(
        base_url,
        "POST",
        f"{API_PREFIX}/workflow-runs",
        payload=_start_payload(),
        timeout=timeout,
        expected_status=202,
    )
    validate_real_start(body)
    return body


def _status(base_url: str, run_id: str, timeout: float) -> dict[str, Any]:
    return _request_json(
        base_url,
        "GET",
        f"{API_PREFIX}/workflow-runs/{run_id}",
        timeout=timeout,
        expected_status=200,
    )


async def _query_agent_runs(run_id: str) -> dict[str, Any]:
    try:
        root_uuid = UUID(run_id)
    except ValueError as exc:
        raise SmokeFailure("RUN_ID_INVALID", "workflow run id is not a UUID") from exc
    async with get_sessionmaker()() as session:
        stmt = (
            select(AgentRun)
            .where(AgentRun.input_summary["workflow_run_id"].as_string() == str(root_uuid))
            .order_by(AgentRun.created_at, AgentRun.id)
        )
        rows = list((await session.execute(stmt)).scalars().all())
    if len(rows) != 5:
        raise SmokeFailure("AGENT_RUN_COUNT_INVALID", "PostgreSQL did not return five child agent_runs")
    if any(row.user_id is None or row.agent_id is None or row.skill_id is None for row in rows):
        raise SmokeFailure("AGENT_RUN_FOREIGN_KEYS_INVALID", "a child agent_runs row has a missing foreign key")
    if any(row.status != "success" for row in rows):
        raise SmokeFailure("AGENT_RUN_STATUS_INVALID", "a success smoke child agent_runs row is not success")
    evidence_ids = {
        str(chunk_id)
        for row in rows
        for chunk_id in (row.evidence_chunk_ids or [])
    }
    return {
        "count": len(rows),
        "run_ids": [str(row.id) for row in rows],
        "agent_ids": [str(row.agent_id) for row in rows],
        "skill_ids": [str(row.skill_id) for row in rows],
        "user_ids": [str(row.user_id) for row in rows],
        "evidence_ids": sorted(evidence_ids),
        "statuses": Counter(str(row.status) for row in rows),
    }


def run_success(base_url: str, timeout: float) -> dict[str, Any]:
    start = _start(base_url, timeout)
    run_id = str(start["run_id"])
    events = _request_sse(
        base_url,
        f"{API_PREFIX}/workflow-runs/{run_id}/events",
        timeout=timeout,
    )
    status = _status(base_url, run_id, timeout)
    evidence_ids = validate_success_events(events, status)
    db = asyncio.run(_query_agent_runs(run_id))
    if set(db["run_ids"]) != {
        str(child["agent_run_id"])
        for child in status["child_runs"]
    }:
        raise SmokeFailure("DB_TRACE_UUID_MISMATCH", "PostgreSQL child UUIDs differ from status API")
    if set(db["evidence_ids"]) != evidence_ids:
        raise SmokeFailure("DB_EVIDENCE_MISMATCH", "PostgreSQL evidence IDs differ from SSE evidence IDs")
    replay = _request_sse(
        base_url,
        f"{API_PREFIX}/workflow-runs/{run_id}/events",
        timeout=timeout,
        headers={"Last-Event-ID": "0"},
    )
    if [int(event["event_id"]) for event in replay] != [int(event["event_id"]) for event in events]:
        raise SmokeFailure("SSE_REPLAY_MISMATCH", "Last-Event-ID replay did not reproduce the event history")
    return {
        "mode": EXPECTED_MODE,
        "provider": EXPECTED_PROVIDER,
        "model": start["model"],
        "root_run_id": run_id,
        "status": status["status"],
        "event_counts": dict(Counter(event["event"] for event in events)),
        "event_count": len(events),
        "replay_event_count": len(replay),
        "agent_run_count": db["count"],
        "agent_run_ids": db["run_ids"],
        "evidence_ids": sorted(evidence_ids),
    }


def run_cancel(base_url: str, timeout: float) -> dict[str, Any]:
    start = _start(base_url, timeout)
    run_id = str(start["run_id"])
    cancel_cursor: int | None = None
    cancel_response: dict[str, Any] | None = None

    def cancel_after_token(event: dict[str, Any]) -> None:
        nonlocal cancel_cursor, cancel_response
        if event["event"] == "token" and cancel_cursor is None:
            cancel_cursor = int(event["event_id"])
            cancel_response = _request_json(
                base_url,
                "POST",
                f"{API_PREFIX}/workflow-runs/{run_id}/cancel",
                timeout=timeout,
                expected_status=200,
            )

    events = _request_sse(
        base_url,
        f"{API_PREFIX}/workflow-runs/{run_id}/events",
        timeout=timeout,
        on_event=cancel_after_token,
    )
    if cancel_cursor is None or cancel_response is None:
        terminal_errors = [event for event in events if event["event"] == "error"]
        if terminal_errors:
            code = str(terminal_errors[-1].get("code") or "WORKFLOW_FAILED")
            raise SmokeFailure(
                f"CANCEL_BEFORE_TOKEN_{code}",
                "cancel workflow ended before a token, so cancel was not sent",
            )
        raise SmokeFailure("CANCEL_NOT_SENT", "cancel endpoint was not called after a token")
    status = _status(base_url, run_id, timeout)
    validate_cancel_events(events, status, cancel_cursor=cancel_cursor)
    return {
        "mode": EXPECTED_MODE,
        "provider": EXPECTED_PROVIDER,
        "model": start["model"],
        "root_run_id": run_id,
        "status": status["status"],
        "cancel_cursor": cancel_cursor,
        "cancel_response_status": cancel_response.get("status"),
        "event_counts": dict(Counter(event["event"] for event in events)),
        "event_count": len(events),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Opt-in Agent Run real HTTP smoke")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument(
        "--mode",
        choices=("success", "cancel-after-first-token", "both"),
        default="success",
    )
    parser.add_argument(
        "--confirm-live",
        action="store_true",
        help="required acknowledgement before any real HTTP request",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        validate_confirmation(args.confirm_live)
        if args.timeout_seconds <= 0:
            raise SmokeFailure("TIMEOUT_INVALID", "--timeout-seconds must be positive")
        _manifest(args.base_url, args.timeout_seconds)
        if args.mode == "success":
            result: Any = run_success(args.base_url, args.timeout_seconds)
        elif args.mode == "cancel-after-first-token":
            result = run_cancel(args.base_url, args.timeout_seconds)
        else:
            result = {
                "cancel": run_cancel(args.base_url, args.timeout_seconds),
                "success": run_success(args.base_url, args.timeout_seconds),
            }
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, sort_keys=True))
        return 0
    except SmokeFailure as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "message": exc.message}, ensure_ascii=False))
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
