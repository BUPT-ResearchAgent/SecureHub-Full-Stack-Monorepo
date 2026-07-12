# Status: real

"""Deterministic runtime eval helpers for candidate/evidence/quality boundaries."""

from __future__ import annotations

from typing import Any

from app.runtime.contracts import QualityDefect, QualityDefectCode


def evaluate_candidate(*, candidate: dict[str, Any], evidence_snapshot_ids: list[str]) -> list[QualityDefect]:
    """Return deterministic defects without fabricating a quality acceptance."""
    defects: list[QualityDefect] = []
    if not evidence_snapshot_ids:
        defects.append(
            QualityDefect(
                code=QualityDefectCode.EVIDENCE_MISSING,
                message="candidate has no durable evidence snapshots",
            )
        )
    if not isinstance(candidate, dict) or not candidate:
        defects.append(
            QualityDefect(
                code=QualityDefectCode.SCHEMA_INVALID,
                message="candidate output is not a non-empty object",
            )
        )
    return defects


__all__ = ["evaluate_candidate"]
