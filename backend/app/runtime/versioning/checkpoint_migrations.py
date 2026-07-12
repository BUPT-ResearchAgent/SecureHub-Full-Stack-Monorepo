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


def build_runtime_checkpoint_migrations() -> CheckpointMigrationRegistry:
    """Return the reviewed migrations shipped with this Runtime build.

    ``v1`` checkpoints stored a flat node mapping.  ``typed-state-v1`` stores
    exactly the same node data below ``node_outputs`` with explicit empty
    decision/defect collections.  The function is deliberately narrow: new
    schema pairs must be registered here rather than being guessed by resume.
    """
    registry = CheckpointMigrationRegistry()

    def v1_to_typed_state(state: dict[str, Any]) -> dict[str, Any]:
        if "node_outputs" in state:
            node_outputs = state.get("node_outputs")
            if not isinstance(node_outputs, dict):
                raise ValueError("v1 checkpoint node_outputs must be an object")
            return {
                "workflow_schema_version": "typed-state-v1",
                "node_outputs": dict(node_outputs),
                "approved_decisions": dict(state.get("approved_decisions") or {}),
                "defect_history": list(state.get("defect_history") or []),
            }
        return {
            "workflow_schema_version": "typed-state-v1",
            "node_outputs": dict(state),
            "approved_decisions": {},
            "defect_history": [],
        }

    registry.register("v1", "typed-state-v1", v1_to_typed_state)
    return registry


__all__ = [
    "CheckpointMigration",
    "CheckpointMigrationRegistry",
    "build_runtime_checkpoint_migrations",
]
