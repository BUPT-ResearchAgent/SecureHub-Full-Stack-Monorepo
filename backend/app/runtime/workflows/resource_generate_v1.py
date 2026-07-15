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

RESOURCE_GENERATE_PRODUCER_PROVIDER_MAX_TOKENS = 2400
RESOURCE_GENERATE_PRODUCER_BUDGET_TOKENS = 8000

PPT_QUALITY_ARTIFACT_FIELDS = (
    "deck_spec",
    "render_mode",
    "evidence_chunk_ids",
)


def producer_input(root_input: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    query = str(root_input["query"])
    rework = state.get("__quality_rework__")
    defects = rework.get("defects") if isinstance(rework, dict) else None
    if isinstance(defects, list):
        feedback = [
            f"{str(item.get('code') or 'quality_defect')}: {str(item.get('message') or '').strip()}"
            for item in defects[:5]
            if isinstance(item, dict)
        ]
        if feedback:
            query = (
                f"{query}\nQuality rework required. Correct these defects without changing the "
                f"knowledge-point scope: {'; '.join(feedback)}"
            )
    return {
        "user_id": root_input["user_id"],
        "query": query,
        "domain": root_input.get("domain", "course_websec"),
        "kp_id": root_input.get("kp_id"),
    }


def _quality_artifact(resource_type: ResourceKind, candidate: object) -> object:
    """Remove PPT compatibility duplicates before the guarded quality boundary."""
    if resource_type != "ppt" or not isinstance(candidate, dict):
        return candidate
    return {
        field: candidate[field]
        for field in PPT_QUALITY_ARTIFACT_FIELDS
        if field in candidate
    }


def quality_input(root_input: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    candidate = state.get("producer", {})
    artifact = candidate.get("output", candidate)
    return {
        "user_id": root_input["user_id"],
        "query": (
            f"Quality check {root_input['resource_type']} for task: "
            f"{root_input['query']}"
        ),
        "domain": root_input.get("domain", "course_websec"),
        "artifact": _quality_artifact(root_input["resource_type"], artifact),
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
            budget_tokens=RESOURCE_GENERATE_PRODUCER_BUDGET_TOKENS,
            provider_max_tokens=RESOURCE_GENERATE_PRODUCER_PROVIDER_MAX_TOKENS,
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
    "PPT_QUALITY_ARTIFACT_FIELDS",
    "RESOURCE_GENERATE_PRODUCER_BUDGET_TOKENS",
    "RESOURCE_GENERATE_PRODUCER_PROVIDER_MAX_TOKENS",
    "RESOURCE_GENERATE_V1",
    "ResourceGenerateInput",
    "ResourceGenerateOutput",
    "quality_input",
]
