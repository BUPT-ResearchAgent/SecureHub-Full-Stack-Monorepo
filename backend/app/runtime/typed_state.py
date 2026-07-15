# Status: real

"""Typed, minimal collaboration state for framework-neutral workflows.

The runtime never uses an agent chat transcript as a transport.  This module
keeps the durable collaboration surface intentionally small: typed node values,
ArtifactRef/EvidenceRef lineage, approved decisions, and defect history.
"""

from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from typing import Any

from pydantic import BaseModel, Field

from app.runtime.contracts import ArtifactRef, EvidenceRef


class WorkflowNodeState(BaseModel):
    """The auditable output of one node attempt, without raw provider text."""

    output: dict[str, Any] = Field(default_factory=dict)
    step_attempt_id: str | None = None
    agent_run_id: str | None = None
    provider_call_id: str | None = None
    stream_attempt: int | None = None
    evidence_snapshot_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    quality_score: float | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    lineage: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_payload(cls, value: "WorkflowNodeState | dict[str, Any]") -> "WorkflowNodeState":
        if isinstance(value, cls):
            return value
        payload = dict(value)
        output = payload.get("output")
        if not isinstance(output, dict):
            output = {}
        evidence_refs = payload.get("evidence_refs") or []
        artifact_refs = payload.get("artifact_refs") or []
        evidence_snapshot_ids = payload.get("evidence_snapshot_ids") or [
            item.get("evidence_snapshot_id")
            for item in evidence_refs
            if isinstance(item, dict) and item.get("evidence_snapshot_id")
        ]
        return cls(
            output=output,
            step_attempt_id=_string(payload.get("step_attempt_id")),
            agent_run_id=_string(payload.get("agent_run_id")),
            provider_call_id=_string(payload.get("provider_call_id")),
            stream_attempt=_integer(payload.get("stream_attempt")),
            evidence_snapshot_ids=[str(item) for item in evidence_snapshot_ids if item is not None],
            evidence_refs=evidence_refs,
            artifact_refs=artifact_refs,
            quality_score=_number(payload.get("quality_score")),
            usage=dict(payload.get("usage") or {}),
            lineage=dict(payload.get("lineage") or {}),
        )


class TypedWorkflowState(MutableMapping[str, dict[str, Any]]):
    """A mapping-compatible typed state container.

    Mapping compatibility keeps existing input mappers concise while the
    container guarantees that checkpoints and projections carry references,
    not implicit prompt/chat history.  A projection is freshly materialised so
    a mapper cannot mutate shared state by accident.
    """

    def __init__(
        self,
        values: dict[str, WorkflowNodeState | dict[str, Any]] | None = None,
        *,
        workflow_schema_version: str = "v1",
        approved_decisions: dict[str, Any] | None = None,
        defect_history: list[dict[str, Any]] | None = None,
    ) -> None:
        self.workflow_schema_version = workflow_schema_version
        self.approved_decisions = dict(approved_decisions or {})
        self.defect_history = [dict(item) for item in (defect_history or [])]
        self._values: dict[str, WorkflowNodeState] = {}
        for key, value in (values or {}).items():
            self._values[str(key)] = WorkflowNodeState.from_payload(value)

    def __getitem__(self, key: str) -> dict[str, Any]:
        return self._values[key].model_dump(mode="json")

    def __setitem__(self, key: str, value: dict[str, Any]) -> None:
        self._values[str(key)] = WorkflowNodeState.from_payload(value)

    def __delitem__(self, key: str) -> None:
        del self._values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def pop(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        value = self._values.pop(key, None)
        if value is None:
            return default
        return value.model_dump(mode="json")

    def project(self, node_ids: tuple[str, ...] | None) -> dict[str, dict[str, Any]]:
        """Return only explicitly authorised upstream collaboration records."""
        names = tuple(self._values) if node_ids is None else node_ids
        return {
            name: self._values[name].model_dump(mode="json")
            for name in names
            if name in self._values
        }

    def record_defects(self, defects: list[dict[str, Any]], *, node_id: str) -> bool:
        """Persist a normalised defect signature and report repeated defects."""
        normalized = [
            {
                "code": str(item.get("code") or item.get("taxonomy") or "unknown"),
                "message": str(item.get("message") or item.get("reason") or "")[:400],
                "target": str(item.get("target_node") or item.get("resource_type") or ""),
            }
            for item in defects
            if isinstance(item, dict)
        ]
        normalized.sort(key=lambda item: (item["code"], item["target"]))
        signature = {"node_id": node_id, "defects": normalized}
        repeat_key = [(item["code"], item["target"]) for item in normalized]
        repeated = any(
            str(previous.get("node_id") or "") == node_id
            and [
                (str(item.get("code") or ""), str(item.get("target") or ""))
                for item in previous.get("defects", [])
                if isinstance(item, dict)
            ] == repeat_key
            for previous in self.defect_history
            if isinstance(previous, dict)
        )
        self.defect_history.append(signature)
        return repeated

    def latest_defect_signature(self) -> dict[str, Any] | None:
        """Return a detached copy of the latest durable QualityCheck feedback."""
        for item in reversed(self.defect_history):
            if not isinstance(item, dict):
                continue
            defects = item.get("defects")
            if not isinstance(defects, list):
                continue
            return {
                "node_id": str(item.get("node_id") or ""),
                "defects": [dict(defect) for defect in defects if isinstance(defect, dict)],
            }
        return None

    def checkpoint_payload(self) -> dict[str, Any]:
        return {
            "workflow_schema_version": self.workflow_schema_version,
            "node_outputs": {
                key: value.model_dump(mode="json") for key, value in self._values.items()
            },
            "approved_decisions": dict(self.approved_decisions),
            "defect_history": [dict(item) for item in self.defect_history],
        }

    @classmethod
    def from_checkpoint(cls, value: dict[str, Any] | None) -> "TypedWorkflowState":
        payload = dict(value or {})
        if "node_outputs" in payload:
            values = payload.get("node_outputs") or {}
            return cls(
                values if isinstance(values, dict) else {},
                workflow_schema_version=str(payload.get("workflow_schema_version") or "v1"),
                approved_decisions=payload.get("approved_decisions") if isinstance(payload.get("approved_decisions"), dict) else {},
                defect_history=payload.get("defect_history") if isinstance(payload.get("defect_history"), list) else [],
            )
        return cls(payload)


def _string(value: Any) -> str | None:
    return str(value) if value is not None else None


def _integer(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


__all__ = ["TypedWorkflowState", "WorkflowNodeState"]
