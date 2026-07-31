# Status: real

"""Durable, user-scoped Wuyinkeji video generation infrastructure."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Literal, Protocol
from urllib.parse import urljoin, urlparse
from uuid import UUID, uuid4
from weakref import WeakValueDictionary

import httpx

from app.core.config import Settings
from app.services.media.volcengine_image_service import (
    MediaConfigurationError,
    MediaProviderError,
)
from app.services.media.websec_visual_prompts import get_websec_visual_prompt


VideoTaskState = Literal["pending", "processing", "completed", "failed"]
_ALLOWED_VIDEO_MIME_TYPES = {
    "video/mp4": "mp4",
    "video/webm": "webm",
}
_REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}
_MAX_REDIRECTS = 3
_TASK_VERSION = 1
_PROVIDER_SUCCESS_CODES = {0, 200}
_task_locks: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()


def _task_lock(lock_key: str) -> asyncio.Lock:
    """Return one process-local lock while allowing idle task locks to be collected."""

    lock = _task_locks.get(lock_key)
    if lock is None:
        # There is no await between lookup and registration, so competing tasks on
        # the same event loop cannot observe two registered locks for this key.
        lock = asyncio.Lock()
        _task_locks[lock_key] = lock
    return lock


class VideoStorage(Protocol):
    async def put_bytes(
        self,
        *,
        object_key: str,
        content: bytes,
        mime_type: str | None = None,
        original_filename: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None: ...

    async def get_bytes(self, object_key: str) -> bytes | None: ...


class VideoTaskNotFoundError(LookupError):
    """The user-scoped local task or asset index does not exist."""


@dataclass(frozen=True)
class GeneratedVideoAsset:
    object_key: str
    asset_filename: str
    media_type: str
    byte_size: int
    duration: str
    size: str
    prompt: str
    model: str
    provider: str
    task_id: str
    kp_id: str | None


@dataclass
class VideoTaskRecord:
    version: int
    task_id: str
    upstream_task_id: str
    user_id: str
    prompt: str
    kp_id: str | None
    size: str
    duration: str
    provider: str
    model: str
    status: VideoTaskState
    poll_attempts: int
    created_at: str
    updated_at: str
    deadline_at: str
    asset_id: str
    object_key: str | None = None
    asset_filename: str | None = None
    media_type: str | None = None
    byte_size: int | None = None
    error_message: str | None = None

    @classmethod
    def from_bytes(cls, content: bytes) -> VideoTaskRecord:
        try:
            payload = json.loads(content)
            if not isinstance(payload, dict):
                raise ValueError
            record = cls(**payload)
        except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MediaProviderError("视频任务记录损坏，无法继续查询。") from exc
        if record.version != _TASK_VERSION:
            raise MediaProviderError("视频任务记录版本不受支持。")
        return record


class WuyinkejiVideoService:
    """Submit provider tasks and safely materialize completed videos."""

    def __init__(
        self,
        *,
        settings: Settings,
        storage: VideoStorage,
        client: httpx.AsyncClient | None = None,
        resolver: Callable[[str], Awaitable[list[str]]] | None = None,
    ) -> None:
        self.settings = settings
        self.storage = storage
        self._client = client
        self._resolver = resolver or _resolve_host_addresses

    async def submit(
        self,
        *,
        user_id: UUID,
        prompt: str,
        kp_id: str | None = None,
        size: str | None = None,
        duration: str | None = None,
        reference_image_url: str | None = None,
    ) -> VideoTaskRecord:
        api_key, model = self._provider_configuration()
        normalized_kp_id = self._normalize_kp_id(kp_id)
        normalized_size = size or self.settings.WUYINKEJI_VIDEO_DEFAULT_SIZE
        normalized_duration = duration or self.settings.WUYINKEJI_VIDEO_DEFAULT_DURATION
        if reference_image_url:
            await _assert_public_https_url(reference_image_url, self._resolver)

        client = self._client or self._new_client()
        owns_client = self._client is None
        try:
            upstream_task_id = await self._submit_upstream(
                client,
                api_key=api_key,
                model=model,
                prompt=prompt,
                size=normalized_size,
                duration=normalized_duration,
                reference_image_url=reference_image_url,
            )
        finally:
            if owns_client:
                await client.aclose()

        now = datetime.now(UTC)
        local_task_id = str(uuid4())
        record = VideoTaskRecord(
            version=_TASK_VERSION,
            task_id=local_task_id,
            upstream_task_id=upstream_task_id,
            user_id=str(user_id),
            prompt=prompt,
            kp_id=normalized_kp_id,
            size=normalized_size,
            duration=normalized_duration,
            provider="wuyinkeji-omni",
            model=model,
            status="pending",
            poll_attempts=0,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            deadline_at=(
                now
                + timedelta(
                    seconds=(
                        self.settings.WUYINKEJI_VIDEO_POLL_INTERVAL_SECONDS
                        * self.settings.WUYINKEJI_VIDEO_MAX_POLL_ATTEMPTS
                    ),
                )
            ).isoformat(),
            asset_id=str(uuid4()),
        )
        await self._save_task(record)
        return record

    async def poll(self, *, user_id: UUID, task_id: str) -> VideoTaskRecord:
        normalized_task_id = _normalize_uuid(task_id)
        lock_key = f"{user_id}:{normalized_task_id}"
        lock = _task_lock(lock_key)
        async with lock:
            record = await self._load_task(user_id=user_id, task_id=normalized_task_id)
            if record.status in {"completed", "failed"}:
                return record
            if record.user_id != str(user_id) or record.task_id != normalized_task_id:
                raise VideoTaskNotFoundError

            if self._task_expired(record):
                record.status = "failed"
                record.error_message = "视频生成等待超时，请重新提交。"
                record.updated_at = datetime.now(UTC).isoformat()
                await self._save_task(record)
                return record

            api_key, _model = self._provider_configuration()
            client = self._client or self._new_client()
            owns_client = self._client is None
            try:
                upstream_status, message = await self._query_upstream(
                    client,
                    api_key=api_key,
                    upstream_task_id=record.upstream_task_id,
                )
                record.poll_attempts += 1
                record.updated_at = datetime.now(UTC).isoformat()
                if upstream_status == 0:
                    record.status = "pending"
                elif upstream_status == 1:
                    record.status = "processing"
                elif upstream_status == 3:
                    record.status = "failed"
                    record.error_message = (
                        "上游已接收任务但未产出视频，且未返回失败详情。"
                        "请检查服务余额、点数及模型状态，或稍后修改描述再试。"
                    )
                elif upstream_status == 2:
                    asset = await self._materialize_completed_video(
                        client,
                        record=record,
                        download_url=message,
                    )
                    record.status = "completed"
                    record.object_key = asset.object_key
                    record.asset_filename = asset.asset_filename
                    record.media_type = asset.media_type
                    record.byte_size = asset.byte_size
                    record.error_message = None
                else:
                    raise MediaProviderError("视频生成服务返回了未知任务状态。")
                await self._save_task(record)
                return record
            finally:
                if owns_client:
                    await client.aclose()

    async def get_task(self, *, user_id: UUID, task_id: str) -> VideoTaskRecord:
        return await self._load_task(
            user_id=user_id,
            task_id=_normalize_uuid(task_id),
        )

    async def get_asset_object_key(
        self,
        *,
        user_id: UUID,
        asset_filename: str,
    ) -> str:
        normalized_filename = _normalize_asset_filename(asset_filename)
        index_key = self.asset_index_key(user_id, normalized_filename)
        content = await self.storage.get_bytes(index_key)
        if content is None:
            raise VideoTaskNotFoundError
        try:
            payload = json.loads(content)
            task_id = _normalize_uuid(payload["task_id"])
            object_key = str(payload["object_key"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise VideoTaskNotFoundError from exc
        expected_prefix = f"media/generated/videos/{user_id}/"
        if (
            not object_key.startswith(expected_prefix)
            or not object_key.endswith(f"/{normalized_filename}")
        ):
            raise VideoTaskNotFoundError
        record = await self._load_task(user_id=user_id, task_id=task_id)
        if (
            record.status != "completed"
            or record.object_key != object_key
            or record.asset_filename != normalized_filename
        ):
            raise VideoTaskNotFoundError
        return object_key

    @staticmethod
    def task_key(user_id: UUID | str, task_id: str) -> str:
        return f"media/tasks/videos/{user_id}/{task_id}.json"

    @staticmethod
    def asset_index_key(user_id: UUID | str, asset_filename: str) -> str:
        return f"media/tasks/videos/assets/{user_id}/{asset_filename}.json"

    def _provider_configuration(self) -> tuple[str, str]:
        api_key = self.settings.WUYINKEJI_VIDEO_API_KEY.strip()
        model = self.settings.WUYINKEJI_VIDEO_MODEL.strip()
        if not api_key or api_key == "__FILL_ME__":
            raise MediaConfigurationError("视频生成服务尚未配置有效 API Key。")
        if not model or model == "__FILL_ME__":
            raise MediaConfigurationError("视频生成服务尚未配置模型。")
        return api_key, model

    def _new_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self.settings.WUYINKEJI_VIDEO_TIMEOUT_SECONDS),
            follow_redirects=False,
        )

    def _normalize_kp_id(self, kp_id: str | None) -> str | None:
        if not kp_id:
            return None
        try:
            return get_websec_visual_prompt(kp_id).kp_id
        except KeyError as exc:
            raise ValueError("当前知识点不支持实时视频生成。") from exc

    async def _submit_upstream(
        self,
        client: httpx.AsyncClient,
        *,
        api_key: str,
        model: str,
        prompt: str,
        size: str,
        duration: str,
        reference_image_url: str | None,
    ) -> str:
        endpoint = (
            f"{self.settings.WUYINKEJI_VIDEO_BASE_URL.rstrip('/')}"
            f"/api/async/{model}"
        )
        body = {
            "prompt": prompt,
            "size": size,
            "duration": duration,
        }
        if reference_image_url:
            body["images"] = reference_image_url
        try:
            response = await client.post(
                endpoint,
                params={"key": api_key},
                headers={
                    "Authorization": api_key,
                    "Content-Type": "application/json",
                },
                json=body,
            )
        except httpx.TimeoutException as exc:
            raise MediaProviderError("视频生成服务提交超时，请稍后重试。") from exc
        except httpx.HTTPError as exc:
            raise MediaProviderError("无法连接视频生成服务，请稍后重试。") from exc
        payload = self._safe_json(response)
        if response.status_code in {401, 403}:
            raise MediaConfigurationError("视频生成凭据已失效或无权访问当前模型。")
        if response.status_code == 429:
            raise MediaProviderError("视频生成服务当前请求过多，请稍后重试。")
        if not response.is_success:
            raise MediaProviderError(
                f"视频生成服务暂不可用（HTTP {response.status_code}）。",
            )
        provider_code = _provider_code(payload)
        if provider_code in {401, 403}:
            raise MediaConfigurationError("视频生成凭据已失效或无权访问当前模型。")
        if provider_code == 429:
            raise MediaProviderError("视频生成服务当前请求过多，请稍后重试。")
        if not _provider_succeeded(payload):
            suffix = f"（业务码 {provider_code}）" if provider_code is not None else ""
            raise MediaProviderError(f"视频生成服务未接受本次任务{suffix}。")
        upstream_task_id = _provider_task_id(payload)
        if upstream_task_id is None:
            raise MediaProviderError("视频生成服务未返回有效任务标识。")
        return upstream_task_id

    async def _query_upstream(
        self,
        client: httpx.AsyncClient,
        *,
        api_key: str,
        upstream_task_id: str,
    ) -> tuple[int, str]:
        endpoint = (
            f"{self.settings.WUYINKEJI_VIDEO_BASE_URL.rstrip('/')}"
            "/api/async/detail"
        )
        try:
            response = await client.get(
                endpoint,
                params={"id": upstream_task_id, "key": api_key},
                headers={"Authorization": api_key},
            )
        except httpx.TimeoutException as exc:
            raise MediaProviderError("视频任务查询超时，请稍后重试。") from exc
        except httpx.HTTPError as exc:
            raise MediaProviderError("无法查询视频任务，请稍后重试。") from exc
        payload = self._safe_json(response)
        if response.status_code in {401, 403}:
            raise MediaConfigurationError("视频生成凭据已失效或无权查询任务。")
        if not response.is_success:
            raise MediaProviderError(
                f"视频任务查询暂不可用（HTTP {response.status_code}）。",
            )
        provider_code = _provider_code(payload)
        if provider_code in {401, 403}:
            raise MediaConfigurationError("视频生成凭据已失效或无权查询任务。")
        if not _provider_succeeded(payload):
            suffix = f"（业务码 {provider_code}）" if provider_code is not None else ""
            raise MediaProviderError(f"视频任务查询未返回有效结果{suffix}。")
        data = payload.get("data")
        status_value = data.get("status") if isinstance(data, dict) else None
        message = data.get("message") if isinstance(data, dict) else None
        normalized_status = _integer_value(status_value)
        if normalized_status is None:
            raise MediaProviderError("视频任务查询返回了无效状态。")
        normalized_message = message.strip() if isinstance(message, str) else ""
        if normalized_status == 2 and isinstance(data, dict):
            result = data.get("result")
            if isinstance(result, str) and result.strip():
                normalized_message = result.strip()
            elif isinstance(result, list):
                normalized_message = next(
                    (
                        item.strip()
                        for item in result
                        if isinstance(item, str) and item.strip()
                    ),
                    normalized_message,
                )
        return normalized_status, normalized_message

    async def _materialize_completed_video(
        self,
        client: httpx.AsyncClient,
        *,
        record: VideoTaskRecord,
        download_url: str,
    ) -> GeneratedVideoAsset:
        if not download_url:
            raise MediaProviderError("视频任务已完成，但未返回下载地址。")
        content, media_type = await self._download_video(client, download_url)
        extension = _ALLOWED_VIDEO_MIME_TYPES[media_type]
        asset_filename = f"{record.asset_id}.{extension}"
        kp_segment = record.kp_id or "custom"
        object_key = (
            f"media/generated/videos/{record.user_id}/{kp_segment}/{asset_filename}"
        )
        await self.storage.put_bytes(
            object_key=object_key,
            content=content,
            mime_type=media_type,
            original_filename=f"{kp_segment}-{asset_filename}",
            metadata={
                "asset_type": "educational_video",
                "course_code": "WEBSEC-101",
                "kp_id": record.kp_id or "custom",
                "user_id": record.user_id,
                "provider": record.provider,
                "model": record.model,
                "source": "live",
                "prompt_sha256": sha256(record.prompt.encode("utf-8")).hexdigest(),
                "local_task_id": record.task_id,
            },
        )
        index_payload = json.dumps(
            {"task_id": record.task_id, "object_key": object_key},
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
        await self.storage.put_bytes(
            object_key=self.asset_index_key(record.user_id, asset_filename),
            content=index_payload,
            mime_type="application/json",
            original_filename=f"{asset_filename}.json",
            metadata={
                "asset_type": "video_asset_index",
                "user_id": record.user_id,
                "local_task_id": record.task_id,
            },
        )
        return GeneratedVideoAsset(
            object_key=object_key,
            asset_filename=asset_filename,
            media_type=media_type,
            byte_size=len(content),
            duration=record.duration,
            size=record.size,
            prompt=record.prompt,
            model=record.model,
            provider=record.provider,
            task_id=record.task_id,
            kp_id=record.kp_id,
        )

    async def _download_video(
        self,
        client: httpx.AsyncClient,
        download_url: str,
    ) -> tuple[bytes, str]:
        current_url = download_url
        for redirect_count in range(_MAX_REDIRECTS + 1):
            await _assert_public_https_url(current_url, self._resolver)
            try:
                async with client.stream(
                    "GET",
                    current_url,
                    follow_redirects=False,
                ) as response:
                    if response.status_code in _REDIRECT_STATUS_CODES:
                        if redirect_count >= _MAX_REDIRECTS:
                            raise MediaProviderError("视频下载重定向次数过多。")
                        location = response.headers.get("location")
                        if not location:
                            raise MediaProviderError("视频下载重定向缺少目标地址。")
                        current_url = urljoin(current_url, location)
                        continue
                    if not response.is_success:
                        raise MediaProviderError("生成成功，但视频下载失败，请稍后重试。")
                    declared_length = response.headers.get("content-length")
                    if declared_length:
                        try:
                            if int(declared_length) > self.settings.WUYINKEJI_VIDEO_MAX_BYTES:
                                raise MediaProviderError("生成视频超过允许的文件大小。")
                        except ValueError as exc:
                            raise MediaProviderError("视频下载响应包含无效文件大小。") from exc
                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > self.settings.WUYINKEJI_VIDEO_MAX_BYTES:
                            raise MediaProviderError("生成视频超过允许的文件大小。")
                        chunks.append(chunk)
                    return _validate_video(
                        b"".join(chunks),
                        response.headers.get("content-type"),
                        self.settings.WUYINKEJI_VIDEO_MAX_BYTES,
                    )
            except httpx.TimeoutException as exc:
                raise MediaProviderError("视频下载超时，请稍后重试。") from exc
            except httpx.HTTPError as exc:
                raise MediaProviderError("视频下载失败，请稍后重试。") from exc
        raise MediaProviderError("视频下载重定向次数过多。")

    async def _load_task(
        self,
        *,
        user_id: UUID,
        task_id: str,
    ) -> VideoTaskRecord:
        content = await self.storage.get_bytes(self.task_key(user_id, task_id))
        if content is None:
            raise VideoTaskNotFoundError
        record = VideoTaskRecord.from_bytes(content)
        if record.user_id != str(user_id) or record.task_id != task_id:
            raise VideoTaskNotFoundError
        return record

    async def _save_task(self, record: VideoTaskRecord) -> None:
        payload = json.dumps(
            asdict(record),
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
        await self.storage.put_bytes(
            object_key=self.task_key(record.user_id, record.task_id),
            content=payload,
            mime_type="application/json",
            original_filename=f"{record.task_id}.json",
            metadata={
                "asset_type": "video_generation_task",
                "user_id": record.user_id,
                "local_task_id": record.task_id,
                "status": record.status,
            },
        )

    def _task_expired(self, record: VideoTaskRecord) -> bool:
        if record.poll_attempts >= self.settings.WUYINKEJI_VIDEO_MAX_POLL_ATTEMPTS:
            return True
        try:
            return datetime.now(UTC) >= datetime.fromisoformat(record.deadline_at)
        except ValueError:
            return True

    @staticmethod
    def _safe_json(response: httpx.Response) -> object:
        try:
            return response.json()
        except ValueError as exc:
            raise MediaProviderError("视频生成服务返回了无法解析的响应。") from exc


def _integer_value(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _provider_code(payload: object) -> int | None:
    if not isinstance(payload, dict):
        return None
    return _integer_value(payload.get("code"))


def _provider_succeeded(payload: object) -> bool:
    code = _provider_code(payload)
    return code in _PROVIDER_SUCCESS_CODES


def _provider_task_id(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if isinstance(data, str):
        candidate = data.strip()
        return candidate or None
    if not isinstance(data, dict):
        return None
    for key in ("id", "task_id"):
        candidate = data.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _normalize_uuid(value: str) -> str:
    try:
        parsed = UUID(value)
    except (TypeError, ValueError, AttributeError) as exc:
        raise VideoTaskNotFoundError from exc
    normalized = str(parsed)
    if value.lower() != normalized:
        raise VideoTaskNotFoundError
    return normalized


def _normalize_asset_filename(value: str) -> str:
    if "." not in value:
        raise VideoTaskNotFoundError
    stem, suffix = value.rsplit(".", 1)
    try:
        normalized_stem = _normalize_uuid(stem)
    except VideoTaskNotFoundError as exc:
        raise VideoTaskNotFoundError from exc
    normalized_suffix = suffix.lower()
    if normalized_suffix not in {"mp4", "webm"}:
        raise VideoTaskNotFoundError
    return f"{normalized_stem}.{normalized_suffix}"


async def _assert_public_https_url(
    value: str,
    resolver: Callable[[str], Awaitable[list[str]]],
) -> None:
    parsed = urlparse(value)
    if (
        parsed.scheme.lower() != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise MediaProviderError("媒体地址不是受支持的公开 HTTPS 地址。")
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".local"):
        raise MediaProviderError("媒体地址指向了不允许的主机。")
    try:
        literal_address = ipaddress.ip_address(hostname)
    except ValueError:
        addresses = await resolver(hostname)
        if not addresses:
            raise MediaProviderError("媒体地址无法解析到有效主机。")
    else:
        addresses = [str(literal_address)]
    try:
        parsed_addresses = [ipaddress.ip_address(address) for address in addresses]
    except ValueError as exc:
        raise MediaProviderError("媒体地址解析结果无效。") from exc
    if any(not address.is_global for address in parsed_addresses):
        raise MediaProviderError("媒体地址指向了不允许的网络。")


async def _resolve_host_addresses(hostname: str) -> list[str]:
    def resolve() -> list[str]:
        results = socket.getaddrinfo(
            hostname,
            443,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )
        return list({str(item[4][0]) for item in results})

    try:
        return await asyncio.to_thread(resolve)
    except OSError as exc:
        raise MediaProviderError("媒体地址无法解析到有效主机。") from exc


def _validate_video(
    content: bytes,
    declared_content_type: str | None,
    max_bytes: int,
) -> tuple[bytes, str]:
    if not content:
        raise MediaProviderError("视频生成服务返回了空文件。")
    if len(content) > max_bytes:
        raise MediaProviderError("生成视频超过允许的文件大小。")
    media_type = _detect_video_mime_type(content)
    if media_type is None:
        raise MediaProviderError("视频生成服务返回了不支持的文件类型。")
    declared = (declared_content_type or "").split(";", 1)[0].strip().lower()
    if declared and declared.startswith("video/") and declared not in _ALLOWED_VIDEO_MIME_TYPES:
        raise MediaProviderError("视频生成服务返回了不支持的媒体类型。")
    return content, media_type


def _detect_video_mime_type(content: bytes) -> str | None:
    if len(content) >= 12 and content[4:8] == b"ftyp":
        return "video/mp4"
    if content.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm"
    return None


__all__ = [
    "GeneratedVideoAsset",
    "VideoTaskNotFoundError",
    "VideoTaskRecord",
    "WuyinkejiVideoService",
]
