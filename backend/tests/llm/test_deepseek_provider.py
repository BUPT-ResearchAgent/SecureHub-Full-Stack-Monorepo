# Status: real

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import app.llm.deepseek_provider as deepseek_module
from app.llm.provider import LLMMessage
from app.runtime.exceptions import LLMProviderError


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

        async def post(self, *_args: object, **kwargs: object) -> _FakeResponse:
            calls.update(kwargs)
            return response

        def stream(self, *_args: object, **kwargs: object) -> _FakeStreamContext:
            calls.update(kwargs)
            return _FakeStreamContext(response)

    monkeypatch.setattr(deepseek_module.httpx, "AsyncClient", _FakeClient)
    provider = deepseek_module.DeepSeekProvider(
        SimpleNamespace(
            DEEPSEEK_API_KEY="test-only-redacted",
            DEEPSEEK_MODEL="deepseek-v4-pro",
            DEEPSEEK_BASE_URL="https://api.deepseek.com",
        )
    )
    return provider, calls


def test_generate_reads_message_content_and_forwards_response_format(monkeypatch):
    provider, calls = _provider(
        monkeypatch,
        _FakeResponse(
            body={
                "choices": [
                    {
                        "message": {
                            "content": '{"answer":true}',
                            "reasoning_content": "must never be used",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
            }
        ),
    )
    response = asyncio.run(
        provider.generate(
            [LLMMessage(role="user", content="test")],
            max_tokens=32,
            response_format={"type": "json_object"},
        )
    )
    assert response.content == '{"answer":true}'
    assert response.finish_reason == "stop"
    assert calls["json"]["response_format"] == {"type": "json_object"}


def test_generate_does_not_promote_reasoning_only_to_final_content(monkeypatch):
    provider, _calls = _provider(
        monkeypatch,
        _FakeResponse(
            body={
                "choices": [
                    {
                        "message": {"content": None, "reasoning_content": "private reasoning"},
                        "finish_reason": "stop",
                    }
                ]
            }
        ),
    )
    response = asyncio.run(provider.generate([LLMMessage(role="user", content="test")]))
    assert response.content == ""
    assert response.finish_reason == "stop"


def test_stream_aggregates_delta_content_and_preserves_finish_reason(monkeypatch):
    provider, calls = _provider(
        monkeypatch,
        _FakeResponse(
            lines=[
                'data: {"choices":[{"delta":{"reasoning_content":"private"}}]}',
                'data: {"choices":[{"delta":{"content":"{\\"answer\\":"}}]}',
                'data: {"choices":[{"delta":{"content":"true}"}}]}',
                'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
                "data: [DONE]",
            ]
        ),
    )

    async def collect():
        return [
            chunk
            async for chunk in provider.stream_generate(
                [LLMMessage(role="user", content="test")],
                response_format={"type": "json_object"},
            )
        ]

    chunks = asyncio.run(collect())
    assert "".join(chunk.content for chunk in chunks) == '{"answer":true}'
    assert chunks[-1].finish_reason == "stop"
    assert all("private" not in chunk.content for chunk in chunks)
    assert calls["json"]["response_format"] == {"type": "json_object"}


def test_stream_reasoning_only_yields_no_final_content_but_keeps_finish_reason(monkeypatch):
    provider, _calls = _provider(
        monkeypatch,
        _FakeResponse(
            lines=[
                'data: {"choices":[{"delta":{"reasoning_content":"private"}}]}',
                'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
                "data: [DONE]",
            ]
        ),
    )

    async def collect():
        return [chunk async for chunk in provider.stream_generate([])]

    chunks = asyncio.run(collect())
    assert chunks == [chunks[0]]
    assert chunks[0].content == ""
    assert chunks[0].finish_reason == "stop"


def test_stream_malformed_sse_json_is_a_provider_error(monkeypatch):
    provider, _calls = _provider(
        monkeypatch,
        _FakeResponse(lines=["data: {not-json}", "data: [DONE]"]),
    )

    async def collect():
        return [chunk async for chunk in provider.stream_generate([])]

    with pytest.raises(LLMProviderError, match="deepseek"):
        asyncio.run(collect())
