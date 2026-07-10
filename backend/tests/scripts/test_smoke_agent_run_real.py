# Status: real

from __future__ import annotations

import json
import asyncio
from types import SimpleNamespace

import pytest

from scripts.smoke_agent_run_real import (
    SmokeFailure,
    main,
    parse_sse_text,
    validate_cancel_events,
    validate_confirmation,
    validate_success_events,
)
from scripts.probe_deepseek_json_protocol import (
    classify_json as classify_protocol_json,
    main as probe_main,
)
from app.runtime.harness.live_adapters import StrictLiveAdapters
from app.runtime.harness.live_adapters import StrictLLMOutputInvalid
from app.runtime.harness.base import _compact_json_schema
from app.agents.task_orchestrator.skills.generate_learning_path import GenerateLearningPathOutput
from app.llm.deepseek_provider import DeepSeekProvider
from app.llm.provider import LLMChunk, LLMMessage


def _event(event_id: int, event_name: str, **payload: object) -> dict[str, object]:
    return {"event_id": event_id, "event": event_name, **payload}


def test_confirmation_gate_does_not_send_network_request(monkeypatch, capsys):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("network must not be touched without --confirm-live")

    import scripts.smoke_agent_run_real as smoke

    monkeypatch.setattr(smoke, "_open_url", fail_if_called)
    assert main(["--mode", "success"]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["error_code"] == "LIVE_CONFIRMATION_REQUIRED"


def test_validate_confirmation_rejects_unconfirmed_live_run():
    with pytest.raises(SmokeFailure, match="no request was sent"):
        validate_confirmation(False)


def test_parse_sse_text_validates_event_names_and_cursors():
    text = (
        'id: 1\nevent: progress\ndata: {"event_id": 1, "status": "running"}\n\n'
        'id: 2\nevent: done\ndata: {"event_id": 2, "status": "succeeded"}\n\n'
    )
    events = parse_sse_text(text)
    assert [event["event"] for event in events] == ["progress", "done"]
    assert [event["event_id"] for event in events] == [1, 2]

    with pytest.raises(SmokeFailure, match="unsupported SSE event type"):
        parse_sse_text('id: 1\nevent: heartbeat\ndata: {}\n\n')


def test_success_validation_requires_real_five_child_persistence():
    child_ids = [f"00000000-0000-0000-0000-00000000000{index}" for index in range(1, 6)]
    evidence_ids = [f"00000000-0000-0000-0000-00000000010{index}" for index in range(1, 4)]
    events = [
        _event(1, "progress", mode="real"),
        _event(
            2,
            "evidence",
            mode="real",
            chunks=[{"chunk_id": evidence_id} for evidence_id in evidence_ids],
        ),
        _event(3, "token", mode="real", content="redacted"),
    ]
    for event_id, (agent_name, child_id) in enumerate(zip(
        ("career_planner", "task_orchestrator", "doc_archivist", "competition_advisor", "outcome_evaluator"),
        child_ids,
        strict=True,
    ), start=4):
        events.append(
            _event(
                event_id,
                "trace",
                mode="real",
                agent_name=agent_name,
                agent_run_id=child_id,
            )
        )
    events.append(_event(9, "done", mode="real", status="succeeded"))
    status = {
        "status": "succeeded",
        "mode": "real",
        "child_run_count": 5,
        "child_runs": [
            {"agent_run_id": child_id, "status": "succeeded", "persistence": "agent_runs"}
            for child_id in child_ids
        ],
    }
    assert validate_success_events(events, status) == set(evidence_ids)

    invalid_status = {**status, "child_runs": [
        {"agent_run_id": child_id, "status": "succeeded", "persistence": "registry"}
        for child_id in child_ids
    ]}
    with pytest.raises(SmokeFailure, match="not persisted as agent_runs"):
        validate_success_events(events, invalid_status)

    with pytest.raises(SmokeFailure, match="terminal error") as error:
        validate_success_events(
            [
                _event(1, "progress", mode="real"),
                _event(2, "error", mode="real", code="LLM_OUTPUT_INVALID"),
            ],
            {"status": "failed", "mode": "real", "child_run_count": 5, "child_runs": []},
        )
    assert error.value.code == "REAL_WORKFLOW_LLM_OUTPUT_INVALID"


def test_cancel_validation_rejects_token_after_cancel_cursor():
    status = {"status": "cancelled"}
    valid = [
        _event(1, "progress", mode="real"),
        _event(2, "token", mode="real"),
        _event(3, "done", mode="real", status="cancelled"),
    ]
    validate_cancel_events(valid, status, cancel_cursor=2)
    invalid = [*valid[:2], _event(3, "token", mode="real"), _event(4, "done", mode="real", status="cancelled")]
    with pytest.raises(SmokeFailure, match="after cancel cursor"):
        validate_cancel_events(invalid, status, cancel_cursor=2)


def test_real_evidence_projection_uses_document_source_url():
    hit = SimpleNamespace(
        chunk_id="chunk-1",
        document_id="document-1",
        domain="course_websec",
        source=None,
        chunk_text="evidence",
        reliability=0.8,
        score=0.7,
        metadata={"platform": "mineru", "rights_note": "internal"},
    )
    card = StrictLiveAdapters._evidence_card(hit, document_source_url="local://course.pdf")
    assert card.source == "local://course.pdf"


def test_deepseek_payload_can_request_json_object_without_network():
    provider = DeepSeekProvider(
        SimpleNamespace(
            DEEPSEEK_API_KEY="redacted-test-value",
            DEEPSEEK_MODEL="deepseek-v4-pro",
            DEEPSEEK_BASE_URL="https://api.deepseek.com",
        )
    )
    payload = provider._build_payload(
        [LLMMessage(role="user", content="test")],
        stream=True,
        temperature=0.2,
        max_tokens=32,
        response_format={"type": "json_object"},
    )
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["thinking"] == {"type": "disabled"}


def test_strict_json_diagnostic_exposes_only_safe_parse_metadata():
    with pytest.raises(StrictLLMOutputInvalid) as error:
        StrictLiveAdapters._parse_json("", finish_reason="length")
    assert error.value.diagnostics == {
        "phase": "parse",
        "finish_reason": "length",
        "content_length": 0,
        "has_final_content": False,
        "parse_category": "no_final_content",
    }
    assert "private" not in str(error.value)
    assert "prompt" not in str(error.value)


def test_compact_output_schema_is_complete_valid_json_and_not_truncated():
    schema = _compact_json_schema(GenerateLearningPathOutput)
    serialized = json.dumps(schema, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    assert json.loads(serialized) == schema
    assert schema["type"] == "object"
    assert set(schema["properties"]) >= {
        "content",
        "evidence_chunk_ids",
        "quality_score",
        "nodes",
        "edges",
        "milestones",
    }


def test_protocol_probe_confirmation_and_safe_json_classification(capsys):
    assert probe_main([]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output == {"ok": False, "error_code": "LIVE_CONFIRMATION_REQUIRED"}
    assert classify_protocol_json('{"answer":true}') == "json_object"
    assert classify_protocol_json("reasoning only") == "invalid_json"
    assert classify_protocol_json("") == "no_final_content"


def test_strict_adapter_rejects_reasoning_only_stream_without_sse_token():
    class ReasoningOnlyProvider:
        provider_name = "deepseek"
        model_name = "fake-deepseek-v4"

        def estimate_tokens(self, text: str) -> int:
            return max(1, len(text) // 4)

        async def stream_generate(self, *_args, **_kwargs):
            yield LLMChunk(content="", index=0, finish_reason="stop")

    events: list[dict[str, object]] = []

    async def emit(event: dict[str, object]) -> None:
        events.append(event)

    async def run():
        adapters = StrictLiveAdapters(provider=ReasoningOnlyProvider())
        await adapters.llm_complete(
            "redacted prompt",
            skill_name="GenerateCourseDoc",
            stream=True,
            emit=emit,
        )

    with pytest.raises(StrictLLMOutputInvalid) as error:
        asyncio.run(run())
    assert error.value.diagnostics["parse_category"] == "no_final_content"
    assert events == []


def test_strict_adapter_coalesces_small_provider_deltas_without_changing_json():
    payload = json.dumps(
        {
            "content": "x" * 256,
            "quality_score": 0.9,
        }
    )

    class CharacterDeltaProvider:
        provider_name = "deepseek"
        model_name = "fake-deepseek-v4"

        def estimate_tokens(self, text: str) -> int:
            return max(1, len(text) // 4)

        async def stream_generate(self, *_args, **_kwargs):
            for index, character in enumerate(payload):
                yield LLMChunk(content=character, index=index)
            yield LLMChunk(content="", index=len(payload), finish_reason="stop")

    events: list[dict[str, object]] = []

    async def emit(event: dict[str, object]) -> None:
        events.append(event)

    async def run() -> dict[str, object]:
        adapters = StrictLiveAdapters(provider=CharacterDeltaProvider())
        return await adapters.llm_complete(
            "redacted prompt",
            skill_name="GenerateCourseDoc",
            stream=True,
            emit=emit,
        )

    result = asyncio.run(run())
    streamed = "".join(str(event["content"]) for event in events)

    assert result["content"] == "x" * 256
    assert streamed == payload
    assert 1 < len(events) < len(payload) // 8
    assert all(event["event"] == "token" for event in events)
