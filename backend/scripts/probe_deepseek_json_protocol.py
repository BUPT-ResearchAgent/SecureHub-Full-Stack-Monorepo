# Status: real

"""One opt-in, minimal DeepSeek streaming JSON protocol diagnostic."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.llm.provider import LLMMessage, get_llm_provider


MAX_DIAGNOSTIC_TOKENS = 128
EXPECTED_PROVIDER = "deepseek"
EXPECTED_MODEL = "deepseek-v4-pro"


def validate_confirmation(confirm_live: bool) -> None:
    if not confirm_live:
        raise ValueError("pass --confirm-live; no request was sent")


def classify_json(content: str) -> str:
    if not isinstance(content, str) or not content.strip():
        return "no_final_content"
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        return "invalid_json"
    return "json_object" if isinstance(value, dict) else "non_object_json"


async def run_probe() -> dict[str, Any]:
    provider = get_llm_provider("deepseek")
    if (
        provider.provider_name != EXPECTED_PROVIDER
        or provider.model_name != EXPECTED_MODEL
    ):
        return {
            "ok": False,
            "error_code": "PROTOCOL_IDENTITY_INVALID",
            "provider": provider.provider_name,
            "model": provider.model_name,
        }
    parts: list[str] = []
    finish_reason: str | None = None
    chunk_count = 0
    try:
        async for chunk in provider.stream_generate(
            [LLMMessage(role="user", content="Return exactly one JSON object: {}")],
            temperature=0.0,
            max_tokens=MAX_DIAGNOSTIC_TOKENS,
            response_format={"type": "json_object"},
        ):
            chunk_count += 1
            if chunk.content:
                parts.append(chunk.content)
            if chunk.finish_reason is not None:
                finish_reason = chunk.finish_reason
    except Exception:
        return {
            "ok": False,
            "error_code": "PROTOCOL_REQUEST_FAILED",
            "provider": EXPECTED_PROVIDER,
            "model": EXPECTED_MODEL,
        }

    content = "".join(parts)
    parse_category = classify_json(content)
    result = {
        "ok": parse_category == "json_object" and finish_reason == "stop",
        "provider": EXPECTED_PROVIDER,
        "model": EXPECTED_MODEL,
        "stream": True,
        "max_tokens": MAX_DIAGNOSTIC_TOKENS,
        "chunk_count": chunk_count,
        "finish_reason": finish_reason or "unknown",
        "final_content_length": len(content),
        "has_final_content": bool(content.strip()),
        "parse_category": parse_category,
    }
    if not result["ok"]:
        result["error_code"] = "PROTOCOL_FINAL_CONTENT_INVALID"
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Opt-in DeepSeek JSON stream probe")
    parser.add_argument("--confirm-live", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        validate_confirmation(args.confirm_live)
    except ValueError:
        print(json.dumps({"ok": False, "error_code": "LIVE_CONFIRMATION_REQUIRED"}))
        return 1
    result = asyncio.run(run_probe())
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
