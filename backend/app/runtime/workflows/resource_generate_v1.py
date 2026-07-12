# Status: real

"""The Wave 1 Golden Vertical Slice workflow definition.

The workflow remains framework-neutral.  The producer selection is a typed
input mapping, while the RuntimeEngine owns every state transition and effect.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.runtime.workflow_definition import EdgeDefinition, NodeDefinition, WorkflowDefinition


ResourceKind = Literal["doc", "ppt", "mindmap", "quiz", "lab", "video", "readings"]


class ResourceGenerateInput(BaseModel):
    user_id: str
    course_id: str
    kp_id: str | None = None
    resource_type: ResourceKind = "doc"
    query: str = Field(min_length=1)
    domain: str = "course_websec"
    options: dict[str, Any] = Field(default_factory=dict)


class ResourceGenerateOutput(BaseModel):
    resource_id: str
    resource_type: ResourceKind
    quality_score: float | None = None
    object_key: str | None = None
    evidence_snapshot_ids: list[str] = Field(default_factory=list)


PRODUCER_BY_RESOURCE_TYPE: dict[ResourceKind, tuple[str, str]] = {
    "doc": ("doc_archivist", "GenerateCourseDoc"),
    "ppt": ("doc_archivist", "GenerateCoursePPT"),
    "mindmap": ("doc_archivist", "GenerateMindmap"),
    "video": ("doc_archivist", "GenerateVideoStoryboard"),
    "quiz": ("competition_advisor", "GenerateQuiz"),
    "lab": ("topic_explorer", "GenerateHandsOnLab"),
    "readings": ("topic_explorer", "RecommendReadings"),
}


def producer_input(root_input: dict[str, Any], _state: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": root_input["user_id"],
        "query": root_input["query"],
        "domain": root_input.get("domain", "course_websec"),
        "kp_id": root_input.get("kp_id"),
    }


def quality_input(root_input: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    candidate = state.get("producer", {})
    return {
        "user_id": root_input["user_id"],
        "query": f"Quality check resource type {root_input['resource_type']}",
        "domain": root_input.get("domain", "course_websec"),
        "artifact": candidate.get("output", candidate),
    }


RESOURCE_GENERATE_V1 = WorkflowDefinition(
    name="resource_generate_v1",
    version=1,
    input_model=ResourceGenerateInput,
    output_model=ResourceGenerateOutput,
    nodes=(
        NodeDefinition(
            node_id="producer",
            kind="skill",
            agent_name="doc_archivist",
            skill_name="GenerateCourseDoc",
            input_mapper=producer_input,
            quality_policy="workflow_node",
            retry_limit=0,
            input_sources=(),
        ),
        NodeDefinition(
            node_id="quality_check",
            kind="skill",
            agent_name="outcome_evaluator",
            skill_name="QualityCheck",
            input_mapper=quality_input,
            quality_policy="none",
            retry_limit=0,
            input_sources=("producer",),
        ),
        NodeDefinition(
            node_id="persist_artifact",
            kind="action",
            action_name="PersistGeneratedResource",
            quality_policy="none",
            input_sources=("producer", "quality_check"),
        ),
    ),
    edges=(
        EdgeDefinition("producer", "quality_check"),
        EdgeDefinition("quality_check", "persist_artifact", condition="accept"),
        EdgeDefinition("quality_check", "producer", condition="defect"),
    ),
    catalog_version="production-catalog-v1",
    provider_policy_version="v1",
    checkpoint_schema_version="v1",
    max_rework_attempts=1,
    metadata={"producer_by_resource_type": PRODUCER_BY_RESOURCE_TYPE},
)


__all__ = [
    "PRODUCER_BY_RESOURCE_TYPE",
    "RESOURCE_GENERATE_V1",
    "ResourceGenerateInput",
    "ResourceGenerateOutput",
]
