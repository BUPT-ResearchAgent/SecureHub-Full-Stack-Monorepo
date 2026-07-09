# Status: real

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from qcloud_cos import CosConfig, CosS3Client
from qcloud_cos.cos_exception import CosClientError, CosServiceError

from app.core.config import Settings, get_settings
from app.services.storage.providers.base import StorageProviderError


_NOT_FOUND_CODES = {"NoSuchKey", "NoSuchResource", "NotFound", "404"}
_ALLOWED_SIGNED_METHODS = {"GET", "PUT", "HEAD", "DELETE"}


class CosStorageProvider:
    provider_name = "cos"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.bucket = self.settings.COS_BUCKET
        self.upload_max_bytes = self.settings.COS_UPLOAD_MAX_BYTES
        self.default_expires_seconds = self.settings.COS_PRESIGNED_EXPIRES_SECONDS
        if client is not None:
            self.client = client
            return

        config = CosConfig(
            Region=self.settings.COS_REGION,
            SecretId=self.settings.COS_SECRET_ID,
            SecretKey=self.settings.COS_SECRET_KEY,
            Scheme=self.settings.COS_SCHEME,
        )
        self.client = CosS3Client(config)

    async def put_bytes(
        self,
        *,
        object_key: str,
        content: bytes,
        mime_type: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> None:
        if len(content) > self.upload_max_bytes:
            raise StorageProviderError(
                "COS upload exceeds COS_UPLOAD_MAX_BYTES "
                f"({len(content)} > {self.upload_max_bytes})"
            )
        kwargs: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": object_key,
            "Body": content,
        }
        if mime_type:
            kwargs["ContentType"] = mime_type
        if metadata:
            kwargs["Metadata"] = dict(metadata)

        try:
            await asyncio.to_thread(self.client.put_object, **kwargs)
        except (CosServiceError, CosClientError) as exc:
            raise _storage_error("put_object", object_key, exc) from exc

    async def get_bytes(self, object_key: str) -> bytes | None:
        def _get() -> bytes:
            response = self.client.get_object(Bucket=self.bucket, Key=object_key)
            return _read_response_body(response.get("Body"))

        try:
            return await asyncio.to_thread(_get)
        except CosServiceError as exc:
            if _is_not_found(exc):
                return None
            raise _storage_error("get_object", object_key, exc) from exc
        except CosClientError as exc:
            raise _storage_error("get_object", object_key, exc) from exc

    async def delete(self, object_key: str) -> None:
        try:
            await asyncio.to_thread(
                self.client.delete_object,
                Bucket=self.bucket,
                Key=object_key,
            )
        except CosServiceError as exc:
            if _is_not_found(exc):
                return
            raise _storage_error("delete_object", object_key, exc) from exc
        except CosClientError as exc:
            raise _storage_error("delete_object", object_key, exc) from exc

    async def exists(self, object_key: str) -> bool:
        try:
            await asyncio.to_thread(
                self.client.head_object,
                Bucket=self.bucket,
                Key=object_key,
            )
            return True
        except CosServiceError as exc:
            if _is_not_found(exc):
                return False
            raise _storage_error("head_object", object_key, exc) from exc
        except CosClientError as exc:
            raise _storage_error("head_object", object_key, exc) from exc

    async def presigned_url(
        self,
        object_key: str,
        *,
        method: str = "GET",
        expires_in: int = 600,
    ) -> str | None:
        method = method.upper()
        if method not in _ALLOWED_SIGNED_METHODS:
            raise ValueError(f"unsupported signed URL method: {method}")
        if expires_in <= 0:
            raise ValueError("expires_in must be positive")
        try:
            return await asyncio.to_thread(
                self.client.get_presigned_url,
                Method=method,
                Bucket=self.bucket,
                Key=object_key,
                Expired=expires_in,
            )
        except (CosServiceError, CosClientError) as exc:
            raise _storage_error("get_presigned_url", object_key, exc) from exc


def _read_response_body(body: Any) -> bytes:
    if body is None:
        return b""
    if isinstance(body, bytes):
        return body
    if isinstance(body, str):
        return body.encode("utf-8")
    if hasattr(body, "get_raw_stream"):
        stream = body.get_raw_stream()
        return stream.read()
    if hasattr(body, "read"):
        return body.read()
    raise StorageProviderError("COS get_object returned an unreadable response body")


def _is_not_found(error: CosServiceError) -> bool:
    status_code = _error_part(error, "get_status_code")
    error_code = _error_part(error, "get_error_code")
    return str(status_code) == "404" or str(error_code) in _NOT_FOUND_CODES


def _storage_error(action: str, object_key: str, error: BaseException) -> StorageProviderError:
    status_code = _error_part(error, "get_status_code") or "unknown"
    error_code = _error_part(error, "get_error_code") or error.__class__.__name__
    request_id = _error_part(error, "get_request_id") or "unknown"
    return StorageProviderError(
        f"COS {action} failed for object_key={object_key!r}; "
        f"status={status_code}; code={error_code}; request_id={request_id}"
    )


def _error_part(error: BaseException, getter: str) -> str | None:
    method = getattr(error, getter, None)
    if callable(method):
        value = method()
        if value is not None:
            return str(value)
    value = getattr(error, getter.removeprefix("get_"), None)
    if value is not None:
        return str(value)
    return None
