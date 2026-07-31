# Status: real

"""Authenticated educational image generation and asset delivery."""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Response, status

from app.deps import RequiredCurrentUserIdDep, SessionDep, SettingsDep
from app.schemas.media import (
    EducationalImageGenerateRequest,
    EducationalImageGenerateResponse,
    VideoGenerateRequest,
    VideoGenerateResponse,
    VideoStatusResponse,
)
from app.services.media.volcengine_image_service import (
    MediaConfigurationError,
    MediaProviderError,
    VolcengineImageService,
)
from app.services.media.websec_visual_prompts import get_websec_visual_prompt
from app.services.media.wuyinkeji_video_service import (
    VideoTaskNotFoundError,
    WuyinkejiVideoService,
)
from app.services.storage.storage_service import StorageService


router = APIRouter(prefix="/media")
_ASSET_FILENAME = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\.(?:jpg|png|webp)$",
    re.IGNORECASE,
)
_MIME_BY_SUFFIX = {
    "jpg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}
_VIDEO_ASSET_FILENAME = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\.(?:mp4|webm)$",
    re.IGNORECASE,
)
_VIDEO_MIME_BY_SUFFIX = {
    "mp4": "video/mp4",
    "webm": "video/webm",
}


@router.post(
    "/generate-image",
    response_model=EducationalImageGenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_educational_image(
    payload: EducationalImageGenerateRequest,
    session: SessionDep,
    settings: SettingsDep,
    current_user_id: RequiredCurrentUserIdDep,
) -> EducationalImageGenerateResponse:
    try:
        get_websec_visual_prompt(payload.kp_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "UNKNOWN_KNOWLEDGE_POINT",
                "message": "当前知识点不支持实时图解生成。",
            },
        ) from exc

    storage = StorageService(session, settings=settings)
    service = VolcengineImageService(settings=settings, storage=storage)
    try:
        asset = await service.generate(
            user_id=current_user_id,
            kp_id=payload.kp_id,
            custom_prompt=payload.prompt,
            visualization_type=payload.visualization_type,
            size=payload.size,
        )
        await session.commit()
    except MediaConfigurationError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "MEDIA_PROVIDER_NOT_READY", "message": str(exc)},
        ) from exc
    except MediaProviderError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "MEDIA_PROVIDER_ERROR", "message": str(exc)},
        ) from exc
    except Exception:
        await session.rollback()
        raise

    return EducationalImageGenerateResponse(
        image_url=f"/api/v1/media/assets/{asset.kp_id}/{asset.asset_filename}",
        object_key=asset.object_key,
        prompt_used=asset.prompt_used,
        model=asset.model,
        provider=asset.provider,
        kp_id=asset.kp_id,
        media_type=asset.media_type,
        byte_size=asset.byte_size,
    )


@router.get("/assets/{kp_id}/{asset_filename}")
async def get_educational_image_asset(
    kp_id: str,
    asset_filename: str,
    session: SessionDep,
    settings: SettingsDep,
    current_user_id: RequiredCurrentUserIdDep,
) -> Response:
    try:
        normalized_kp_id = get_websec_visual_prompt(kp_id).kp_id
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="asset not found") from exc
    if not _ASSET_FILENAME.fullmatch(asset_filename):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="asset not found")

    object_key = (
        f"media/generated/images/{current_user_id}/{normalized_kp_id}/{asset_filename}"
    )
    content = await StorageService(session, settings=settings).get_bytes(object_key)
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="asset not found")
    suffix = asset_filename.rsplit(".", 1)[-1].lower()
    return Response(
        content=content,
        media_type=_MIME_BY_SUFFIX[suffix],
        headers={
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post(
    "/generate-video",
    response_model=VideoGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_educational_video(
    payload: VideoGenerateRequest,
    session: SessionDep,
    settings: SettingsDep,
    current_user_id: RequiredCurrentUserIdDep,
) -> VideoGenerateResponse:
    storage = StorageService(session, settings=settings)
    service = WuyinkejiVideoService(settings=settings, storage=storage)
    try:
        record = await service.submit(
            user_id=current_user_id,
            prompt=payload.prompt,
            kp_id=payload.kp_id,
            size=payload.size,
            duration=payload.duration,
            reference_image_url=payload.reference_image_url,
        )
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_VIDEO_REQUEST", "message": str(exc)},
        ) from exc
    except MediaConfigurationError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "VIDEO_PROVIDER_NOT_READY", "message": str(exc)},
        ) from exc
    except MediaProviderError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "VIDEO_PROVIDER_ERROR", "message": str(exc)},
        ) from exc
    except Exception:
        await session.rollback()
        raise
    return VideoGenerateResponse(
        task_id=record.task_id,
        model=record.model,
    )


@router.get(
    "/video-status/{task_id}",
    response_model=VideoStatusResponse,
)
async def get_educational_video_status(
    task_id: str,
    session: SessionDep,
    settings: SettingsDep,
    current_user_id: RequiredCurrentUserIdDep,
) -> VideoStatusResponse:
    storage = StorageService(session, settings=settings)
    service = WuyinkejiVideoService(settings=settings, storage=storage)
    try:
        record = await service.poll(user_id=current_user_id, task_id=task_id)
        await session.commit()
    except VideoTaskNotFoundError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "VIDEO_TASK_NOT_FOUND", "message": "视频任务不存在。"},
        ) from exc
    except MediaConfigurationError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "VIDEO_PROVIDER_NOT_READY", "message": str(exc)},
        ) from exc
    except MediaProviderError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "VIDEO_PROVIDER_ERROR", "message": str(exc)},
        ) from exc
    except Exception:
        await session.rollback()
        raise
    return VideoStatusResponse(
        task_id=record.task_id,
        status=record.status,
        video_url=(
            f"/api/v1/media/video-assets/{record.asset_filename}"
            if record.status == "completed" and record.asset_filename
            else None
        ),
        object_key=record.object_key if record.status == "completed" else None,
        error_message=record.error_message if record.status == "failed" else None,
        model=record.model,
        prompt=record.prompt,
        kp_id=record.kp_id,
        size=record.size,
        duration=record.duration,
        media_type=record.media_type,
        byte_size=record.byte_size,
        generated_at=record.updated_at if record.status == "completed" else None,
    )


@router.get("/video-assets/{asset_filename}")
async def get_educational_video_asset(
    asset_filename: str,
    session: SessionDep,
    settings: SettingsDep,
    current_user_id: RequiredCurrentUserIdDep,
) -> Response:
    if not _VIDEO_ASSET_FILENAME.fullmatch(asset_filename):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="asset not found",
        )
    storage = StorageService(session, settings=settings)
    service = WuyinkejiVideoService(settings=settings, storage=storage)
    try:
        object_key = await service.get_asset_object_key(
            user_id=current_user_id,
            asset_filename=asset_filename,
        )
    except VideoTaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="asset not found",
        ) from exc
    content = await storage.get_bytes(object_key)
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="asset not found",
        )
    suffix = asset_filename.rsplit(".", 1)[-1].lower()
    return Response(
        content=content,
        media_type=_VIDEO_MIME_BY_SUFFIX[suffix],
        headers={
            "Cache-Control": "private, max-age=3600",
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
        },
    )


__all__ = ["router"]
