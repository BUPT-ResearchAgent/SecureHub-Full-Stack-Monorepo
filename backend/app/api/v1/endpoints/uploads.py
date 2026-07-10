# Status: real

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from app.deps import SettingsDep
from app.schemas.uploads import UploadInitRequest, UploadInitResponse
from app.services.storage.upload_gate import UploadGateError, UploadGateService


router = APIRouter(prefix="/uploads")


@router.post("/init", response_model=UploadInitResponse)
async def init_upload(
    payload: UploadInitRequest,
    settings: SettingsDep,
    upload_key: Annotated[str | None, Header(alias="X-SecureHub-Upload-Key")] = None,
) -> UploadInitResponse:
    try:
        result = await UploadGateService(settings).init_upload(
            supplied_key=upload_key,
            filename=payload.filename,
            mime_type=payload.mime_type,
            size_bytes=payload.size_bytes,
            target_prefix=payload.target_prefix,
        )
    except UploadGateError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    return UploadInitResponse(
        upload_id=result.upload_id,
        object_key=result.object_key,
        method=result.method,
        presigned_url=result.presigned_url,
        expires_in=result.expires_in,
        max_bytes=result.max_bytes,
    )
