# Status: real

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from hashlib import sha256
import json
import mimetypes
from pathlib import Path
import subprocess
import sys

from sqlalchemy import text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.db import models  # noqa: F401
from app.db.session import get_sessionmaker
from app.services.storage.storage_service import StorageService


DEFAULT_MANIFEST = REPO_ROOT / "data" / "manifests" / "cos_private_team_sync_manifest.jsonl"
MIGRATION_BATCH = "7-COS-3-private-sync"
DEFAULT_RIGHTS_NOTE = "private-team-sync-only; no public distribution"
TEXTBOOK_RIGHTS_NOTE = (
    "private-team-sync-only; proprietary educational material; "
    "no public distribution; no runtime exposure"
)
DB_BACKUP_RIGHTS_NOTE = "private-team-sync-only; database backup; no public distribution"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
TEXTBOOK_SUFFIXES = {".pdf"}
DB_BACKUP_SUFFIXES = {".dump", ".backup"}
BLOCKED_SECRET_NAMES = {"secretkey.csv", "account.csv"}
BLOCKED_SECRET_SUFFIXES = {".pem", ".key", ".p12"}
BLOCKED_DB_SUFFIXES = {".sqlite", ".sqlite3", ".db", ".db-wal", ".db-shm"}
BLOCKED_SCAN_ROOTS = (
    ".codegraph",
    "data/raw/mediacrawler",
    "data/storage/course_websec/mediacrawler",
    "data/reports",
)
PRIVATE_DATA_PREFIX = "private/team-sync/data"
POSTGRES_BACKUP_PREFIX = "backups/postgres"


@dataclass(frozen=True, slots=True)
class InventoryEntry:
    source_path: Path
    source_relpath: str
    classification: str
    is_git_ignored: bool

    @property
    def is_allowed(self) -> bool:
        return self.classification.startswith("allowed_")


@dataclass(frozen=True, slots=True)
class UploadCandidate:
    source_path: Path
    source_relpath: str
    classification: str
    object_key: str
    size_bytes: int
    sha256: str
    mime_type: str
    rights_note: str

    def manifest_row(self, *, bucket: str, created_at: str) -> dict[str, object]:
        return {
            "provider": "cos",
            "bucket": bucket,
            "object_key": self.object_key,
            "source_relpath": self.source_relpath,
            "classification": self.classification,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "mime_type": self.mime_type,
            "rights_note": self.rights_note,
            "migration_batch": MIGRATION_BATCH,
            "created_at": created_at,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory and sync Git-ignored private team data to Tencent COS."
    )
    parser.add_argument("--inventory-only", action="store_true", help="Print classification counts only.")
    parser.add_argument("--dry-run", action="store_true", help="Print upload plan without COS/db/manifest writes.")
    parser.add_argument("--upload", action="store_true", help="Upload selected allowlist files to COS.")
    parser.add_argument("--verify", action="store_true", help="After upload, HEAD and GET each object and verify hash.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum upload candidates to process.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="JSONL manifest path. Defaults to data/manifests/cos_private_team_sync_manifest.jsonl.",
    )
    parser.add_argument(
        "--include-textbook-private",
        action="store_true",
        help="Include private textbook PDFs/full.md under private/team-sync.",
    )
    parser.add_argument(
        "--include-db-dump",
        action="store_true",
        help="Include ignored .dump/.backup files under backups/postgres.",
    )
    parser.add_argument(
        "--fail-on-blocked",
        action="store_true",
        help="Exit non-zero if any blocked ignored/private path is discovered.",
    )
    return parser.parse_args()


def discover_inventory() -> list[InventoryEntry]:
    candidate_relpaths = set(_discover_candidate_paths())
    ignored_relpaths = _git_check_ignored(candidate_relpaths)
    blocked_relpaths = set(_discover_blocked_existing_paths())
    entries: list[InventoryEntry] = []
    for relpath in sorted(candidate_relpaths | blocked_relpaths):
        path = _repo_path(relpath)
        if not path.is_file():
            continue
        entries.append(
            InventoryEntry(
                source_path=path,
                source_relpath=relpath,
                classification=classify_relpath(relpath),
                is_git_ignored=relpath in ignored_relpaths,
            )
        )
    return entries


