# Status: real

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import app.llm.xfyun_provider as xfyun_module
from app.agents.outcome_evaluator.skills.quality_check import QualityCheckOutput
from app.llm.provider import LLMMessage


class _FakeResponse:
    def __init__(self, *, body: dict | None = None, lines: list[str] | None = None) -> None:
        self._body = body or {}
        self._lines = lines or []

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._body

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class _FakeStreamContext:
    def __init__(self, response: _FakeResponse) -> None:
        self.response = response

    async def __aenter__(self) -> _FakeResponse:
        return self.response

    async def __aexit__(self, *_args: object) -> None:
        return None


def _provider(monkeypatch, response: _FakeResponse) -> tuple[object, dict[str, object]]:
    calls: dict[str, object] = {}

    class _FakeClient:
        def __init__(self, **_kwargs: object) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, url: str, **kwargs: object) -> _FakeResponse:
            calls["url"] = url
            calls.update(kwargs)
            return response

        def stream(self, _method: str, url: str, **kwargs: object) -> _FakeStreamContext:
            calls["url"] = url
            calls.update(kwargs)
            return _FakeStreamContext(response)

    monkeypatch.setattr(xfyun_module.httpx, "AsyncClient", _FakeClient)
    provider = xfyun_module.XunfeiSparkProvider(
        SimpleNamespace(
            XFYUN_API_KEY="test-api-password",
            XFYUN_BASE_URL="https://spark-api-open.xf-yun.com/agent/v1/",
            XFYUN_MODEL="spark-x",
            XFYUN_THINKING_MODE="disabled",
        )
    )
    return provider, calls


