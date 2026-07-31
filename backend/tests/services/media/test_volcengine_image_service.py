# Status: real

from __future__ import annotations

import json
from uuid import UUID

import httpx
import pytest

from app.core.config import Settings
from app.services.media.volcengine_image_service import (
    MediaConfigurationError,
    MediaProviderError,
    VolcengineImageService,
)
from app.services.media.websec_visual_prompts import (
    WEBSEC_VISUAL_PROMPTS,
    get_websec_visual_prompt,
)


_PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
)
_USER_ID = UUID("11111111-1111-4111-8111-111111111111")


class _MemoryStorage:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def put_bytes(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "VOLCENGINE_IMAGE_API_KEY": "ark-unit-test-key",
        "VOLCENGINE_IMAGE_MODEL": "doubao-seedream-5.0-lite",
        "VOLCENGINE_IMAGE_BASE_URL": "https://ark.cn-beijing.volces.com/api/plan/v3",
        "VOLCENGINE_IMAGE_MAX_BYTES": 1024 * 1024,
    }
    values.update(overrides)
    return Settings(**values)


def test_websec_prompt_library_covers_all_knowledge_points() -> None:
    assert set(WEBSEC_VISUAL_PROMPTS) == {
        "http-basics",
        "same-origin",
        "cookie-session",
        "sql-injection",
        "sql-injection-blind",
        "xss-reflected",
        "xss-stored",
        "xss-dom",
        "csrf",
        "file-upload",
        "ssrf",
        "deserialization",
        "rce",
        "auth-bypass",
        "waf-bypass",
        "secure-coding",
        "owasp-top10",
    }
    assert len(WEBSEC_VISUAL_PROMPTS) == 17
    rendered = get_websec_visual_prompt("sql-injection").render()
    assert "参数绑定" in rendered
    assert "16:9" in rendered


@pytest.mark.anyio
async def test_generate_downloads_and_persists_provider_image() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST":
            return httpx.Response(
                200,
                json={"data": [{"url": "https://cdn.volcengine.example/image.png"}]},
            )
        return httpx.Response(
            200,
            content=_PNG_1X1,
            headers={"content-type": "image/png"},
        )

    storage = _MemoryStorage()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        asset = await VolcengineImageService(
            settings=_settings(),
            storage=storage,
            client=client,
        ).generate(
            user_id=_USER_ID,
            kp_id="sql-injection",
            size="1024x1024",
        )

    assert [request.method for request in requests] == ["POST", "GET"]
    provider_request = requests[0]
    assert str(provider_request.url) == (
        "https://ark.cn-beijing.volces.com/api/plan/v3/images/generations"
    )
    provider_payload = json.loads(provider_request.content)
    assert provider_payload["model"] == "doubao-seedream-5.0-lite"
    assert provider_payload["size"] == "2K"
    assert provider_payload["sequential_image_generation"] == "disabled"
    assert provider_payload["output_format"] == "png"
    assert provider_payload["response_format"] == "url"
    assert provider_payload["watermark"] is False
    assert asset.provider == "volcengine-ark"
    assert asset.media_type == "image/png"
    assert asset.object_key.startswith(
        f"media/generated/images/{_USER_ID}/sql-injection/"
    )
    assert storage.calls[0]["content"] == _PNG_1X1
    assert storage.calls[0]["mime_type"] == "image/png"
    metadata = storage.calls[0]["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["source"] == "live"
    assert "prompt_sha256" in metadata


@pytest.mark.anyio
async def test_generate_fails_closed_without_api_key() -> None:
    storage = _MemoryStorage()
    service = VolcengineImageService(
        settings=_settings(VOLCENGINE_IMAGE_API_KEY=""),
        storage=storage,
    )
    with pytest.raises(MediaConfigurationError, match="API Key"):
        await service.generate(user_id=_USER_ID, kp_id="csrf")
    assert storage.calls == []


@pytest.mark.anyio
async def test_generate_rejects_private_download_address() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": [{"url": "https://127.0.0.1/internal.png"}]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = VolcengineImageService(
            settings=_settings(),
            storage=_MemoryStorage(),
            client=client,
        )
        with pytest.raises(MediaProviderError, match="不允许的网络"):
            await service.generate(user_id=_USER_ID, kp_id="ssrf")