def classify_relpath(relpath: str) -> str:
    normalized = _normalize_relpath(relpath)
    lowered = normalized.lower()
    name = lowered.rsplit("/", 1)[-1]
    suffix = _suffix(lowered)

    if (
        name == ".env"
        or name.startswith(".env.")
        or name in BLOCKED_SECRET_NAMES
        or suffix in BLOCKED_SECRET_SUFFIXES
    ):
        return "blocked_secret"
    if lowered.startswith(".codegraph/"):
        return "blocked_tool_cache"
    if (
        suffix in BLOCKED_DB_SUFFIXES
        or lowered.startswith("data/raw/mediacrawler/")
        or lowered.startswith("data/storage/course_websec/mediacrawler/")
        or lowered.startswith("data/reports/")
    ):
        return "blocked_pii_or_platform_raw"
    if _is_allowed_runtime_asset(lowered):
        return "allowed_runtime_asset"
    if _is_allowed_private_textbook(lowered):
        return "allowed_private_textbook"
    if _is_allowed_db_backup(lowered):
        return "allowed_db_backup"
    return "blocked_unknown"


def select_upload_candidates(
    inventory: Iterable[InventoryEntry],
    *,
    include_textbook_private: bool,
    include_db_dump: bool,
    limit: int | None,
) -> list[UploadCandidate]:
    if limit is not None and limit < 0:
        raise ValueError("--limit must be >= 0")

    selected: list[UploadCandidate] = []
    for entry in inventory:
        if not entry.is_git_ignored or not entry.is_allowed:
            continue
        if entry.classification == "allowed_private_textbook" and not include_textbook_private:
            continue
        if entry.classification == "allowed_db_backup" and not include_db_dump:
            continue
        candidate = build_upload_candidate(entry)
        _validate_target_key(candidate.object_key, candidate.classification)
        selected.append(candidate)
        if limit is not None and len(selected) >= limit:
            break
    return selected


def build_upload_candidate(entry: InventoryEntry) -> UploadCandidate:
    digest = sha256(entry.source_path.read_bytes()).hexdigest()
    size_bytes = entry.source_path.stat().st_size
    mime_type = mimetypes.guess_type(entry.source_path.name)[0] or "application/octet-stream"
    return UploadCandidate(
        source_path=entry.source_path,
        source_relpath=entry.source_relpath,
        classification=entry.classification,
        object_key=object_key_for_entry(entry),
        size_bytes=size_bytes,
        sha256=digest,
        mime_type=mime_type,
        rights_note=rights_note_for_classification(entry.classification),
    )


def object_key_for_entry(entry: InventoryEntry, *, today: date | None = None) -> str:
    if entry.classification == "allowed_db_backup":
        day = (today or date.today()).isoformat()
        return f"{POSTGRES_BACKUP_PREFIX}/{day}/{Path(entry.source_relpath).name}"
    return f"{PRIVATE_DATA_PREFIX}/{entry.source_relpath}"


def rights_note_for_classification(classification: str) -> str:
    if classification == "allowed_private_textbook":
        return TEXTBOOK_RIGHTS_NOTE
    if classification == "allowed_db_backup":
        return DB_BACKUP_RIGHTS_NOTE
    return DEFAULT_RIGHTS_NOTE


