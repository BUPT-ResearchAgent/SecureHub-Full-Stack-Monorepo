# Status: real

"""Framework-neutral, versioned workflow definitions.

Definitions carry graph metadata and typed mappings only.  They do not import
or expose LangGraph state, task objects, checkpoint classes, or provider SDKs.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel


InputMapper = Callable[[dict[str, Any], dict[str, Any]], BaseModel | dict[str, Any]]
OutputProjector = Callable[[BaseModel | dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class EdgeDefinition:
    source: str
    target: str
    condition: str | None = None


@dataclass(frozen=True)
class NodeDefinition:
    node_id: str
    kind: Literal["skill", "action"]
    agent_name: str | None = None
    skill_name: str | None = None
    action_name: str | None = None
    input_mapper: InputMapper | None = None
    output_projector: OutputProjector | None = None
    quality_policy: Literal["none", "deterministic", "workflow_node"] = "none"
    retry_limit: int = 0
    timeout_seconds: float = 60.0
    concurrency_group: str = "default"
    # ``None`` preserves the direct-predecessor default.  An explicit empty
    # tuple means the node intentionally receives no shared collaboration
    # output.  This keeps root input, node-local input and shared state apart.
    input_sources: tuple[str, ...] | None = None
    max_concurrency: int | None = None
    risk_level: Literal["low", "medium", "high"] = "low"
    approval_required: bool = False
    budget_tokens: int | None = None

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("workflow node_id must be non-empty")
        if self.kind == "skill":
            if not self.agent_name or not self.skill_name or self.action_name:
                raise ValueError("skill nodes require agent_name and skill_name only")
        elif not self.action_name or self.agent_name or self.skill_name:
            raise ValueError("action nodes require action_name only")
        if self.retry_limit < 0 or self.timeout_seconds <= 0:
            raise ValueError("node retry_limit/timeout_seconds are invalid")
        if self.max_concurrency is not None and self.max_concurrency < 1:
            raise ValueError("node max_concurrency must be positive")
        if self.budget_tokens is not None and self.budget_tokens < 1:
            raise ValueError("node budget_tokens must be positive")

    def serializable(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "kind": self.kind,
            "agent_name": self.agent_name,
            "skill_name": self.skill_name,
            "action_name": self.action_name,
            "quality_policy": self.quality_policy,
            "retry_limit": self.retry_limit,
            "timeout_seconds": self.timeout_seconds,
            "concurrency_group": self.concurrency_group,
            "input_sources": self.input_sources,
            "max_concurrency": self.max_concurrency,
            "risk_level": self.risk_level,
            "approval_required": self.approval_required,
            "budget_tokens": self.budget_tokens,
        }


@dataclass(frozen=True)
class WorkflowDefinition:
    name: str
    version: int
    input_model: type[BaseModel]
    output_model: type[BaseModel] | None
    nodes: tuple[NodeDefinition, ...]
    edges: tuple[EdgeDefinition, ...] = ()
    catalog_version: str = "v1"
    provider_policy_version: str = "v1"
    checkpoint_schema_version: str = "v1"
    max_rework_attempts: int = 0
    required_domains: tuple[str, ...] = ("course_websec",)
    max_parallel_nodes: int = 4
    root_budget_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name or self.version < 1:
            raise ValueError("workflow requires a name and positive version")
        node_ids = [node.node_id for node in self.nodes]
        if not node_ids or len(node_ids) != len(set(node_ids)):
            raise ValueError("workflow nodes must be non-empty and unique")
        known = set(node_ids)
        for edge in self.edges:
            if edge.source not in known or edge.target not in known:
                raise ValueError(f"workflow edge references unknown node: {edge}")
        for node in self.nodes:
            if node.input_sources is not None:
                unknown_sources = set(node.input_sources).difference(known)
                if unknown_sources:
                    raise ValueError(
                        f"node {node.node_id!r} input_sources reference unknown nodes: {sorted(unknown_sources)!r}"
                    )
                if node.node_id in node.input_sources:
                    raise ValueError(f"node {node.node_id!r} cannot project its own output")
        quality_nodes = [node for node in self.nodes if node.skill_name == "QualityCheck"]
        if any(node.quality_policy == "workflow_node" for node in self.nodes):
            if len(quality_nodes) != 1:
                raise ValueError("workflow_node quality policy requires exactly one explicit QualityCheck node")
            quality = quality_nodes[0]
            if quality.agent_name != "outcome_evaluator" or quality.quality_policy != "none":
                raise ValueError("QualityCheck must be outcome_evaluator and cannot recursively quality check")
        if self.max_rework_attempts < 0:
            raise ValueError("max_rework_attempts cannot be negative")
        if self.max_parallel_nodes < 1:
            raise ValueError("max_parallel_nodes must be positive")
        if self.root_budget_tokens is not None and self.root_budget_tokens < 1:
            raise ValueError("root_budget_tokens must be positive")

    @property
    def key(self) -> tuple[str, int]:
        return (self.name, self.version)

    @property
    def definition_digest(self) -> str:
        encoded = json.dumps(
            {
                "name": self.name,
                "version": self.version,
                "input_model": self.input_model.__name__,
                "output_model": self.output_model.__name__ if self.output_model else None,
                "nodes": [node.serializable() for node in self.nodes],
                "edges": [edge.__dict__ for edge in self.edges],
                "catalog_version": self.catalog_version,
                "provider_policy_version": self.provider_policy_version,
                "checkpoint_schema_version": self.checkpoint_schema_version,
                "max_rework_attempts": self.max_rework_attempts,
                "required_domains": self.required_domains,
                "max_parallel_nodes": self.max_parallel_nodes,
                "root_budget_tokens": self.root_budget_tokens,
                "metadata": self.metadata,
            },
            ensure_ascii=True,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def initial_nodes(self) -> tuple[NodeDefinition, ...]:
        # A ``defect`` edge is an explicit bounded rework back-edge, not an
        # inbound dependency that makes the producer non-initial.
        targets = {edge.target for edge in self.edges if edge.condition != "defect"}
        return tuple(node for node in self.nodes if node.node_id not in targets)

    def successors(self, node_id: str, *, condition: str | None = None) -> tuple[NodeDefinition, ...]:
        lookup = {node.node_id: node for node in self.nodes}
        return tuple(
            lookup[edge.target]
            for edge in self.edges
            if edge.source == node_id and (edge.condition is None or edge.condition == condition)
        )

    def input_sources_for(self, node_id: str) -> tuple[str, ...] | None:
        """Return the minimum declared shared-state projection for a node."""
        node = next(item for item in self.nodes if item.node_id == node_id)
        if node.input_sources is not None:
            return node.input_sources
        predecessors = tuple(
            edge.source
            for edge in self.edges
            if edge.target == node_id and edge.condition is None
        )
        return predecessors

    def common_join(self, node_ids: tuple[str, ...]) -> NodeDefinition | None:
        """Find the single unconditional fan-in target for a fan-out branch."""
        if not node_ids:
            return None
        successor_sets = [
            {node.node_id for node in self.successors(node_id)}
            for node_id in node_ids
        ]
        if not successor_sets or any(len(values) != 1 for values in successor_sets):
            return None
        targets = set.intersection(*successor_sets)
        if len(targets) != 1:
            return None
        return next(node for node in self.nodes if node.node_id in targets)

    def rework_targets(self, quality_node_id: str, defects: list[dict[str, Any]]) -> tuple[NodeDefinition, ...]:
        """Choose bounded rework branches only from reviewed taxonomy routes."""
        routes = self.metadata.get("defect_routes", {})
        if not isinstance(routes, dict):
            routes = {}
        codes = {
            str(item.get("code") or item.get("taxonomy") or "")
            for item in defects
            if isinstance(item, dict)
        }
        targets: list[str] = []
        for code in sorted(code for code in codes if code):
            target_values = routes.get(code, ())
            if isinstance(target_values, str):
                target_values = (target_values,)
            targets.extend(str(value) for value in target_values)
        if not targets:
            targets.extend(edge.target for edge in self.edges if edge.source == quality_node_id and edge.condition == "defect")
        lookup = {node.node_id: node for node in self.nodes}
        result: list[NodeDefinition] = []
        for target in targets:
            node = lookup.get(target)
            if node is not None and node not in result:
                result.append(node)
        return tuple(result)


__all__ = ["EdgeDefinition", "InputMapper", "NodeDefinition", "OutputProjector", "WorkflowDefinition"]
