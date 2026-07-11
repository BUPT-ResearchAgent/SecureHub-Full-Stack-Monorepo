# Status: real

"""Canonical SkillDefinition and CandidateOutput contracts for RuntimeEngine."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel

from app.runtime.contracts import EvidenceRef


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    agent_name: str
    version: int
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    prompt_template: str
    prompt_version: str = "v1"
    required_ports: tuple[str, ...] = ("RetrieverPort", "ProviderPort", "EvidenceSnapshotStore")
    model_tools: tuple[str, ...] = ()
    required_domains: tuple[str, ...] = ("course_websec",)
    evidence_floor: int = 3
    guardrails: tuple[str, ...] = ("input", "retrieved_prompt", "output")
    quality_policy: Literal["none", "deterministic", "workflow_node"] = "workflow_node"
    artifact_policy: Literal["none", "after_quality_accept"] = "none"
    timeout_seconds: float = 60.0
    fallback_policy: Literal["none", "explicit-real-provider-only"] = "none"
    risk_level: Literal["low", "medium", "high"] = "low"

    def __post_init__(self) -> None:
        if not self.name or not self.agent_name or self.version < 1:
            raise ValueError("SkillDefinition requires name, agent_name, and version >= 1")
        if self.evidence_floor < 0 or self.timeout_seconds <= 0:
            raise ValueError("SkillDefinition has invalid evidence floor or timeout")
        if self.quality_policy == "workflow_node" and self.name == "QualityCheck":
            raise ValueError("QualityCheck must use quality_policy='none' to avoid recursion")

    @property
    def definition_digest(self) -> str:
        serializable = {
            "name": self.name,
            "agent_name": self.agent_name,
            "version": self.version,
            "input_model": self.input_model.__name__,
            "output_model": self.output_model.__name__,
            "prompt_version": self.prompt_version,
            "prompt_template": self.prompt_template,
            "required_ports": self.required_ports,
            "model_tools": self.model_tools,
            "required_domains": self.required_domains,
            "evidence_floor": self.evidence_floor,
            "guardrails": self.guardrails,
            "quality_policy": self.quality_policy,
            "artifact_policy": self.artifact_policy,
            "timeout_seconds": self.timeout_seconds,
            "fallback_policy": self.fallback_policy,
            "risk_level": self.risk_level,
        }
        return hashlib.sha256(
            json.dumps(serializable, ensure_ascii=True, sort_keys=True).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class CandidateOutput:
    """A strictly parsed Skill result before QualityCheck or artifact persistence."""

    output: BaseModel
    evidence: tuple[EvidenceRef, ...] = ()
    provider_call_id: str | None = None
    actual_provider: str | None = None
    actual_model: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    stream_attempt: int = 1

    def output_payload(self) -> dict[str, Any]:
        return self.output.model_dump(mode="json")


__all__ = ["CandidateOutput", "SkillDefinition"]
