# Status: real

"""Version compatibility checks used before a durable run resumes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.db.models.workflow_runtime import WorkflowCheckpoint, WorkflowRun
from app.runtime.contracts import RuntimeSemanticVersion
from app.runtime.versioning.checkpoint_migrations import CheckpointMigrationRegistry


Compatibility = Literal["compatible", "migratable", "incompatible"]


@dataclass(frozen=True, slots=True)
class CompatibilityDecision:
    status: Compatibility
    reasons: tuple[str, ...] = ()

    @property
    def can_resume(self) -> bool:
        return self.status in {"compatible", "migratable"}


class CompatibilityPolicy:
    """Compares fixed runtime semantics, never guessing a safe upgrade."""

    def __init__(self, migrations: CheckpointMigrationRegistry | None = None) -> None:
        self.migrations = migrations or CheckpointMigrationRegistry()

    def assess(
        self,
        run: WorkflowRun,
        checkpoint: WorkflowCheckpoint | None,
        target: RuntimeSemanticVersion,
    ) -> CompatibilityDecision:
        root_mismatches = self._root_mismatches(run, target)
        if root_mismatches:
            return CompatibilityDecision("incompatible", tuple(root_mismatches))
        if checkpoint is None:
            return CompatibilityDecision("compatible")
        checkpoint_mismatches = self._checkpoint_mismatches(checkpoint, target)
        if not checkpoint_mismatches:
            return CompatibilityDecision("compatible")
        only_schema = checkpoint_mismatches == ["checkpoint_schema_version"]
        if only_schema and self.migrations.can_migrate(
            checkpoint.checkpoint_schema_version, target.checkpoint_schema_version
        ):
            return CompatibilityDecision("migratable", tuple(checkpoint_mismatches))
        return CompatibilityDecision("incompatible", tuple(checkpoint_mismatches))

    @staticmethod
    def _root_mismatches(run: WorkflowRun, target: RuntimeSemanticVersion) -> list[str]:
        comparisons = {
            "workflow_definition_digest": (run.workflow_definition_digest, target.workflow_definition_digest),
            "catalog_version": (run.catalog_version, target.catalog_version),
            "provider_policy_version": (run.provider_policy_version, target.provider_policy_version),
            "runtime_build_sha": (run.runtime_build_sha, target.runtime_build_sha),
        }
        return [name for name, (stored, desired) in comparisons.items() if stored != desired]

    @staticmethod
    def _checkpoint_mismatches(
        checkpoint: WorkflowCheckpoint, target: RuntimeSemanticVersion
    ) -> list[str]:
        comparisons = {
            "workflow_definition_digest": (
                checkpoint.workflow_definition_digest,
                target.workflow_definition_digest,
            ),
            "catalog_version": (checkpoint.catalog_version, target.catalog_version),
            "checkpoint_schema_version": (
                checkpoint.checkpoint_schema_version,
                target.checkpoint_schema_version,
            ),
            "runtime_build_sha": (checkpoint.runtime_build_sha, target.runtime_build_sha),
        }
        return [name for name, (stored, desired) in comparisons.items() if stored != desired]


__all__ = ["CompatibilityDecision", "CompatibilityPolicy"]
