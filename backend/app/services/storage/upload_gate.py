# Status: real

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import re
from uuid import uuid4

from app.core.config import Settings
from app.services.storage.provider_factory import create_storage_provider


RESTRICTED_TARGET_PREFIXES = ("private/team-sync/", "runtime/", "backups/")


class UploadGateError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class UploadInitResult:
    upload_id: str
    object_key: str
    method: str
    presigned_url: str
    expires_in: int
    max_bytes: int


class UploadGateService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def init_upload(
        self,
        *,
        supplied_key: str | None,
        filename: str,
        mime_type: str,
        size_bytes: int,
        target_prefix: str,
    ) -> UploadInitResult:
        self._validate_upload_key(supplied_key)
        self._validate_size(size_bytes)
        self._validate_mime_type(mime_type)
        self._validate_target_prefix(target_prefix)

        upload_id = str(uuid4())
        object_key = f"tmp/uploads/{upload_id}/{_safe_filename(filename)}"
        presigned_url = await self._create_presigned_put_url(object_key)
        return UploadInitResult(
            upload_id=upload_id,
            object_key=object_key,
            method="PUT",
            presigned_url=presigned_url,
            expires_in=self.settings.UPLOAD_GATE_PRESIGNED_EXPIRES_SECONDS,
            max_bytes=self.settings.UPLOAD_GATE_MAX_BYTES,
        )

    def _validate_upload_key(self, supplied_key: str | None) -> None:
        if not self.settings.UPLOAD_GATE_ENABLED:
            raise UploadGateError(403, "UPLOAD_GATE_DISABLED", "Upload gate is disabled.")
        expected_hash = _normalize_secret_hash(self.settings.UPLOAD_GATE_SECRET_HASH)
        if not expected_hash or not supplied_key:
            raise UploadGateError(401, "UPLOAD_GATE_UNAUTHORIZED", "Invalid upload key.")
        supplied_hash = sha256(supplied_key.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(supplied_hash, expected_hash):
            raise UploadGateError(401, "UPLOAD_GATE_UNAUTHORIZED", "Invalid upload key.")

    def _validate_size(self, size_bytes: int) -> None:
        if size_bytes <= 0:
            raise UploadGateError(400, "UPLOAD_SIZE_INVALID", "Upload size must be positive.")
        if size_bytes > self.settings.UPLOAD_GATE_MAX_BYTES:
            raise UploadGateError(413, "UPLOAD_TOO_LARGE", "Upload exceeds configured max bytes.")

    def _validate_mime_type(self, mime_type: str) -> None:
        normalized = mime_type.strip().lower()
        allowed = any(
            normalized.startswith(prefix.lower())
            if prefix.endswith("/")
            else normalized == prefix.lower()
            for prefix in self.settings.UPLOAD_GATE_ALLOWED_MIME_PREFIXES
        )
        if not allowed:
            raise UploadGateError(400, "UPLOAD_MIME_NOT_ALLOWED", "MIME type is not allowed.")

    def _validate_target_prefix(self, target_prefix: str) -> None:
        normalized = _normalize_prefix(target_prefix)
        if any(normalized.startswith(prefix) for prefix in RESTRICTED_TARGET_PREFIXES):
            raise UploadGateError(400, "UPLOAD_PREFIX_NOT_ALLOWED", "Target prefix is not allowed.")

        allowed = False
        for prefix in self.settings.UPLOAD_GATE_ALLOWED_PREFIXES:
            allowed_prefix = _normalize_prefix(prefix)
            if normalized == allowed_prefix.rstrip("/") or normalized.startswith(allowed_prefix):
                allowed = True
                break
        if not allowed:
            raise UploadGateError(400, "UPLOAD_PREFIX_NOT_ALLOWED", "Target prefix is not allowed.")

    async def _create_presigned_put_url(self, object_key: str) -> str:
        if self.settings.STORAGE_PROVIDER != "cos":
            raise UploadGateError(503, "UPLOAD_PROVIDER_UNAVAILABLE", "Upload gate requires COS storage.")
        provider = create_storage_provider(self.settings)
        signed_url = await provider.presigned_url(
            object_key,
            method="PUT",
            expires_in=self.settings.UPLOAD_GATE_PRESIGNED_EXPIRES_SECONDS,
        )
        if not signed_url:
            raise UploadGateError(503, "UPLOAD_SIGNING_FAILED", "Failed to create upload URL.")
        return signed_url


def _normalize_secret_hash(value: str) -> str:
    text = value.strip().lower()
    if text.startswith("sha256:"):
        text = text.removeprefix("sha256:").strip()
    return text


def _normalize_prefix(value: str) -> str:
    normalized = value.replace("\\", "/").strip().lstrip("/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    if not normalized or ".." in normalized.split("/"):
        raise UploadGateError(400, "UPLOAD_PREFIX_NOT_ALLOWED", "Target prefix is not allowed.")
    if not normalized.endswith("/"):
        normalized = f"{normalized}/"
    return normalized


def _safe_filename(filename: str) -> str:
    basename = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    basename = basename.strip(".")
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", basename)
    return safe or "upload.bin"
