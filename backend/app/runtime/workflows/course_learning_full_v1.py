# Status: real

"""The bounded parallel resource workflow used by the A3 demonstration path."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.runtime.workflow_definition import EdgeDefinition, NodeDefinition, WorkflowDefinition


class CourseLearningFullInput(BaseModel):
    user_id: str
    course_id: str
    query: str = Field(min_length=1)
    kp_id: str | None = None
    domain: str = "course_websec"
    options: dict[str, Any] = Field(default_factory=dict)


class CourseLearningFullOutput(BaseModel):
    resources: list[dict[str, Any]] = Field(default_factory=list)
    quality_score: float | None = None


def _base_input(root: dict[str, Any], _state: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": root["user_id"],
        "course_id": root["course_id"],
        "query": root["query"],
        "kp_id": root.get("kp_id"),
        "domain": root.get("domain", "course_websec"),
    }


def _quality_input(root: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    artifacts: dict[str, Any] = {}
    for node_id, value in state.items():
        output = value.get("output") if isinstance(value, dict) else None
        if isinstance(output, dict):
            artifacts[node_id] = output
    return {
        "user_id": root["user_id"],
        "query": f"Quality check parallel course resources: {root['query']}",
        "domain": root.get("domain", "course_websec"),
        "artifact": artifacts,
    }


_RESOURCE_NODES = ("resource_doc", "resource_ppt", "resource_quiz", "resource_lab")


COURSE_LEARNING_FULL_V1 = WorkflowDefinition(
    name="course_learning_full_v1",
    version=1,
    input_model=CourseLearningFullInput,
    output_model=CourseLearningFullOutput,
    nodes=(
        NodeDefinition(
            "generate_path",
            "skill",
            "task_orchestrator",
            "GenerateLearningPath",
            input_mapper=_base_input,
            quality_policy="workflow_node",
            input_sources=(),
        ),
        NodeDefinition(
            "resource_doc",
            "skill",
            "doc_archivist",
            "GenerateCourseDoc",
            input_mapper=_base_input,
            quality_policy="workflow_node",
            input_sources=("generate_path",),
            concurrency_group="resource-fanout",
        ),
        NodeDefinition(
            "resource_ppt",
            "skill",
            "doc_archivist",
            "GenerateCoursePPT",
            input_mapper=_base_input,
            quality_policy="workflow_node",
            input_sources=("generate_path",),
            concurrency_group="resource-fanout",
        ),
        NodeDefinition(
            "resource_quiz",
            "skill",
            "competition_advisor",
            "GenerateQuiz",
            input_mapper=_base_input,
            quality_policy="workflow_node",
            input_sources=("generate_path",),
            concurrency_group="resource-fanout",
        ),
        NodeDefinition(
            "resource_lab",
            "skill",
            "topic_explorer",
            "GenerateHandsOnLab",
            input_mapper=_base_input,
            quality_policy="workflow_node",
            input_sources=("generate_path",),
            concurrency_group="resource-fanout",
        ),
        NodeDefinition(
            "quality_check",
            "skill",
            "outcome_evaluator",
            "QualityCheck",
            input_mapper=_quality_input,
            quality_policy="none",
            input_sources=_RESOURCE_NODES,
        ),
        NodeDefinition(
            "persist_artifacts",
            "action",
            action_name="PersistResourceFanout",
            input_sources=(*_RESOURCE_NODES, "quality_check"),
        ),
    ),
    edges=(
        EdgeDefinition("generate_path", "resource_doc"),
        EdgeDefinition("generate_path", "resource_ppt"),
        EdgeDefinition("generate_path", "resource_quiz"),
        EdgeDefinition("generate_path", "resource_lab"),
        EdgeDefinition("resource_doc", "quality_check"),
        EdgeDefinition("resource_ppt", "quality_check"),
        EdgeDefinition("resource_quiz", "quality_check"),
        EdgeDefinition("resource_lab", "quality_check"),
        EdgeDefinition("quality_check", "persist_artifacts", "accept"),
        EdgeDefinition("quality_check", "resource_doc", "defect"),
        EdgeDefinition("quality_check", "resource_ppt", "defect"),
        EdgeDefinition("quality_check", "resource_quiz", "defect"),
        EdgeDefinition("quality_check", "resource_lab", "defect"),
    ),
    catalog_version="production-catalog-v1",
    provider_policy_version="spark-primary-deepseek-fallback-v1",
    checkpoint_schema_version="typed-state-v1",
    max_rework_attempts=1,
    max_parallel_nodes=4,
    metadata={
        "defect_routes": {
            "evidence_missing": _RESOURCE_NODES,
            "fact_conflict": _RESOURCE_NODES,
            "schema_invalid": _RESOURCE_NODES,
            "instructional_mismatch": _RESOURCE_NODES,
            "citation_mismatch": _RESOURCE_NODES,
        },
        "fanout_resource_types": {
            "resource_doc": "doc",
            "resource_ppt": "ppt",
            "resource_quiz": "quiz",
            "resource_lab": "lab",
        },
    },
)


__all__ = ["COURSE_LEARNING_FULL_V1", "CourseLearningFullInput", "CourseLearningFullOutput"]
