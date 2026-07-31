# Status: real

from __future__ import annotations

import asyncio
import gc
import json
import weakref
from uuid import UUID

import httpx
import pytest

from app.core.config import Settings
from app.services.media.volcengine_image_service import (
    MediaConfigurationError,
    MediaProviderError,
)
from app.services.media.websec_visual_prompts import WEBSEC_VIDEO_PROMPTS
from app.services.media.wuyinkeji_video_service import (
    VideoTaskNotFoundError,
    WuyinkejiVideoService,
    _task_lock,
    _task_locks,
)


_USER_A = UUID("11111111-1111-4111-8111-111111111111")
_USER_B = UUID("22222222-2222-4222-8222-222222222222")
_MP4 = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 32


class _MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.calls: list[dict[str, object]] = []

    async def put_bytes(self, **kwargs: object) -> None:
        self.calls.append(dict(kwargs))
        self.objects[str(kwargs["object_key"])] = bytes(kwargs["content"])

    async def get_bytes(self, object_key: str) -> bytes | None:
        return self.objects.get(object_key)


async def _public_resolver(_hostname: str) -> list[str]:
    return ["93.184.216.34"]


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "WUYINKEJI_VIDEO_API_KEY": "unit-test-key",
        "WUYINKEJI_VIDEO_BASE_URL": "https://api.wuyinkeji.example",
        "WUYINKEJI_VIDEO_MODEL": "video_google_omni",
        "WUYINKEJI_VIDEO_TIMEOUT_SECONDS": 30,
        "WUYINKEJI_VIDEO_POLL_INTERVAL_SECONDS": 2,
        "WUYINKEJI_VIDEO_MAX_POLL_ATTEMPTS": 10,
        "WUYINKEJI_VIDEO_MAX_BYTES": 1024,
    }
    values.update(overrides)
    return Settings(**values)


def test_video_prompt_library_has_six_detailed_english_presets() -> None:
    assert set(WEBSEC_VIDEO_PROMPTS) == {
        "http-basics",
        "sql-injection",
        "xss-reflected",
        "csrf",
        "ssrf",
        "owasp-top10",
    }
    assert all(len(item.prompt) > 240 for item in WEBSEC_VIDEO_PROMPTS.values())
    assert all("10-second" in item.prompt for item in WEBSEC_VIDEO_PROMPTS.values())


def test_task_lock_registry_reuses_live_lock_and_releases_idle_lock() -> None:
    lock_key = "test-user:test-task"
    first = _task_lock(lock_key)
    second = _task_lock(lock_key)
    reference = weakref.ref(first)

    assert first is second
    assert _task_locks.get(lock_key) is first

    del first, second
    gc.collect()

    assert reference() is None
    assert lock_key not in _task_locks


@pytest.mark.anyio
async def test_submit_uses_opaque_local_id_and_persists_redacted_task() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"code": 200, "msg": "success", "data": {"id": "provider-task-1"}},
        )

    storage = _MemoryStorage()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        record = await WuyinkejiVideoService(
            settings=_settings(),
            storage=storage,
            client=client,
            resolver=_public_resolver,
        ).submit(
            user_id=_USER_A,
            prompt="A safe educational HTTP animation for students.",
            kp_id="http-basics",
        )

    assert UUID(record.task_id)
    assert record.task_id != "provider-task-1"
    assert requests[0].url.path == "/api/async/video_google_omni"
    assert requests[0].url.params["key"] == "unit-test-key"
    assert requests[0].headers["authorization"] == "unit-test-key"
    assert requests[0].headers["content-type"] == "application/json"
    assert json.loads(requests[0].content) == {
        "prompt": "A safe educational HTTP animation for students.",
        "size": "1280x720",
        "duration": "10",
    }
    task_key = WuyinkejiVideoService.task_key(_USER_A, record.task_id)
    persisted = storage.objects[task_key].decode()
    assert "provider-task-1" in persisted
    assert "unit-test-key" not in persisted
    assert "https://" not in persisted
    assert '"status":"pending"' in persisted


