# Status: real

from pathlib import Path

from scripts.sync_cos_private_data import (
    InventoryEntry,
    classify_relpath,
    object_key_for_entry,
    rights_note_for_classification,
)


def test_classify_allowed_runtime_assets() -> None:
    assert (
        classify_relpath("data/storage/course_websec/mineru/book/assets/page_001.png")
        == "allowed_runtime_asset"
    )
    assert (
        classify_relpath("data/processed/mineru/book/assets/page_001.jpg")
        == "allowed_runtime_asset"
    )


def test_classify_explicit_private_textbook_sources() -> None:
    assert classify_relpath("data/raw/pdf/websec.pdf") == "allowed_private_textbook"
    assert (
        classify_relpath("data/storage/course_websec/mineru/websec-textbook/full.md")
        == "allowed_private_textbook"
    )
    assert classify_relpath("data/processed/mineru/websec-textbook/full.md") == (
        "allowed_private_textbook"
    )


def test_classify_permanently_blocked_sources() -> None:
    assert classify_relpath("backend/.env") == "blocked_secret"
    assert classify_relpath("SecretKey.csv") == "blocked_secret"
    assert classify_relpath("account.csv") == "blocked_secret"
    assert classify_relpath(".codegraph/codegraph.db") == "blocked_tool_cache"
    assert classify_relpath("local.sqlite") == "blocked_pii_or_platform_raw"
    assert classify_relpath("data/raw/mediacrawler/raw.json") == "blocked_pii_or_platform_raw"
    assert classify_relpath("data/storage/course_websec/mediacrawler/raw.json") == (
        "blocked_pii_or_platform_raw"
    )
    assert classify_relpath("data/reports/raw.md") == "blocked_pii_or_platform_raw"
    assert classify_relpath("data/demo/smoke/backend.log") == "blocked_unknown"


def test_private_team_sync_object_key_uses_repo_relative_path() -> None:
    entry = InventoryEntry(
        source_path=Path("unused"),
        source_relpath="data/processed/mineru/book/assets/page_001.jpg",
        classification="allowed_runtime_asset",
        is_git_ignored=True,
    )

    assert object_key_for_entry(entry) == (
        "private/team-sync/data/data/processed/mineru/book/assets/page_001.jpg"
    )


def test_db_backup_object_key_uses_postgres_backup_prefix() -> None:
    entry = InventoryEntry(
        source_path=Path("unused"),
        source_relpath="dumps/securehub.dump",
        classification="allowed_db_backup",
        is_git_ignored=True,
    )

    assert object_key_for_entry(entry, today=__import__("datetime").date(2026, 7, 9)) == (
        "backups/postgres/2026-07-09/securehub.dump"
    )


def test_textbook_rights_note_is_private_only() -> None:
    assert "no runtime exposure" in rights_note_for_classification("allowed_private_textbook")
