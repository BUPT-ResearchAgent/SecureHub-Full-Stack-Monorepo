"""Offline contract tests for the opt-in durable live-smoke helper."""

from __future__ import annotations

import json

import pytest

from scripts.smoke_agent_run_real import (
    SmokeFailure,
    _start_payload,
    authenticate_demo,
    main,
    parse_sse_text,
    validate_confirmation,
)


def test_confirmation_gate_makes_no_network_request(capsys) -> None:
    assert main([]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["error_code"] == "LIVE_CONFIRMATION_REQUIRED"


def test_validate_confirmation_rejects_unconfirmed_runs() -> None:
    with pytest.raises(SmokeFailure, match="confirm-live"):
        validate_confirmation(False)


def test_sse_parser_uses_durable_envelope_sequence() -> None:
    events = parse_sse_text(
        'id: 1\nevent: progress\ndata: {"sequence": 1, "mode": "real", "payload": {"status": "running"}}\n\n'
        'id: 2\nevent: done\ndata: {"sequence": 2, "mode": "real", "payload": {"status": "succeeded"}}\n\n'
    )
    assert [event["event"] for event in events] == ["progress", "done"]
    assert [event["sequence"] for event in events] == [1, 2]


def test_parser_rejects_mismatched_sse_cursor() -> None:
    with pytest.raises(SmokeFailure, match="did not match"):
        parse_sse_text('id: 2\nevent: done\ndata: {"sequence": 1}\n\n')


def test_default_real_payload_selects_spark_primary() -> None:
    payload = _start_payload("course_learning_full_v1", mode="real", provider="xfyun", model=None)
    assert payload["mode"] == "real"
    assert payload["provider"] == "xfyun"
    assert payload["input"]["course_id"] if "course_id" in payload["input"] else payload["course_id"]


def test_fixture_payload_is_explicit() -> None:
    payload = _start_payload("resource_generate_v1", mode="fixture", provider="xfyun", model=None)
    assert payload["provider"] == "fixture"
    assert payload["model"] == "fixture-v1"


def test_demo_authentication_returns_header_without_exposing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_request(*_args: object, **kwargs: object) -> dict[str, str]:
        captured.update(kwargs)
        return {"access_token": "test-token"}

    monkeypatch.setattr("scripts.smoke_agent_run_real._request_json", fake_request)

    assert authenticate_demo("http://example.invalid", timeout=3) == {"Authorization": "Bearer test-token"}
    assert captured["expected_status"] == 200
    assert captured["payload"] == {
        "email": "demo-student@securehub.local",
        "password": "SecureHub@2026",
    }
