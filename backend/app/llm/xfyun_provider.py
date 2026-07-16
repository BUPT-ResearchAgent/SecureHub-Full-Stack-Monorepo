# Status: real

"""XunfeiSparkProvider — BaseLLMProvider 实现。

读取 XFYUN_API_KEY，调用讯飞星火 OpenAI 兼容 API。
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.llm.provider import (
    BaseLLMProvider,
    HealthStatus,
    LLMChunk,
    LLMMessage,
    LLMResponse,
    TokenUsage,
)

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://spark-api-open.xf-yun.com/v1"
_DEFAULT_MODEL = "spark-v4"
_STRUCTURED_OUTPUT_TOOL_NAME = "securehub_emit_json"
_X2_REQUEST_GATES: dict[str, asyncio.Lock] = {}


class XunfeiSparkProvider(BaseLLMProvider):
    """讯飞星火 OpenAI-compatible provider (spark-api-open)."""

    provider_name = "xfyun"

    def __init__(
        self,
        settings: Any | None = None,
        *,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        from app.core.config import get_settings

        cfg = settings or get_settings()
        # The value can be a user credential resolved for one durable root;
        # never write it back to Settings.
        self.api_key: str = cfg.XFYUN_API_KEY if api_key is None else api_key
        self.base_url: str = getattr(cfg, "XFYUN_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")
        self.model_name = model or getattr(cfg, "XFYUN_MODEL", _DEFAULT_MODEL)
        self.thinking_mode = str(getattr(cfg, "XFYUN_THINKING_MODE", "") or "").strip().lower()
        self.timeout = httpx.Timeout(60.0, read=120.0)
        self.retry = 1

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        messages: list[LLMMessage],
        *,
        stream: bool,
        temperature: float,
        max_tokens: int | None,
        response_format: dict[str, str] | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        serialized_messages = [message.model_dump() for message in messages]
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": serialized_messages,
            "stream": stream,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        thinking_mode = self.thinking_mode
        if response_format is not None and not thinking_mode and self.base_url.endswith("/agent/v1"):
            # Spark X2 documents ``thinking`` but not OpenAI's
            # ``response_format``. A strict-JSON request must reserve the
            # output budget for final content rather than private reasoning.
            thinking_mode = "disabled"
        if thinking_mode:
            payload["thinking"] = {"type": thinking_mode}
        if response_schema is not None and self._uses_x2_agent_api:
            # Spark X2 does not document OpenAI ``response_format``. Its
            # documented forced function calling returns valid JSON through
            # ``tool_calls[].function.arguments`` instead.
            tool_name = self._structured_tool_name(response_schema)
            string_fields = self._top_level_string_fields(response_schema)
            string_field_instruction = (
                " For top-level string fields "
                f"({', '.join(string_fields)}), provide plain JSON strings only; never use an object, array, or null. "
                "If an optional field has no suitable string value, omit it."
                if string_fields
                else ""
            )
            for message in serialized_messages:
                if message["role"] == "user" and isinstance(message.get("content"), str):
                    content = message["content"]
                    marker = "Return JSON matching:"
                    if marker in content:
                        content = content.split(marker, 1)[0].rstrip()
                    message["content"] = (
                        f"{content}\n\nCall {tool_name} using the function parameter schema supplied by the API."
                    )
            insertion_index = 0
            while insertion_index < len(serialized_messages) and serialized_messages[insertion_index]["role"] == "system":
                insertion_index += 1
            serialized_messages.insert(
                insertion_index,
                {
                    "role": "system",
                    "content": (
                        f"You must call {tool_name} to return the result. Do not answer in normal assistant content. "
                        "The user's JSON-format request must be satisfied by the function arguments. "
                        "Put the output only in those arguments and obey its parameter schema."
                        f"{string_field_instruction}"
                    ),
                },
            )
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": f"Submit the {tool_name.removeprefix('submit_')} structured result.",
                        "parameters": self._provider_tool_schema(response_schema),
                    },
                }
            ]
            payload["tool_choice"] = {"type": "function", "name": tool_name}
        return payload

    @staticmethod
    def _tool_arguments(value: Any, expected_tool_name: str) -> str:
        """Return only arguments from the one forced structured-output tool."""
        if not isinstance(value, dict):
            return ""
        tool_calls = value.get("tool_calls")
        if not isinstance(tool_calls, list):
            return ""
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            function = tool_call.get("function")
            if not isinstance(function, dict) or function.get("name") != expected_tool_name:
                continue
            arguments = function.get("arguments")
            return arguments if isinstance(arguments, str) else ""
        return ""

    @staticmethod
    def _strict_direct_json_object(value: Any) -> str:
        """Accept only a complete JSON object when X2 ignores forced tools.

        Some Spark X2 responses honor the JSON instruction but omit
        ``tool_calls`` despite a forced function choice.  This is deliberately
        narrower than accepting assistant prose: the value must itself be one
        JSON object.  ``SkillExecutor`` still applies the full server-owned
        Pydantic schema before anything becomes a candidate output.
        """
        if not isinstance(value, str):
            return ""
        candidate = value.strip()
        if not candidate.startswith("{") or not candidate.endswith("}"):
            return ""
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            return ""
        return candidate if isinstance(parsed, dict) else ""

    @property
    def _uses_x2_agent_api(self) -> bool:
        return self.base_url.endswith("/agent/v1")

    def _x2_request_gate(self) -> asyncio.Lock:
        """Serialize one credential's X2 calls to respect its single-flow gate.

        Spark X2 reports error 10007 when a new request is sent before the
        current response has finished.  The gate is scoped by a one-way digest
        of endpoint and credential, so separate users/accounts do not block
        each other and no secret is retained as a dictionary key.
        """
        scope = hashlib.sha256(f"{self.base_url}\0{self.api_key}".encode("utf-8")).hexdigest()
        return _X2_REQUEST_GATES.setdefault(scope, asyncio.Lock())

    @staticmethod
    def _structured_tool_name(response_schema: dict[str, Any]) -> str:
        title = str(response_schema.get("title") or "").removesuffix("Output")
        snake_case = re.sub(r"(?<!^)(?=[A-Z])", "_", title).lower()
        snake_case = re.sub(r"[^a-z0-9_]+", "_", snake_case).strip("_")
        return f"submit_{snake_case}" if snake_case else _STRUCTURED_OUTPUT_TOOL_NAME

    @staticmethod
    def _top_level_string_fields(response_schema: dict[str, Any]) -> tuple[str, ...]:
        """Return server-schema field names that require a literal JSON string."""
        properties = response_schema.get("properties")
        if not isinstance(properties, dict):
            return ()
        return tuple(
            str(name)
            for name, schema in properties.items()
            if isinstance(schema, dict) and schema.get("type") == "string"
        )

    @classmethod
    def _provider_tool_schema(cls, response_schema: dict[str, Any]) -> dict[str, Any]:
        """Project Pydantic JSON Schema to Spark X2's function-schema subset.

        The final output still goes through the complete original Pydantic
        schema in ``SkillExecutor``. This projection only removes unsupported
        metadata and inlines local references so Spark can produce tool
        arguments for nested output models such as ``QualityCheck``.
        """
        schema = copy.deepcopy(response_schema)
        definitions = schema.pop("$defs", {})
        return cls._project_tool_schema(schema, definitions)

    @classmethod
    def _project_tool_schema(cls, value: Any, definitions: dict[str, Any]) -> Any:
        if isinstance(value, list):
            return [cls._project_tool_schema(item, definitions) for item in value]
        if not isinstance(value, dict):
            return value

        reference = value.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/$defs/"):
            target = definitions.get(reference.removeprefix("#/$defs/"))
            if isinstance(target, dict):
                merged = {
                    **target,
                    **{key: item for key, item in value.items() if key != "$ref"},
                }
                return cls._project_tool_schema(merged, definitions)

        union = value.get("anyOf") or value.get("oneOf")
        if isinstance(union, list):
            selected = next(
                (
                    item
                    for item in union
                    if isinstance(item, dict) and item.get("type") not in {None, "null"}
                ),
                None,
            )
            if isinstance(selected, dict):
                merged = {
                    **selected,
                    **{
                        key: item
                        for key, item in value.items()
                        if key not in {"anyOf", "oneOf", "allOf", "$ref", "title", "default", "examples"}
                    },
                }
                return cls._project_tool_schema(merged, definitions)

        result: dict[str, Any] = {}
        for key in (
            "type",
            "enum",
            "description",
            "required",
            "minItems",
            "maxItems",
            "minimum",
            "maximum",
            "minLength",
            "maxLength",
            "pattern",
        ):
            if key in value:
                result[key] = cls._project_tool_schema(value[key], definitions)
        if isinstance(value.get("properties"), dict):
            result["properties"] = {
                name: cls._project_tool_schema(item, definitions)
                for name, item in value["properties"].items()
            }
            result.setdefault("type", "object")
        if "items" in value:
            result["items"] = cls._project_tool_schema(value["items"], definitions)
            result.setdefault("type", "array")
        return result

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> LLMResponse:
        payload = self._build_payload(
            messages,
            stream=False,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            response_schema=response_schema,
        )
        async def request_completion() -> dict[str, Any]:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers,
                    json=payload,
                )
                resp.raise_for_status()
                response_body = resp.json()

            return response_body if isinstance(response_body, dict) else {}

        try:
            if self._uses_x2_agent_api:
                async with self._x2_request_gate():
                    body = await request_completion()
            else:
                body = await request_completion()
        except httpx.HTTPStatusError as exc:
            raise self.map_error(exc, exc.response.status_code) from exc
        except httpx.TimeoutException as exc:
            raise self.map_error(exc) from exc

        raw_choice = (body.get("choices") or [{}])[0] if isinstance(body, dict) else {}
        choice = raw_choice if isinstance(raw_choice, dict) else {}
        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        expected_tool_name = self._structured_tool_name(response_schema) if response_schema and self._uses_x2_agent_api else None
        if expected_tool_name is not None:
            content = self._tool_arguments(message, expected_tool_name)
            if not content:
                content = self._strict_direct_json_object(message.get("content"))
            if not content:
                raise RuntimeError("Spark X2 did not return structured-output tool arguments or a strict direct JSON object")
        else:
            content = message.get("content", "")
        if not isinstance(content, str):
            content = ""
        usage_raw = body.get("usage", {}) if isinstance(body, dict) else {}
        if not isinstance(usage_raw, dict):
            usage_raw = {}
        return LLMResponse(
            content=content,
            usage=TokenUsage(
                prompt_tokens=usage_raw.get("prompt_tokens", 0),
                completion_tokens=usage_raw.get("completion_tokens", 0),
                total_tokens=usage_raw.get("total_tokens", 0),
            ),
            provider=self.provider_name,
            model=self.model_name,
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def stream_generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> AsyncIterator[LLMChunk]:
        if response_schema is not None and self._uses_x2_agent_api:
            # Spark X2 streams ordinary content even when forced function
            # calling is requested. The non-stream response reliably exposes
            # the schema-constrained tool arguments, so surface that one
            # complete final JSON chunk to the Runtime instead of accepting
            # malformed streamed prose as a strict candidate.
            response = await self.generate(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
                response_schema=response_schema,
            )
            if response.content:
                yield LLMChunk(content=response.content, index=0, finish_reason=response.finish_reason)
            return
        payload = self._build_payload(
            messages,
            stream=True,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            response_schema=response_schema,
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    index = 0
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data = line[len("data: "):].strip()
                        if data == "[DONE]":
                            return
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        raw_choice = (chunk.get("choices") or [{}])[0] if isinstance(chunk, dict) else {}
                        choice = raw_choice if isinstance(raw_choice, dict) else {}
                        delta = choice.get("delta") if isinstance(choice.get("delta"), dict) else {}
                        content = ""
                        if response_schema is not None and self._uses_x2_agent_api:
                            tool_calls = delta.get("tool_calls")
                            if isinstance(tool_calls, list):
                                for tool_call in tool_calls:
                                    if not isinstance(tool_call, dict):
                                        continue
                                    function = tool_call.get("function")
                                    if not isinstance(function, dict):
                                        continue
                                    arguments = function.get("arguments")
                                    if isinstance(arguments, str):
                                        content += arguments
                        else:
                            value = delta.get("content")
                            content = value if isinstance(value, str) else ""
                        if content:
                            yield LLMChunk(content=content, index=index)
                            index += 1
        except httpx.HTTPStatusError as exc:
            raise self.map_error(exc, exc.response.status_code) from exc

    async def health_check(self) -> HealthStatus:
        if not self.api_key:
            return HealthStatus(
                provider=self.provider_name,
                model=self.model_name,
                mode="fixture",
                live_enabled=False,
                status="error",
                last_error="XFYUN_API_KEY not set",
            )
        try:
            await self.generate(
                [LLMMessage(role="user", content="ping")],
                max_tokens=1,
            )
            return HealthStatus(
                provider=self.provider_name,
                model=self.model_name,
                mode="real",
                live_enabled=True,
                status="available",
            )
        except Exception as exc:
            return HealthStatus(
                provider=self.provider_name,
                model=self.model_name,
                mode="real",
                live_enabled=True,
                status="error",
                last_error=str(exc),
            )