async def upload_and_verify(candidates: list[UploadCandidate], *, manifest_path: Path, verify: bool) -> None:
    if not candidates:
        print("COS_PRIVATE_SYNC_UPLOAD_SKIPPED count=0 reason=no_allowlist_candidates")
        return

    settings = get_settings()
    if settings.STORAGE_PROVIDER != "cos":
        raise SystemExit("Set STORAGE_PROVIDER=cos before running private COS sync upload.")

    rows: list[dict[str, object]] = []
    created_at = datetime.now(UTC).isoformat()
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            await session.execute(text("SELECT 1"))
        except Exception:
            raise SystemExit(
                "Database preflight failed before COS upload; "
                "start the configured database and rerun the command."
            )
        storage = StorageService(session, settings=settings)
        for index, candidate in enumerate(candidates, start=1):
            _validate_target_key(candidate.object_key, candidate.classification)
            print(
                "COS_PRIVATE_SYNC_OBJECT_START "
                f"index={index} total={len(candidates)} object_key={candidate.object_key}",
                flush=True,
            )
            content = candidate.source_path.read_bytes()
            if sha256(content).hexdigest() != candidate.sha256:
                raise RuntimeError(f"source hash changed before upload: {candidate.source_relpath}")
            await storage.put_bytes(
                object_key=candidate.object_key,
                content=content,
                mime_type=candidate.mime_type,
                original_filename=candidate.source_path.name,
                metadata={
                    "classification": candidate.classification,
                    "migration_batch": MIGRATION_BATCH,
                    "rights_note": candidate.rights_note,
                    "source_relpath": candidate.source_relpath,
                },
            )
            if not await storage.exists(candidate.object_key):
                raise RuntimeError(f"COS HEAD failed for object_key={candidate.object_key!r}")
            if verify:
                downloaded = await storage.get_bytes(candidate.object_key)
                if downloaded is None:
                    raise RuntimeError(f"COS GET returned empty object for object_key={candidate.object_key!r}")
                if len(downloaded) != candidate.size_bytes:
                    raise RuntimeError(f"COS GET size mismatch for object_key={candidate.object_key!r}")
                if sha256(downloaded).hexdigest() != candidate.sha256:
                    raise RuntimeError(f"COS GET hash mismatch for object_key={candidate.object_key!r}")
            if not candidate.source_path.exists():
                raise RuntimeError(f"local source disappeared: {candidate.source_relpath}")
            rows.append(candidate.manifest_row(bucket=settings.COS_BUCKET, created_at=created_at))
            print(
                "COS_PRIVATE_SYNC_OBJECT_OK "
                f"index={index} total={len(candidates)} object_key={candidate.object_key}",
                flush=True,
            )
        await session.commit()

    write_manifest(manifest_path, rows)
    print(f"COS_PRIVATE_SYNC_UPLOAD_OK count={len(rows)}")
    print(f"COS_PRIVATE_SYNC_HEAD_OK count={len(rows)}")
    if verify:
        print(f"COS_PRIVATE_SYNC_GET_HASH_OK count={len(rows)}")
    print(f"STORAGE_OBJECTS_PRIVATE_SYNC_UPSERT_OK count={len(rows)}")
    print(f"LOCAL_PRIVATE_SYNC_SOURCE_OK count={len(rows)}")
    print(f"MANIFEST_PRIVATE_SYNC_WRITE_OK count={len(rows)}")


def dry_run(candidates: list[UploadCandidate]) -> None:
    for candidate in candidates:
        print(
            "DRY_RUN_PRIVATE_SYNC "
            f"source_relpath={candidate.source_relpath} "
            f"object_key={candidate.object_key} "
            f"classification={candidate.classification} "
            f"size_bytes={candidate.size_bytes} "
            f"mime_type={candidate.mime_type} "
            f"sha256={candidate.sha256}"
        )
    if not candidates:
        print("COS_PRIVATE_SYNC_DRY_RUN_EMPTY reason=no_allowlist_candidates")
    print(f"COS_PRIVATE_SYNC_DRY_RUN count={len(candidates)}")


def print_inventory_summary(entries: list[InventoryEntry]) -> Counter[str]:
    counts = Counter(entry.classification for entry in entries)
    ignored_count = sum(1 for entry in entries if entry.is_git_ignored)
    print(f"GIT_IGNORED_DISCOVERY count={ignored_count}")
    print(f"PRIVATE_SYNC_INVENTORY_TOTAL count={len(entries)}")
    for classification in (
        "allowed_runtime_asset",
        "allowed_private_textbook",
        "allowed_db_backup",
        "blocked_secret",
        "blocked_pii_or_platform_raw",
        "blocked_tool_cache",
        "blocked_unknown",
    ):
        print(f"PRIVATE_SYNC_INVENTORY {classification}={counts.get(classification, 0)}")
    return counts


def write_manifest(manifest_path: Path, rows: Iterable[dict[str, object]]) -> None:
    path = _resolve_manifest_path(manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _discover_candidate_paths() -> list[str]:
    relpaths: list[str] = []
    for root_relpath in ("data", "dumps"):
        root = _repo_path(root_relpath)
        if root.exists():
            relpaths.extend(path.relative_to(REPO_ROOT).as_posix() for path in root.rglob("*") if path.is_file())

    for pattern in ("*.dump", "*.backup", ".env", ".env.*", "SecretKey.csv", "account.csv"):
        relpaths.extend(path.relative_to(REPO_ROOT).as_posix() for path in REPO_ROOT.glob(pattern) if path.is_file())

    for root_relpath in ("backend", "frontend"):
        root = _repo_path(root_relpath)
        if not root.exists():
            continue
        for pattern in (".env", ".env.*", "SecretKey.csv", "account.csv"):
            relpaths.extend(path.relative_to(REPO_ROOT).as_posix() for path in root.glob(pattern) if path.is_file())

    return [_normalize_relpath(relpath) for relpath in relpaths]


def _git_check_ignored(relpaths: Iterable[str]) -> set[str]:
    items = sorted({_normalize_relpath(relpath) for relpath in relpaths})
    if not items:
        return set()
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "check-ignore", "-z", "--stdin"],
        input="\0".join(items) + "\0",
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode not in {0, 1}:
        raise RuntimeError(f"git check-ignore failed: {result.stderr.strip()}")
    return {_normalize_relpath(item) for item in result.stdout.split("\0") if item}


