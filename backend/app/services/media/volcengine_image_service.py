# Status: real

"""Volcengine Ark image generation with bounded download and durable storage."""

from __future__ import annotations

import base64
import binascii
import ipaddress
from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol
from urllib.parse import urljoin, urlparse
from uuid import UUID, uuid4

import httpx

from app.core.config import Settings
from app.services.media.websec_visual_prompts import get_websec_visual_prompt


_ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
_REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}


class MediaStorage(Protocol):
    async def put_bytes(
        self,
        *,
        object_key: str,
        content: bytes,
        mime_type: str | None = None,
        original_filename: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None: ...


class MediaConfigurationError(RuntimeError):
    """The image provider cannot be called with the current configuration."""


class MediaProviderError(RuntimeError):
    """The provider or returned media failed a safe, recoverable boundary."""


@dataclass(frozen=True)
class GeneratedImageAsset:
    kp_id: str
    prompt_used: str
    model: str
    provider: str
    object_key: str
    asset_filename: str
    media_type: str
    byte_size: int


class VolcengineImageService:
    def __init__(
        self,
        *,
        settings: Settings,
        storage: MediaStorage,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self.storage = storage
        self._client = client

    async def generate(
        self,
        *,
        user_id: UUID,
        kp_id: str,
        custom_prompt: str | None = None,
        visualization_type: str | None = None,
        size: str = "1024x1024",
    ) -> GeneratedImageAsset:
        api_key = self.settings.VOLCENGINE_IMAGE_API_KEY.strip()
        model = self.settings.VOLCENGINE_IMAGE_MODEL.strip()
        if not api_key or api_key == "__FILL_ME__":
            raise MediaConfigurationError("图像生成服务尚未配置有效 API Key。")
        if not model or model == "__FILL_ME__":
            raise MediaConfigurationError("图像生成服务尚未配置模型 ID。")

        visual_prompt = get_websec_visual_prompt(kp_id)
        prompt_used = visual_prompt.render(
            custom_prompt=custom_prompt,
            visualization_type=visualization_type,
        )
        client = self._client or httpx.AsyncClient(
            timeout=httpx.Timeout(self.settings.VOLCENGINE_IMAGE_TIMEOUT_SECONDS),
            follow_redirects=False,
        )
        owns_client = self._client is None
        try:
            image_bytes, media_type = await self._request_image(
                client,
                api_key=api_key,
                model=model,
                prompt=prompt_used,
                size=size,
            )
        finally:
            if owns_client:
                await client.aclose()

        extension = _ALLOWED_IMAGE_MIME_TYPES[media_type]
        asset_filename = f"{uuid4()}.{extension}"
        object_key = (
            f"media/generated/images/{user_id}/{visual_prompt.kp_id}/{asset_filename}"
        )
        await self.storage.put_bytes(
            object_key=object_key,
            content=image_bytes,
            mime_type=media_type,
            original_filename=f"{visual_prompt.kp_id}-{asset_filename}",
            metadata={
                "asset_type": "educational_image",
                "course_code": "WEBSEC-101",
                "kp_id": visual_prompt.kp_id,
                "user_id": str(user_id),
                "provider": "volcengine-ark",
                "model": model,
                "source": "live",
                "prompt_sha256": sha256(prompt_used.encode("utf-8")).hexdigest(),
            },
        )
        return GeneratedImageAsset(
            kp_id=visual_prompt.kp_id,
            prompt_used=prompt_used,
            model=model,
            provider="volcengine-ark",
            object_key=object_key,
            asset_filename=asset_filename,
            media_type=media_type,
            byte_size=len(image_bytes),
        )

    async def _request_image(
        self,
        client: httpx.AsyncClient,
        *,
        api_key: str,
        model: str,
        prompt: str,
        size: str,
    ) -> tuple[bytes, str]:
        endpoint = f"{self.settings.VOLCENGINE_IMAGE_BASE_URL}/images/generations"
        try:
            response = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "prompt": prompt,
                    "size": size,
                    "sequential_image_generation": "disabled",
                    "response_format": "url",
                    "watermark": False,
                },
            )
        except httpx.TimeoutException as exc:
            raise MediaProviderError("图像生成服务响应超时，请稍后重试。") from exc
        except httpx.HTTPError as exc:
            raise MediaProviderError("无法连接图像生成服务，请稍后重试。") from exc

        if response.status_code == 401:
            raise MediaConfigurationError("图像生成凭据已失效或无权访问当前模型。")
        if response.status_code == 429:
            raise MediaProviderError("图像生成服务当前请求过多，请稍后重试。")
        if not response.is_success:
            raise MediaProviderError(_safe_provider_error(response))

        try:
            payload = response.json()
        except ValueError as exc:
            raise MediaProviderError("图像生成服务返回了无法解析的响应。") from exc
        data = payload.get("data") if isinstance(payload, dict) else None
        item = data[0] if isinstance(data, list) and data and isinstance(data[0], dict) else None
        if item is None:
            raise MediaProviderError("图像生成服务没有返回可用图片。")

        encoded = item.get("b64_json")
        if isinstance(encoded, str) and encoded.strip():
            try:
                content = base64.b64decode(encoded, validate=True)
            except (ValueError, binascii.Error) as exc:
                raise MediaProviderError("图像生成服务返回了损坏的图片数据。") from exc
            return _validate_image(content, None, self.settings.VOLCENGINE_IMAGE_MAX_BYTES)

        image_url = item.get("url")
        if not isinstance(image_url, str) or not image_url.strip():
            raise MediaProviderError("图像生成服务没有返回图片下载地址。")
        return await self._download_image(client, image_url.strip())

    async def _download_image(
        self,
        client: httpx.AsyncClient,
        image_url: str,
    ) -> tuple[bytes, str]:
        current_url = image_url
        for _redirect_count in range(4):
            _assert_public_https_url(current_url)
            try:
                async with client.stream("GET", current_url, follow_redirects=False) as response:
                    if response.status_code in _REDIRECT_STATUS_CODES:
                        location = response.headers.get("location")
                        if not location:
                            raise MediaProviderError("图片下载重定向缺少目标地址。")
                        current_url = urljoin(current_url, location)
                        continue
                    if not response.is_success:
                        raise MediaProviderError("生成成功，但图片下载失败，请稍后重试。")
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > self.settings.VOLCENGINE_IMAGE_MAX_BYTES:
                        raise MediaProviderError("生成图片超过允许的文件大小。")
                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > self.settings.VOLCENGINE_IMAGE_MAX_BYTES:
                            raise MediaProviderError("生成图片超过允许的文件大小。")
                        chunks.append(chunk)
                    return _validate_image(
                        b"".join(chunks),
                        response.headers.get("content-type"),
                        self.settings.VOLCENGINE_IMAGE_MAX_BYTES,
                    )
            except httpx.TimeoutException as exc:
                raise MediaProviderError("图片下载超时，请稍后重试。") from exc
            except httpx.HTTPError as exc:
                raise MediaProviderError("图片下载失败，请稍后重试。") from exc
            except ValueError as exc:
                raise MediaProviderError("图片下载响应包含无效的文件大小。") from exc
        raise MediaProviderError("图片下载重定向次数过多。")


