# Status: real

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.media import (
    generate_educational_video,
    get_educational_video_asset,
    get_educational_video_status,
)
from app.core.config import Settings
from app.schemas.media import VideoGenerateRequest


_USER_ID = UUID("11111111-1111-4111-8111-111111111111")


class _Session:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def flush(self) -> None:
        return None


def _settings(local_root: Path) -> Settings:
    return Settings(
        _env_file=None,
        STORAGE_PROVIDER="local",
        STORAGE_LOCAL_ROOT=local_root,
        WUYINKEJI_VIDEO_API_KEY="__FILL_ME__",
    )


@pytest.mark.anyio
async def test_generate_video_returns_friendly_503_without_key(tmp_path: Path) -> None:
    session = _Session()
    with pytest.raises(HTTPException) as error:
        await generate_educational_video(
            VideoGenerateRequest(
                prompt="A sufficiently detailed educational animation prompt.",
                kp_id="http-basics",
            ),
            session,  # type: ignore[arg-type]
            _settings(tmp_path),
            _USER_ID,
        )
    assert error.value.status_code == 503
    assert error.value.detail == {
        "code": "VIDEO_PROVIDER_NOT_READY",
        "message": "视频生成服务尚未配置有效 API Key。",
    }
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.anyio
async def test_video_status_hides_malformed_or_missing_task_as_404(
    tmp_path: Path,
) -> None:
    for task_id in ("not-a-uuid", "11111111-1111-4111-8111-111111111111"):
        session = _Session()
        with pytest.raises(HTTPException) as error:
            await get_educational_video_status(
                task_id,
                session,  # type: ignore[arg-type]
                _settings(tmp_path),
                _USER_ID,
            )
        assert error.value.status_code == 404
        assert error.value.detail["code"] == "VIDEO_TASK_NOT_FOUND"
        assert session.rollbacks == 1


@pytest.mark.anyio
async def test_video_asset_rejects_non_uuid_filename(tmp_path: Path) -> None:
    with pytest.raises(HTTPException) as error:
        await get_educational_video_asset(
            "../../secret.mp4",
            _Session(),  # type: ignore[arg-type]
            _settings(tmp_path),
            _USER_ID,
        )
    assert error.value.status_code == 404
