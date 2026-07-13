# Status: real

"""Framework-neutral six-resource course workflow for the A3 product journey.

``course_learning_full_v1`` remains replay-compatible and is intentionally
untouched.  This definition adds the six resource fan-out as a new workflow
identity with its own checkpoint schema and definition digest.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.runtime.workflow_definition import EdgeDefinition, NodeDefinition, WorkflowDefinition
from app.runtime.workflows.resource_generate_v1 import PRODUCER_BY_RESOURCE_TYPE


CourseResourceKind = Literal["doc", "ppt", "mindmap", "quiz", "lab", "video", "readings"]

# Six resources are the default course bundle.  Readings stay available through
# the same canonical binding as an opt-in single-resource workflow; a static
# WorkflowDefinition cannot conditionally add a seventh branch without a new
# Runtime topology contract.
DEFAULT_RESOURCE_TYPES: tuple[CourseResourceKind, ...] = (
    "doc",
    "ppt",
    "mindmap",
    "quiz",
    "lab",
    "video",
)
OPTIONAL_RESOURCE_TYPES: tuple[CourseResourceKind, ...] = ("readings",)

RESOURCE_NODE_BY_TYPE: dict[CourseResourceKind, str] = {
    "doc": "resource_doc",
    "ppt": "resource_ppt",
    "mindmap": "resource_mindmap",
    "quiz": "resource_quiz",
    "lab": "resource_lab",
    "video": "resource_video",
    "readings": "resource_readings",
}

_REWORKABLE_DEFECT_CODES = (
    "evidence_missing",
    "fact_conflict",
    "schema_invalid",
    "instructional_mismatch",
    "citation_mismatch",
)


class CourseLearningFullV2Input(BaseModel):
    user_id: str
    course_id: str
    query: str = Field(min_length=1)
    kp_id: str | None = None
    domain: str = "course_websec"
    options: dict[str, Any] = Field(default_factory=dict)


class CourseLearningFullV2Output(BaseModel):
    resources: list[dict[str, Any]] = Field(default_factory=list)
    quality_score: float | None = None


def _base_input(root: dict[str, Any], _state: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": root["user_id"],
        "query": root["query"],
        "domain": root.get("domain", "course_websec"),
        "kp_id": root.get("kp_id"),
    }


def _quality_input(root: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Pass bounded candidate reviews plus durable lineage to QualityCheck.

    The full six generated artifacts are already held in typed workflow state
    for ArtifactSaga.  Re-injecting all of them into one QualityCheck exceeds
    the canonical input guardrail, so the evaluator receives an immutable
    digest, a bounded content preview, and the complete evidence/attempt
    identity for every branch instead.  This is a prompt projection only; it
    does not replace, truncate, or mutate the persisted artifact payload.
    """
    candidates: dict[str, dict[str, Any]] = {}
    for resource_type in DEFAULT_RESOURCE_TYPES:
        node_id = RESOURCE_NODE_BY_TYPE[resource_type]
        branch = state.get(node_id)
        if not isinstance(branch, dict):
            continue
        output = branch.get("output") if isinstance(branch.get("output"), dict) else {}
        serialized = json.dumps(output, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
        candidates[node_id] = {
            "resource_type": resource_type,
            "producer_agent": PRODUCER_BY_RESOURCE_TYPE[resource_type][0],
            "producer_skill": PRODUCER_BY_RESOURCE_TYPE[resource_type][1],
            "candidate_digest": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
            "candidate_preview": serialized[:800],
            "evidence_snapshot_ids": branch.get("evidence_snapshot_ids", []),
            "step_attempt_id": branch.get("step_attempt_id"),
            "agent_run_id": branch.get("agent_run_id"),
        }
    return {
        "user_id": root["user_id"],
        "query": f"Quality check course resource bundle: {root['query']}",
        "domain": root.get("domain", "course_websec"),
        "artifact": candidates,
    }


def _resource_node(resource_type: CourseResourceKind) -> NodeDefinition:
    """Bind every v2 branch explicitly to the canonical producer skill."""
    agent_name, skill_name = PRODUCER_BY_RESOURCE_TYPE[resource_type]
    return NodeDefinition(
        node_id=RESOURCE_NODE_BY_TYPE[resource_type],
        kind="skill",
        agent_name=agent_name,
        skill_name=skill_name,
        input_mapper=_base_input,
        quality_policy="workflow_node",
        input_sources=("generate_path",),
        concurrency_group="resource-fanout-v2",
        max_concurrency=4,
    )


_RESOURCE_NODES = tuple(RESOURCE_NODE_BY_TYPE[resource_type] for resource_type in DEFAULT_RESOURCE_TYPES)


COURSE_LEARNING_FULL_V2 = WorkflowDefinition(
    name="course_learning_full_v2",
    version=2,
    input_model=CourseLearningFullV2Input,
    output_model=CourseLearningFullV2Output,
    nodes=(
        NodeDefinition(
            node_id="generate_path",
            kind="skill",
            agent_name="task_orchestrator",
            skill_name="GenerateLearningPath",
            input_mapper=_base_input,
            quality_policy="workflow_node",
            input_sources=(),
        ),
        *(_resource_node(resource_type) for resource_type in DEFAULT_RESOURCE_TYPES),
        NodeDefinition(
            node_id="quality_check",
            kind="skill",
            agent_name="outcome_evaluator",
            skill_name="QualityCheck",
            input_mapper=_quality_input,
            quality_policy="none",
            input_sources=_RESOURCE_NODES,
            # The quality decision is an internal strict JSON record, not a
            # learner-facing draft. Its compact schema needs no token stream.
            budget_tokens=320,
        ),
        NodeDefinition(
            node_id="persist_artifacts",
            kind="action",
            action_name="PersistResourceFanout",
            quality_policy="none",
            input_sources=(*_RESOURCE_NODES, "quality_check"),
        ),
    ),
    edges=(
        *(EdgeDefinition("generate_path", node_id) for node_id in _RESOURCE_NODES),
        *(EdgeDefinition(node_id, "quality_check") for node_id in _RESOURCE_NODES),
        EdgeDefinition("quality_check", "persist_artifacts", "accept"),
        *(EdgeDefinition("quality_check", node_id, "defect") for node_id in _RESOURCE_NODES),
    ),
    catalog_version="production-catalog-v1",
    # S2-S4 are explicitly direct DeepSeek product paths.  Spark policy is
    # deferred to S8 and must not be recorded on new v2 roots.
    provider_policy_version="deepseek-direct-v1",
    checkpoint_schema_version="typed-state-v2",
    max_rework_attempts=1,
    max_parallel_nodes=4,
    metadata={
        "defect_routes": {
            code: _RESOURCE_NODES
            for code in _REWORKABLE_DEFECT_CODES
        },
        "blocked_defect_codes": ("safety_violation",),
        "fanout_resource_types": {
            RESOURCE_NODE_BY_TYPE[resource_type]: resource_type
            for resource_type in DEFAULT_RESOURCE_TYPES
        },
        "resource_lineage": {
            resource_type: {
                "producer_node_id": RESOURCE_NODE_BY_TYPE[resource_type],
                "agent_name": PRODUCER_BY_RESOURCE_TYPE[resource_type][0],
                "skill_name": PRODUCER_BY_RESOURCE_TYPE[resource_type][1],
                "quality_node_id": "quality_check",
                "artifact_action": "PersistResourceFanout",
            }
            for resource_type in DEFAULT_RESOURCE_TYPES
        },
        "optional_resource_types": {
            "readings": {
                "agent_name": PRODUCER_BY_RESOURCE_TYPE["readings"][0],
                "skill_name": PRODUCER_BY_RESOURCE_TYPE["readings"][1],
                "workflow": "resource_generate_v1",
                "reason": "opt-in resource retains the canonical artifact and lineage contract",
            }
        },
        "resource_retry": {
            "scope": "single-resource",
            "requires": "a resource-scoped control endpoint that creates a child attempt under the existing root",
            "root_retry_allowed": False,
        },
    },
)


__all__ = [
    "COURSE_LEARNING_FULL_V2",
    "CourseLearningFullV2Input",
    "CourseLearningFullV2Output",
    "CourseResourceKind",
    "DEFAULT_RESOURCE_TYPES",
    "OPTIONAL_RESOURCE_TYPES",
    "RESOURCE_NODE_BY_TYPE",
]