def test_x2_generate_uses_agent_endpoint_model_and_bearer_auth(monkeypatch):
    provider, calls = _provider(
        monkeypatch,
        _FakeResponse(
            body={
                "choices": [
                    {
                        "message": {
                            "content": "ignored final prose",
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "securehub_emit_json",
                                        "arguments": '{"answer":"ok"}',
                                    }
                                }
                            ],
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
        ),
    )

    response = asyncio.run(
        provider.generate(
            [LLMMessage(role="user", content="ping")],
            max_tokens=1,
            response_format={"type": "json_object"},
            response_schema={
                "type": "object",
                "properties": {"answer": {"type": "string"}},
                "required": ["answer"],
            },
        )
    )

    assert response.content == '{"answer":"ok"}'
    assert response.model == "spark-x"
    assert calls["url"] == "https://spark-api-open.xf-yun.com/agent/v1/chat/completions"
    assert calls["headers"] == {
        "Authorization": "Bearer test-api-password",
        "Content-Type": "application/json",
    }
    assert calls["json"]["model"] == "spark-x"
    assert calls["json"]["max_tokens"] == 1
    assert calls["json"]["thinking"] == {"type": "disabled"}
    assert "response_format" not in calls["json"]
    assert calls["json"]["tool_choice"] == {"type": "function", "name": "securehub_emit_json"}
    assert calls["json"]["tools"][0]["function"]["parameters"] == {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
    }


def test_x2_stream_uses_final_content_only(monkeypatch):
    provider, calls = _provider(
        monkeypatch,
        _FakeResponse(
            lines=[
                'data: {"choices":[{"delta":{"reasoning_content":"private"}}]}',
                'data: {"choices":[{"delta":{"content":"ok"}}]}',
                "data: [DONE]",
            ]
        ),
    )

    async def collect():
        return [
            chunk
            async for chunk in provider.stream_generate(
                [LLMMessage(role="user", content="ping")],
                response_format={"type": "json_object"},
            )
        ]

    chunks = asyncio.run(collect())

    assert "".join(chunk.content for chunk in chunks) == "ok"
    assert calls["url"] == "https://spark-api-open.xf-yun.com/agent/v1/chat/completions"
    assert calls["json"]["thinking"] == {"type": "disabled"}


def test_x2_structured_stream_uses_nonstream_tool_arguments(monkeypatch):
    provider, calls = _provider(
        monkeypatch,
        _FakeResponse(
            body={
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "securehub_emit_json",
                                        "arguments": '{"answer":"ok"}',
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ),
    )

    async def collect():
        return [
            chunk
            async for chunk in provider.stream_generate(
                [LLMMessage(role="user", content="ping")],
                response_format={"type": "json_object"},
                response_schema={"type": "object"},
            )
        ]

    chunks = asyncio.run(collect())

    assert [chunk.content for chunk in chunks] == ['{"answer":"ok"}']
    assert calls["url"] == "https://spark-api-open.xf-yun.com/agent/v1/chat/completions"
    assert calls["json"]["tool_choice"] == {"type": "function", "name": "securehub_emit_json"}


def test_x2_projects_complex_schema_and_uses_a_semantic_tool_name(monkeypatch):
    provider, _calls = _provider(monkeypatch, _FakeResponse())

    payload = provider._build_payload(
        [LLMMessage(role="user", content="ping")],
        stream=False,
        temperature=0.2,
        max_tokens=8,
        response_format={"type": "json_object"},
        response_schema=QualityCheckOutput.model_json_schema(),
    )

    function = payload["tools"][0]["function"]
    defect_schema = function["parameters"]["properties"]["defects"]["items"]
    assert function["name"] == "submit_quality_check"
    assert "$defs" not in function["parameters"]
    assert defect_schema["properties"]["code"]["enum"]


def test_x2_structured_payload_rewrites_direct_json_instruction(monkeypatch):
    provider, _calls = _provider(monkeypatch, _FakeResponse())

    payload = provider._build_payload(
        [LLMMessage(role="user", content="Return JSON matching:\n{\"answer\":{\"type\":\"string\"}}")],
        stream=False,
        temperature=0.2,
        max_tokens=8,
        response_format={"type": "json_object"},
        response_schema={"title": "RouteTutorQuestionOutput", "type": "object"},
    )

    user_message = next(message for message in payload["messages"] if message["role"] == "user")
    assert "Call submit_route_tutor_question using the function parameter schema supplied by the API." in user_message["content"]
    assert '{"answer":{"type":"string"}}' not in user_message["content"]


def test_x2_structured_payload_emphasises_top_level_string_fields(monkeypatch):
    provider, _calls = _provider(monkeypatch, _FakeResponse())

    payload = provider._build_payload(
        [LLMMessage(role="user", content="Return JSON matching:\n{}")],
        stream=False,
        temperature=0.2,
        max_tokens=8,
        response_format={"type": "json_object"},
        response_schema={
            "title": "GenerateLearningPathOutput",
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "nodes": {"type": "array"},
            },
        },
    )

    structured_system_message = next(
        message["content"]
        for message in payload["messages"]
        if message["role"] == "system" and "submit_generate_learning_path" in message["content"]
    )
    assert "content" in structured_system_message
    assert "plain JSON strings only" in structured_system_message


def test_x2_request_gate_is_scoped_to_one_endpoint_and_credential(monkeypatch):
    provider, _calls = _provider(monkeypatch, _FakeResponse())
    same_credential = xfyun_module.XunfeiSparkProvider(
        SimpleNamespace(
            XFYUN_API_KEY="test-api-password",
            XFYUN_BASE_URL="https://spark-api-open.xf-yun.com/agent/v1/",
            XFYUN_MODEL="spark-x",
            XFYUN_THINKING_MODE="disabled",
        )
    )
    other_credential = xfyun_module.XunfeiSparkProvider(
        SimpleNamespace(
            XFYUN_API_KEY="other-test-api-password",
            XFYUN_BASE_URL="https://spark-api-open.xf-yun.com/agent/v1/",
            XFYUN_MODEL="spark-x",
            XFYUN_THINKING_MODE="disabled",
        )
    )

    assert provider._x2_request_gate() is same_credential._x2_request_gate()
    assert provider._x2_request_gate() is not other_credential._x2_request_gate()


def test_x2_missing_forced_tool_arguments_is_not_treated_as_final_content(monkeypatch):
    provider, _calls = _provider(
        monkeypatch,
        _FakeResponse(body={"choices": [{"message": {"content": "ordinary response"}}]}),
    )

    async def call():
        await provider.generate(
            [LLMMessage(role="user", content="ping")],
            response_format={"type": "json_object"},
            response_schema={"title": "QualityCheckOutput", "type": "object"},
        )

    try:
        asyncio.run(call())
    except RuntimeError as exc:
        assert "structured-output tool arguments" in str(exc)
    else:  # pragma: no cover - a text fallback would bypass strict parsing.
        raise AssertionError("missing tool arguments unexpectedly became final content")


def test_x2_complete_direct_json_content_remains_strictly_usable(monkeypatch):
    provider, _calls = _provider(
        monkeypatch,
        _FakeResponse(body={"choices": [{"message": {"content": '{"answer":"ok"}'}}]}),
    )

    response = asyncio.run(
        provider.generate(
            [LLMMessage(role="user", content="ping")],
            response_format={"type": "json_object"},
            response_schema={"title": "QualityCheckOutput", "type": "object"},
        )
    )

    assert response.content == '{"answer":"ok"}'
    assert provider._strict_direct_json_object("prefix {\"answer\":\"ok\"}") == ""
    assert provider._strict_direct_json_object('["answer"]') == ""
