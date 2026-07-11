# Status: real

"""Recovery decisions for expired leases and provider unknown outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.db.models.workflow_runtime import WorkflowCheckpoint, WorkflowRun
from app.runtime.execution.lease import Lease
from app.runtime.persistence.checkpoint_store import CheckpointStore
from app.runtime.persistence.provider_call_store import ProviderCallStore
from app.runtime.persistence.run_store import RunStore
from app.runtime.versioning.compatibility import CompatibilityDecision, CompatibilityPolicy


@dataclass(frozen=True, slots=True)
class RecoveryResult:
    action: str
    checkpoint: WorkflowCheckpoint | None = None
    compatibility: CompatibilityDecision | None = None
    unknown_provider_call_ids: tuple[str, ...] = ()


class RecoveryService:
    """Never auto-replays an externally unknown provider request."""

    def __init__(
        self,
        run_store: RunStore,
        checkpoint_store: CheckpointStore,
        provider_call_store: ProviderCallStore,
        *,
        compatibility_policy: CompatibilityPolicy | None = None,
    ) -> None:
        self.run_store = run_store
        self.checkpoints = checkpoint_store
        self.provider_calls = provider_call_store
        self.compatibility_policy = compatibility_policy

    async def prepare_resume(
        self,
        run: WorkflowRun,
        lease: Lease,
        *,
        target_semantic_version: Any | None = None,
    ) -> RecoveryResult:
        unknown_calls = await self.provider_calls.mark_started_unknown_for_run(
            run.id,
            reason="worker lease recovered before provider completion was recorded",
        )
        if unknown_calls:
            updated = await self.run_store.transition_run(
                run.id,
                expected_state_version=run.state_version,
                lease_epoch=lease.epoch,
                status="waiting_approval",
                event_type="trace",
                event_payload={
                    "code": "PROVIDER_UNKNOWN_OUTCOME",
                    "provider_call_ids": [str(call.id) for call in unknown_calls],
                    "action": "explicit_retry_or_approval_required",
                },
            )
            return RecoveryResult(
                action="waiting_approval",
                unknown_provider_call_ids=tuple(str(call.id) for call in unknown_calls),
            )

        checkpoint = await self.checkpoints.latest(run.id)
        if target_semantic_version is not None and self.compatibility_policy is not None:
            decision = self.compatibility_policy.assess(run, checkpoint, target_semantic_version)
            if decision.status == "incompatible":
                await self.run_store.transition_run(
                    run.id,
                    expected_state_version=run.state_version,
                    lease_epoch=lease.epoch,
                    status="blocked",
                    changes={
                        "error": {
                            "code": "SEMANTIC_VERSION_INCOMPATIBLE",
                            "reasons": list(decision.reasons),
                        }
                    },
                    event_type="error",
                    event_payload={
                        "code": "SEMANTIC_VERSION_INCOMPATIBLE",
                        "recoverable": False,
                    },
                )
                return RecoveryResult("blocked", checkpoint, decision)
            return RecoveryResult("resume", checkpoint, decision)
        return RecoveryResult("resume", checkpoint)


__all__ = ["RecoveryResult", "RecoveryService"]
