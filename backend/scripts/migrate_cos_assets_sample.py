# Status: real

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
import mimetypes
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import Settings, get_settings
from app.db import models  # noqa: F401
from app.db.session import get_sessionmaker
from app.services.storage.storage_service import StorageService


ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
MIGRATION_BATCH = "7-COS-2-sample"
RIGHTS_NOTE = "internal-demo-evidence-asset; no textbook PDF/full markdown migrated"
MINERU_INGESTED_ROOT = REPO_ROOT / "data" / "storage" / "course_websec" / "mineru_ingested"
DEFAULT_MANIFEST = REPO_ROOT / "data" / "manifests" / "cos_runtime_assets_sample.jsonl"
TARGET_PREFIX = "runtime/course_websec/mineru_ingested"


@dataclass(frozen=True, slots=True)
class AssetCandidate:
    source_path: Path
    source_relpath: str
    object_key: str
    size_bytes: int
    sha256: str
    mime_type: str

    def manifest_row(self, *, bucket: str, created_at: str) -> dict[str, object]:
        return {
            "provider": "cos",
            "bucket": bucket,
            "object_key": self.object_key,
            "source_relpath": self.source_relpath,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "mime_type": self.mime_type,
            "rights_note": RIGHTS_NOTE,
            "migration_batch": MIGRATION_BATCH,
            "created_at": created_at,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate a small sample of MinerU runtime image assets to Tencent COS."
    )
    parser.add_argument("--dry-run", action="store_true", help="List candidates without upload/db/manifest writes.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum sample size. Defaults to 10.")
    parser.add_argument("--verify", action="store_true", help="GET each uploaded object and verify sha256.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="JSONL manifest path. Defaults to data/manifests/cos_runtime_assets_sample.jsonl.",
    )
    return parser.parse_args()


def discover_candidates(*, limit: int) -> list[AssetCandidate]:
    if limit < 0:
        raise ValueError("--limit must be >= 0")
    if not MINERU_INGESTED_ROOT.exists():
        return []

    files = sorted(
        path
        for path in MINERU_INGESTED_ROOT.rglob("*")
        if path.is_file()
        and path.parent.name == "assets"
        and path.suffix.lower() in ALLOWED_SUFFIXES
    )
    return [_candidate_from_path(path) for path in files[:limit]]


def _candidate_from_path(path: Path) -> AssetCandidate:
    rel_to_ingested = path.relative_to(MINERU_INGESTED_ROOT).as_posix()
    source_relpath = path.relative_to(REPO_ROOT).as_posix()
    digest = sha256(path.read_bytes()).hexdigest()
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return AssetCandidate(
        source_path=path,
        source_relpath=source_relpath,
        object_key=f"{TARGET_PREFIX}/{rel_to_ingested}",
        size_bytes=path.stat().st_size,
        sha256=digest,
        mime_type=mime_type,
    )


async def migrate(candidates: list[AssetCandidate], *, manifest_path: Path, verify: bool) -> None:
    settings = get_settings()
    if settings.STORAGE_PROVIDER != "cos":
        raise SystemExit("Set STORAGE_PROVIDER=cos before running COS asset migration.")

    rows: list[dict[str, object]] = []
    created_at = datetime.now(UTC).isoformat()
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        storage = StorageService(session, settings=settings)
        for candidate in candidates:
            _validate_target_key(candidate.object_key)
            content = candidate.source_path.read_bytes()
            await storage.put_bytes(
                object_key=candidate.object_key,
                content=content,
                mime_type=candidate.mime_type,
                original_filename=candidate.source_path.name,
                metadata={
                    "migration_batch": MIGRATION_BATCH,
                    "rights_note": RIGHTS_NOTE,
                    "source_relpath": candidate.source_relpath,
                },
            )
            if not await storage.exists(candidate.object_key):
                raise RuntimeError(f"COS HEAD failed for object_key={candidate.object_key!r}")
            if verify:
                downloaded = await storage.get_bytes(candidate.object_key)
                downloaded_hash = sha256(downloaded or b"").hexdigest()
                if downloaded_hash != candidate.sha256:
                    raise RuntimeError(f"COS GET hash mismatch for object_key={candidate.object_key!r}")
            if not candidate.source_path.exists():
                raise RuntimeError(f"Local source disappeared: {candidate.source_relpath}")
            rows.append(candidate.manifest_row(bucket=settings.COS_BUCKET, created_at=created_at))
        await session.commit()

    write_manifest(manifest_path, rows)
    print(f"COS_ASSET_UPLOAD_OK count={len(rows)}")
    print(f"COS_ASSET_HEAD_OK count={len(rows)}")
    if verify:
        print(f"COS_ASSET_GET_HASH_OK count={len(rows)}")
    print(f"STORAGE_OBJECTS_UPSERT_OK count={len(rows)}")
    print(f"LOCAL_SOURCE_OK count={len(rows)}")
    print(f"MANIFEST_WRITE_OK count={len(rows)}")


def write_manifest(manifest_path: Path, rows: Iterable[dict[str, object]]) -> None:
    manifest_path = _resolve_manifest_path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def dry_run(candidates: list[AssetCandidate]) -> None:
    for candidate in candidates:
        print(
            "DRY_RUN_ASSET "
            f"source_relpath={candidate.source_relpath} "
            f"object_key={candidate.object_key} "
            f"size_bytes={candidate.size_bytes} "
            f"mime_type={candidate.mime_type} "
            f"sha256={candidate.sha256}"
        )
    print(f"COS_ASSET_DRY_RUN count={len(candidates)}")


def _resolve_manifest_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def _validate_target_key(object_key: str) -> None:
    prefix = f"{TARGET_PREFIX}/"
    if not object_key.startswith(prefix) or "/assets/" not in object_key:
        raise ValueError(f"Refusing non-runtime asset object_key: {object_key}")
    lowered = object_key.lower()
    if lowered.endswith(".pdf") or lowered.endswith("/full.md"):
        raise ValueError(f"Refusing restricted object_key: {object_key}")


async def async_main() -> None:
    args = parse_args()
    candidates = discover_candidates(limit=args.limit)
    if args.dry_run:
        dry_run(candidates)
        return
    await migrate(candidates, manifest_path=args.manifest, verify=args.verify)


if __name__ == "__main__":
    asyncio.run(async_main())