def _discover_blocked_existing_paths() -> list[str]:
    relpaths: list[str] = []
    for root_relpath in BLOCKED_SCAN_ROOTS:
        root = _repo_path(root_relpath)
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                relpaths.append(path.relative_to(REPO_ROOT).as_posix())
    return relpaths


def _is_allowed_runtime_asset(lowered: str) -> bool:
    suffix = _suffix(lowered)
    if suffix not in IMAGE_SUFFIXES or "/assets/" not in lowered:
        return False
    return lowered.startswith("data/storage/course_websec/mineru/") or lowered.startswith(
        "data/processed/mineru/"
    )


def _is_allowed_private_textbook(lowered: str) -> bool:
    if lowered.startswith("data/raw/pdf/") and lowered.endswith(".pdf"):
        return True
    if lowered.startswith("data/storage/course_websec/mineru/") and lowered.endswith(".pdf"):
        return True
    if lowered.startswith("data/storage/course_websec/mineru/") and lowered.endswith("/full.md"):
        return True
    if lowered.startswith("data/processed/mineru/") and lowered.endswith("/full.md"):
        return True
    return False


def _is_allowed_db_backup(lowered: str) -> bool:
    suffix = _suffix(lowered)
    return suffix in DB_BACKUP_SUFFIXES and (
        "/" not in lowered or lowered.startswith("dumps/") or lowered.count("/") == 0
    )


def _validate_target_key(object_key: str, classification: str) -> None:
    if "\\" in object_key or ".." in object_key.split("/"):
        raise ValueError(f"refusing unsafe object_key: {object_key}")
    if classification == "allowed_db_backup":
        if not object_key.startswith(f"{POSTGRES_BACKUP_PREFIX}/") or _suffix(object_key) not in DB_BACKUP_SUFFIXES:
            raise ValueError(f"refusing non-postgres-backup object_key: {object_key}")
        return
    if not object_key.startswith(f"{PRIVATE_DATA_PREFIX}/data/"):
        raise ValueError(f"refusing non-private-team-sync object_key: {object_key}")
    lowered = object_key.lower()
    if lowered.startswith("runtime/") or lowered.startswith("tmp/") or lowered.startswith("backups/"):
        raise ValueError(f"refusing reserved object_key prefix: {object_key}")


def _repo_path(relpath: str) -> Path:
    return (REPO_ROOT / _normalize_relpath(relpath)).resolve()


def _resolve_manifest_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def _normalize_relpath(relpath: str) -> str:
    normalized = relpath.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.lstrip("/")
    if normalized.startswith("../") or "/../" in normalized:
        raise ValueError(f"refusing path outside repository: {relpath}")
    return normalized


def _suffix(relpath: str) -> str:
    path = relpath.lower()
    for suffix in (".db-wal", ".db-shm"):
        if path.endswith(suffix):
            return suffix
    return Path(path).suffix


async def async_main() -> None:
    args = parse_args()
    inventory = discover_inventory()
    counts = print_inventory_summary(inventory)
    blocked_count = sum(
        count for classification, count in counts.items() if classification.startswith("blocked_")
    )
    if args.fail_on_blocked and blocked_count:
        raise SystemExit(f"blocked files discovered; refusing to continue count={blocked_count}")
    if args.inventory_only and not args.dry_run and not args.upload:
        return

    candidates = select_upload_candidates(
        inventory,
        include_textbook_private=args.include_textbook_private,
        include_db_dump=args.include_db_dump,
        limit=args.limit,
    )
    if args.dry_run:
        dry_run(candidates)
    if args.upload:
        await upload_and_verify(candidates, manifest_path=args.manifest, verify=args.verify)
    if not args.inventory_only and not args.dry_run and not args.upload:
        print("No mode selected; inventory summary only. Use --dry-run or --upload to proceed.")


if __name__ == "__main__":
    asyncio.run(async_main())
