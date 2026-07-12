"""Focused contract checks for the additive A3 six-resource workflow."""

from __future__ import annotations

from app.runtime.workflows.course_learning_full_v1 import COURSE_LEARNING_FULL_V1
from app.runtime.workflows.course_learning_full_v2 import (
    COURSE_LEARNING_FULL_V2,
    DEFAULT_RESOURCE_TYPES,
    RESOURCE_NODE_BY_TYPE,
)
from app.runtime.workflows.resource_generate_v1 import PRODUCER_BY_RESOURCE_TYPE


def test_course_learning_full_v2_keeps_v1_identity_and_declares_six_real_producers() -> None:
    assert COURSE_LEARNING_FULL_V2.name == "course_learning_full_v2"
    assert COURSE_LEARNING_FULL_V2.version == 2
    assert COURSE_LEARNING_FULL_V2.definition_digest != COURSE_LEARNING_FULL_V1.definition_digest
    assert COURSE_LEARNING_FULL_V2.max_parallel_nodes == 4

    nodes = {node.node_id: node for node in COURSE_LEARNING_FULL_V2.nodes}
    assert set(DEFAULT_RESOURCE_TYPES) == {"doc", "ppt", "mindmap", "quiz", "lab", "video"}
    for resource_type in DEFAULT_RESOURCE_TYPES:
        node = nodes[RESOURCE_NODE_BY_TYPE[resource_type]]
        assert (node.agent_name, node.skill_name) == PRODUCER_BY_RESOURCE_TYPE[resource_type]
        assert node.quality_policy == "workflow_node"
        assert node.concurrency_group == "resource-fanout-v2"
        assert node.max_concurrency == 4


def test_course_learning_full_v2_keeps_each_resource_in_quality_and_artifact_lineage() -> None:
    nodes = {node.node_id: node for node in COURSE_LEARNING_FULL_V2.nodes}
    quality = nodes["quality_check"]
    persist = nodes["persist_artifacts"]
    resource_nodes = tuple(RESOURCE_NODE_BY_TYPE[value] for value in DEFAULT_RESOURCE_TYPES)

    assert quality.agent_name == "outcome_evaluator"
    assert quality.skill_name == "QualityCheck"
    assert quality.input_sources == resource_nodes
    assert persist.action_name == "PersistResourceFanout"
    assert persist.input_sources == (*resource_nodes, "quality_check")
    assert COURSE_LEARNING_FULL_V2.rework_targets(
        "quality_check", [{"code": "citation_mismatch"}]
    ) == tuple(nodes[node_id] for node_id in resource_nodes)

    lineage = COURSE_LEARNING_FULL_V2.metadata["resource_lineage"]
    assert set(lineage) == set(DEFAULT_RESOURCE_TYPES)
    assert all(item["quality_node_id"] == "quality_check" for item in lineage.values())
    assert all(item["artifact_action"] == "PersistResourceFanout" for item in lineage.values())


def test_course_learning_full_v2_quality_projection_keeps_branch_evidence_and_producer_identity() -> None:
    nodes = {node.node_id: node for node in COURSE_LEARNING_FULL_V2.nodes}
    quality_mapper = nodes["quality_check"].input_mapper
    assert quality_mapper is not None
    state = {
        RESOURCE_NODE_BY_TYPE[resource_type]: {
            "output": {"content": f"{resource_type} output"},
            "evidence_snapshot_ids": [f"snapshot-{resource_type}"],
            "step_attempt_id": f"step-{resource_type}",
            "agent_run_id": f"agent-run-{resource_type}",
        }
        for resource_type in DEFAULT_RESOURCE_TYPES
    }

    mapped = quality_mapper(
        {"user_id": "user-1", "query": "SQL injection", "domain": "course_websec"},
        state,
    )
    artifact = mapped["artifact"]
    assert set(artifact) == set(RESOURCE_NODE_BY_TYPE[value] for value in DEFAULT_RESOURCE_TYPES)
    for resource_type in DEFAULT_RESOURCE_TYPES:
        candidate = artifact[RESOURCE_NODE_BY_TYPE[resource_type]]
        assert candidate["resource_type"] == resource_type
        assert candidate["evidence_snapshot_ids"] == [f"snapshot-{resource_type}"]
        assert (candidate["producer_agent"], candidate["producer_skill"]) == PRODUCER_BY_RESOURCE_TYPE[resource_type]
        assert len(candidate["candidate_digest"]) == 64
        assert len(candidate["candidate_preview"]) <= 800


def test_course_learning_full_v2_documents_optional_readings_and_resource_scoped_retry() -> None:
    optional = COURSE_LEARNING_FULL_V2.metadata["optional_resource_types"]["readings"]
    assert optional["workflow"] == "resource_generate_v1"
    assert (optional["agent_name"], optional["skill_name"]) == PRODUCER_BY_RESOURCE_TYPE["readings"]

    retry = COURSE_LEARNING_FULL_V2.metadata["resource_retry"]
    assert retry["scope"] == "single-resource"
    assert retry["root_retry_allowed"] is False