@pytest.mark.anyio
async def test_submit_fails_closed_without_key() -> None:
    service = WuyinkejiVideoService(
        settings=_settings(WUYINKEJI_VIDEO_API_KEY="__FILL_ME__"),
        storage=_MemoryStorage(),
    )
    with pytest.raises(MediaConfigurationError, match="API Key"):
        await service.submit(
            user_id=_USER_A,
            prompt="A sufficiently detailed video prompt.",
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("provider_status", "expected_status"),
    [(0, "pending"), (1, "processing"), (3, "failed")],
)
async def test_poll_maps_provider_states(
    provider_status: int,
    expected_status: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                200,
                json={"code": 0, "data": {"id": "provider-task-state"}},
            )
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "status": provider_status,
                    "message": "provider-internal-message",
                },
            },
        )

    storage = _MemoryStorage()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = WuyinkejiVideoService(
            settings=_settings(),
            storage=storage,
            client=client,
            resolver=_public_resolver,
        )
        submitted = await service.submit(
            user_id=_USER_A,
            prompt="A sufficiently detailed video prompt.",
            kp_id="csrf",
        )
        result = await service.poll(user_id=_USER_A, task_id=submitted.task_id)

    assert result.status == expected_status
    assert result.poll_attempts == 1
    if provider_status == 3:
        assert result.error_message == (
            "上游已接收任务但未产出视频，且未返回失败详情。"
            "请检查服务余额、点数及模型状态，或稍后修改描述再试。"
        )
        task_json = storage.objects[
            WuyinkejiVideoService.task_key(_USER_A, submitted.task_id)
        ].decode()
        assert "provider-internal-message" not in task_json


@pytest.mark.anyio
async def test_completed_poll_downloads_once_and_builds_user_asset_index() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST":
            return httpx.Response(
                200,
                json={"code": 200, "data": {"id": "provider-task-completed"}},
            )
        if request.url.path == "/api/async/detail":
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "data": {
                        "status": "2",
                        "result": ["https://cdn.example/video.mp4"],
                        "message": "",
                    },
                },
            )
        return httpx.Response(
            200,
            content=_MP4,
            headers={"content-type": "video/mp4"},
        )

    storage = _MemoryStorage()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = WuyinkejiVideoService(
            settings=_settings(),
            storage=storage,
            client=client,
            resolver=_public_resolver,
        )
        submitted = await service.submit(
            user_id=_USER_A,
            prompt="A sufficiently detailed video prompt.",
            kp_id="sql-injection",
        )
        completed, concurrent = await asyncio.gather(
            service.poll(user_id=_USER_A, task_id=submitted.task_id),
            service.poll(user_id=_USER_A, task_id=submitted.task_id),
        )
        request_count = len(requests)
        repeated = await service.poll(user_id=_USER_A, task_id=submitted.task_id)
        object_key = await service.get_asset_object_key(
            user_id=_USER_A,
            asset_filename=completed.asset_filename or "",
        )

    assert completed.status == "completed"
    assert concurrent.status == "completed"
    assert repeated.status == "completed"
    assert len(requests) == request_count
    assert completed.asset_filename is not None
    assert completed.asset_filename.endswith(".mp4")
    assert object_key == completed.object_key
    assert object_key.startswith(
        f"media/generated/videos/{_USER_A}/sql-injection/",
    )
    assert storage.objects[object_key] == _MP4
    index_key = WuyinkejiVideoService.asset_index_key(
        _USER_A,
        completed.asset_filename,
    )
    index_json = storage.objects[index_key].decode()
    assert set(__import__("json").loads(index_json)) == {"task_id", "object_key"}
    assert "provider-task-completed" not in index_json


@pytest.mark.anyio
async def test_task_and_asset_lookup_are_user_scoped() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": 0, "data": {"id": "provider-task-private"}},
        )

    storage = _MemoryStorage()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = WuyinkejiVideoService(
            settings=_settings(),
            storage=storage,
            client=client,
            resolver=_public_resolver,
        )
        submitted = await service.submit(
            user_id=_USER_A,
            prompt="A sufficiently detailed video prompt.",
        )
        with pytest.raises(VideoTaskNotFoundError):
            await service.poll(user_id=_USER_B, task_id=submitted.task_id)
        with pytest.raises(VideoTaskNotFoundError):
            await service.poll(user_id=_USER_A, task_id="not-a-uuid")


