# Status: real

"""The one SecureHub lifecycle state machine.

Only RuntimeEngine may invoke these transitions in production.  Keeping the
rules pure makes invalid transitions easy to lock with architecture tests.
"""

from __future__ import annotations

from app.runtime.contracts import RunStatus, StepStatus, TERMINAL_RUN_STATUSES, TERMINAL_STEP_STATUSES


class InvalidStateTransition(ValueError):
    pass


_ROOT_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.QUEUED: frozenset({RunStatus.RUNNING, RunStatus.CANCELLING, RunStatus.CANCELLED, RunStatus.FAILED, RunStatus.BLOCKED}),
    RunStatus.RUNNING: frozenset({RunStatus.REWORKING, RunStatus.PAUSING, RunStatus.WAITING_APPROVAL, RunStatus.CANCELLING, RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.BLOCKED}),
    RunStatus.REWORKING: frozenset({RunStatus.RUNNING, RunStatus.CANCELLING, RunStatus.BLOCKED, RunStatus.FAILED}),
    RunStatus.PAUSING: frozenset({RunStatus.PAUSED, RunStatus.CANCELLING, RunStatus.FAILED}),
    RunStatus.PAUSED: frozenset({RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.CANCELLING, RunStatus.BLOCKED}),
    RunStatus.WAITING_APPROVAL: frozenset({RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.CANCELLING, RunStatus.BLOCKED}),
    RunStatus.CANCELLING: frozenset({RunStatus.CANCELLED, RunStatus.FAILED, RunStatus.BLOCKED}),
    RunStatus.CANCELLED: frozenset(),
    RunStatus.SUCCEEDED: frozenset(),
    RunStatus.FAILED: frozenset(),
    RunStatus.BLOCKED: frozenset(),
}

_STEP_TRANSITIONS: dict[StepStatus, frozenset[StepStatus]] = {
    StepStatus.PENDING: frozenset({StepStatus.READY, StepStatus.SKIPPED, StepStatus.CANCELLED}),
    StepStatus.READY: frozenset({StepStatus.RUNNING, StepStatus.SKIPPED, StepStatus.CANCELLED}),
    StepStatus.RUNNING: frozenset({StepStatus.SUCCEEDED, StepStatus.FAILED, StepStatus.BLOCKED, StepStatus.CANCELLED}),
    StepStatus.SUCCEEDED: frozenset(),
    StepStatus.FAILED: frozenset(),
    StepStatus.BLOCKED: frozenset(),
    StepStatus.CANCELLED: frozenset(),
    StepStatus.SKIPPED: frozenset(),
}


class SecureHubStateMachine:
    """Pure state validation; persistence CAS and side effects belong elsewhere."""

    @staticmethod
    def is_terminal_run(status: str | RunStatus) -> bool:
        return RunStatus(status) in TERMINAL_RUN_STATUSES

    @staticmethod
    def is_terminal_step(status: str | StepStatus) -> bool:
        return StepStatus(status) in TERMINAL_STEP_STATUSES

    @staticmethod
    def assert_run_transition(current: str | RunStatus, target: str | RunStatus) -> None:
        before = RunStatus(current)
        after = RunStatus(target)
        if before == after:
            return
        if after not in _ROOT_TRANSITIONS[before]:
            raise InvalidStateTransition(f"invalid root transition: {before.value} -> {after.value}")

    @staticmethod
    def assert_step_transition(current: str | StepStatus, target: str | StepStatus) -> None:
        before = StepStatus(current)
        after = StepStatus(target)
        if before == after:
            return
        if after not in _STEP_TRANSITIONS[before]:
            raise InvalidStateTransition(f"invalid step transition: {before.value} -> {after.value}")


__all__ = ["InvalidStateTransition", "SecureHubStateMachine"]
