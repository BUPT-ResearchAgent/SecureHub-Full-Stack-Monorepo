# Status: real

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import sys

import httpx
from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.db import models  # noqa: F401
from app.db.models.storage.storage_object import StorageObject
from app.db.session import get_sessionmaker
from app.services.storage.provider_factory import create_storage_provider


DEFAULT_MANIFEST = REPO_ROOT / "data" / "manifests" / "cos_private_team_sync_manifest.jsonl"
PRIVATE_DATA_PREFIX = "private/team-sync/data/"
POSTGRES_BACKUP_PREFIX = "backups/postgres/"


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    object_key: str
    sha256: str
    size_bytes: int
    bucket: str
    mime_type: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify private COS sync manifest entries.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="JSONL manifest path. Defaults to data/manifests/cos_private_team_sync_manifest.jsonl.",
    )
    parser.add_argument("--limit", type=int, default=10, help="Maximum entries to verify. Defaults to 10.")
    return parser.parse_args()


def load_manifest(path: Path, *, limit: int) -> list[ManifestEntry]:
    if limit < 0:
        raise ValueError("--limit must be >= 0")
    path = path if path.is_absolute() else REPO_ROOT / path
    if not path.exists():
        raise FileNotFoundError(f"manifest not found: {path}")

    entries: list[ManifestEntry] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if len(entries) >= limit:
                break
            if not line.strip():
                continue
            row = json.loads(line)
            object_key = str(row["object_key"])
            _validate_manifest_object_key(object_key)
            entries.append(
                ManifestEntry(
                    object_key=object_key,
                    sha256=str(row["sha256"]),
                    size_bytes=int(row["size_bytes"]),
                    bucket=str(row["bucket"]),
                    mime_type=row.get("mime_type"),
                )
            )
    return entries


async def verify_entries(entries: list[ManifestEntry]) -> None:
    settings = get_settings()
    if settings.STORAGE_PROVIDER != "cos":
        raise SystemExit("Set STORAGE_PROVIDER=cos before verifying private COS sync URLs.")

    provider = create_storage_provider(settings)
    url_ok = 0
    hash_ok = 0
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for entry in entries:
            signed_url = await provider.presigned_url(
                entry.object_key,
                method="GET",
                expires_in=settings.COS_PRESIGNED_EXPIRES_SECONDS,
            )
            if not signed_url:
                raise RuntimeError(f"failed to generate signed URL for object_key={entry.object_key!r}")
            response = await client.get(signed_url)
            if response.status_code != 200:
                raise RuntimeError(
                    f"signed URL GET failed for object_key={entry.object_key!r}; "
                    f"status={response.status_code}"
                )
            url_ok += 1
            if len(response.content) != entry.size_bytes:
                raise RuntimeError(f"size mismatch for object_key={entry.object_key!r}")
            if sha256(response.content).hexdigest() != entry.sha256:
                raise RuntimeError(f"hash mismatch for object_key={entry.object_key!r}")
            hash_ok += 1

    storage_ok = await verify_storage_objects(entries)
    print(f"COS_PRIVATE_SYNC_URL_OK count={url_ok}")
    print(f"COS_PRIVATE_SYNC_HASH_OK count={hash_ok}")
    print(f"STORAGE_OBJECTS_PRIVATE_SYNC_OK count={storage_ok}")


async def verify_storage_objects(entries: list[ManifestEntry]) -> int:
    sessionmaker = get_sessionmaker()
    count = 0
    async with sessionmaker() as session:
        for entry in entries:
            row = (
                await session.execute(
                    select(StorageObject).where(StorageObject.object_key == entry.object_key)
                )
            ).scalar_one_or_none()
            if row is None:
                raise RuntimeError(f"storage_objects missing object_key={entry.object_key!r}")
            if row.provider != "cos" or row.bucket != entry.bucket or row.status != "ready":
                raise RuntimeError(f"storage_objects provider/bucket/status mismatch for {entry.object_key!r}")
            if row.size_bytes != entry.size_bytes or row.content_hash != entry.sha256:
                raise RuntimeError(f"storage_objects size/hash mismatch for {entry.object_key!r}")
            if entry.mime_type is not None and row.mime_type != entry.mime_type:
                raise RuntimeError(f"storage_objects mime_type mismatch for {entry.object_key!r}")
            count += 1
    return count


def _validate_manifest_object_key(object_key: str) -> None:
    if "\\" in object_key or ".." in object_key.split("/"):
        raise ValueError(f"refusing unsafe object_key: {object_key}")
    if object_key.startswith(PRIVATE_DATA_PREFIX) or object_key.startswith(POSTGRES_BACKUP_PREFIX):
        return
    raise ValueError(f"refusing non-private-sync object_key: {object_key}")


async def async_main() -> None:
    args = parse_args()
    entries = load_manifest(args.manifest, limit=args.limit)
    await verify_entries(entries)


if __name__ == "__main__":
    asyncio.run(async_main())
