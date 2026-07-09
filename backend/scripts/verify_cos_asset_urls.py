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

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.services.storage.provider_factory import create_storage_provider


DEFAULT_MANIFEST = REPO_ROOT / "data" / "manifests" / "cos_runtime_assets_sample.jsonl"
TARGET_PREFIX = "runtime/course_websec/mineru_ingested/"


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    object_key: str
    sha256: str
    size_bytes: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify COS sample asset signed URLs without printing URLs.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="JSONL manifest path. Defaults to data/manifests/cos_runtime_assets_sample.jsonl.",
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
            if not object_key.startswith(TARGET_PREFIX) or "/assets/" not in object_key:
                raise ValueError(f"refusing non-runtime asset object_key: {object_key}")
            entries.append(
                ManifestEntry(
                    object_key=object_key,
                    sha256=str(row["sha256"]),
                    size_bytes=int(row["size_bytes"]),
                )
            )
    return entries


async def verify_entries(entries: list[ManifestEntry]) -> None:
    settings = get_settings()
    if settings.STORAGE_PROVIDER != "cos":
        raise SystemExit("Set STORAGE_PROVIDER=cos before verifying COS asset URLs.")

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

    print(f"COS_ASSET_URL_OK count={url_ok}")
    print(f"COS_ASSET_HASH_OK count={hash_ok}")


async def async_main() -> None:
    args = parse_args()
    entries = load_manifest(args.manifest, limit=args.limit)
    await verify_entries(entries)


if __name__ == "__main__":
    asyncio.run(async_main())