def _safe_provider_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None
    error = payload.get("error") if isinstance(payload, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    if isinstance(code, str) and code:
        return f"图像生成服务暂不可用（{code}）。"
    return f"图像生成服务暂不可用（HTTP {response.status_code}）。"


def _assert_public_https_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise MediaProviderError("图片下载地址不是受支持的 HTTPS 地址。")
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".local"):
        raise MediaProviderError("图片下载地址指向了不允许的主机。")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return
    if not address.is_global:
        raise MediaProviderError("图片下载地址指向了不允许的网络。")


def _validate_image(
    content: bytes,
    declared_content_type: str | None,
    max_bytes: int,
) -> tuple[bytes, str]:
    if not content:
        raise MediaProviderError("图像生成服务返回了空文件。")
    if len(content) > max_bytes:
        raise MediaProviderError("生成图片超过允许的文件大小。")
    detected = _detect_image_mime_type(content)
    if detected is None:
        raise MediaProviderError("图像生成服务返回了不支持的文件类型。")
    declared = (declared_content_type or "").split(";", 1)[0].strip().lower()
    if declared and declared.startswith("image/") and declared not in _ALLOWED_IMAGE_MIME_TYPES:
        raise MediaProviderError("图像生成服务返回了不支持的媒体类型。")
    return content, detected


def _detect_image_mime_type(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


__all__ = [
    "GeneratedImageAsset",
    "MediaConfigurationError",
    "MediaProviderError",
    "VolcengineImageService",
]
