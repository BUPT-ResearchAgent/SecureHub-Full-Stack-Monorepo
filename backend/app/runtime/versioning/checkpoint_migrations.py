# Status: real

"""Explicit checkpoint schema migrations; no silent state reinterpretation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


CheckpointMigration = Callable[[dict[str, Any]], dict[str, Any]]


class CheckpointMigrationRegistry:
    def __init__(self) -> None:
        self._migrations: dict[tuple[str, str], CheckpointMigration] = {}

    def register(
        self, from_version: str, to_version: str, migration: CheckpointMigration
    ) -> None:
        key = (str(from_version), str(to_version))
        if key in self._migrations:
            raise ValueError(f"checkpoint migration already registered: {key!r}")
        self._migrations[key] = migration

    def can_migrate(self, from_version: str, to_version: str) -> bool:
        return (str(from_version), str(to_version)) in self._migrations

    def migrate(self, from_version: str, to_version: str, state: dict[str, Any]) -> dict[str, Any]:
        try:
            migration = self._migrations[(str(from_version), str(to_version))]
        except KeyError as exc:
            raise ValueError(
                f"no explicit checkpoint migration: {from_version!r} -> {to_version!r}"
            ) from exc
        return migration(dict(state))


__all__ = ["CheckpointMigration", "CheckpointMigrationRegistry"]