@pytest.mark.anyio
async def test_completed_poll_rejects_private_download_and_invalid_video() -> None:
    mode = "private"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                200,
                json={"code": 0, "data": {"id": f"provider-{mode}"}},
            )
        if request.url.path == "/api/async/detail":
            url = (
                "https://127.0.0.1/private.mp4"
                if mode == "private"
                else "https://cdn.example/not-video.mp4"
            )
            return httpx.Response(
                200,
                json={"code": 0, "data": {"status": 2, "message": url}},
            )
        return httpx.Response(200, content=b"not a video")

    storage = _MemoryStorage()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = WuyinkejiVideoService(
            settings=_settings(),
            storage=storage,
            client=client,
            resolver=_public_resolver,
        )
        private_task = await service.submit(
            user_id=_USER_A,
            prompt="A sufficiently detailed video prompt.",
        )
        with pytest.raises(MediaProviderError, match="不允许的网络"):
            await service.poll(user_id=_USER_A, task_id=private_task.task_id)

        mode = "invalid"
        invalid_task = await service.submit(
            user_id=_USER_A,
            prompt="A second sufficiently detailed video prompt.",
        )
        with pytest.raises(MediaProviderError, match="文件类型"):
            await service.poll(user_id=_USER_A, task_id=invalid_task.task_id)


@pytest.mark.anyio
async def test_completed_poll_rejects_private_dns_resolution() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                200,
                json={"code": 0, "data": {"id": "provider-private-dns"}},
            )
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "status": 2,
                    "message": "https://cdn.example/video.mp4",
                },
            },
        )

    async def private_resolver(_hostname: str) -> list[str]:
        return ["10.0.0.8"]

    storage = _MemoryStorage()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = WuyinkejiVideoService(
            settings=_settings(),
            storage=storage,
            client=client,
            resolver=private_resolver,
        )
        submitted = await service.submit(
            user_id=_USER_A,
            prompt="A sufficiently detailed video prompt.",
        )
        with pytest.raises(MediaProviderError, match="不允许的网络"):
            await service.poll(user_id=_USER_A, task_id=submitted.task_id)


@pytest.mark.anyio
async def test_completed_poll_rejects_oversized_download() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                200,
                json={"code": 0, "data": {"id": "provider-oversized"}},
            )
        if request.url.path == "/api/async/detail":
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "status": 2,
                        "message": "https://cdn.example/video.mp4",
                    },
                },
            )
        return httpx.Response(
            200,
            content=_MP4 + (b"x" * 2_048),
            headers={"content-type": "video/mp4"},
        )

    storage = _MemoryStorage()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = WuyinkejiVideoService(
            settings=_settings(),
            storage=storage,
            client=client,
            resolver=_public_resolver,
        )
        submitted = await service.submit(
            user_id=_USER_A,
            prompt="A sufficiently detailed video prompt.",
        )
        with pytest.raises(MediaProviderError, match="文件大小"):
            await service.poll(user_id=_USER_A, task_id=submitted.task_id)


@pytest.mark.anyio
async def test_provider_error_never_echoes_secret_or_response() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            500,
            json={
                "message": (
                    "unit-test-key https://api.wuyinkeji.example/"
                    "api/async/video_google_omni?key=unit-test-key"
                ),
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = WuyinkejiVideoService(
            settings=_settings(),
            storage=_MemoryStorage(),
            client=client,
            resolver=_public_resolver,
        )
        with pytest.raises(MediaProviderError) as error:
            await service.submit(
                user_id=_USER_A,
                prompt="A sufficiently detailed video prompt.",
            )
    message = str(error.value)
    assert "unit-test-key" not in message
    assert "?key=" not in message
    assert "HTTP 500" in message
