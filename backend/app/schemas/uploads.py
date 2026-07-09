# Status: real

from pydantic import BaseModel, Field


class UploadInitRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., min_length=1, max_length=128)
    size_bytes: int = Field(..., ge=1)
    target_prefix: str = Field(..., min_length=1, max_length=256)


class UploadInitResponse(BaseModel):
    upload_id: str
    object_key: str
    method: str
    presigned_url: str
    expires_in: int
    max_bytes: int
