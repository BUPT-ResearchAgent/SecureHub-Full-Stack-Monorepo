# Status: real

"""Versioned tutor workflow with explicit course and learner context.

``tutor_routing_v2`` remains replay-compatible. Version 3 only changes new
roots by projecting the authenticated course/KP context into the tutor skill;
the Runtime-provided persona snapshot remains bounded and never streams.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.runtime.workflow_definition import EdgeDefinition, NodeDefinition, WorkflowDefinition


_REWORKABLE_QUALITY_CODES = (
    "evidence_missing",
    "fact_conflict",
    "schema_invalid",
    "instructional_mismatch",
    "citation_mismatch",
)


class TutorRoutingV3Input(BaseModel):
    user_id: str
    course_id: str
    question: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    domain: str = "course_websec"
    # Server-owned, sanitized profile snapshot persisted with the root so it
    # remains available when RuntimeEngine revalidates a queued/replayed run.
    persona_summary: str = Field(default="", max_length=800)


class TutorRoutingV3Output(BaseModel):
    content: str = ""
    resources: list[dict[str, Any]] = Field(default_factory=list)
    quality_score: float | None = None


def _base_input(root: dict[str, Any], _state: dict[str, Any]) -> dict[str, Any]:
    context = root.get("context") if isinstance(root.get("context"), dict) else {}
    return {
        "user_id": root["user_id"],
        "query": root["question"],
        "domain": root.get("domain", "course_websec"),
        "course_id": root["course_id"],
        "current_kp_id": context.get("kp_id"),
        "learning_context": {
            "current_path_node_ids": context.get("current_path_node_ids")
            if isinstance(context.get("current_path_node_ids"), list)
            else [],
        },
    }


def _route_input(root: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    return {**_base_input(root, state), "question": root["question"]}


def _quality_input(root: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    return {
        **_base_input(root, state),
        "artifact": {key: value.get("output", value) for key, value in state.items()},
    }


TUTOR_ROUTING_V3 = WorkflowDefinition(
    name="tutor_routing_v3",
    version=3,
    input_model=TutorRoutingV3Input,
    output_model=TutorRoutingV3Output,
    nodes=(
        NodeDefinition("route_question", "skill", "career_planner", "RouteTutorQuestion", input_mapper=_route_input, quality_policy="workflow_node", input_sources=()),
        NodeDefinition("answer", "skill", "career_planner", "RecommendResources", input_mapper=_base_input, quality_policy="workflow_node", input_sources=("route_question",)),
        NodeDefinition("quality_check", "skill", "outcome_evaluator", "QualityCheck", input_mapper=_quality_input, input_sources=("answer",)),
        NodeDefinition("project_answer", "action", action_name="ProjectTutorAnswer", input_sources=("answer", "quality_check")),
    ),
    edges=(
        EdgeDefinition("route_question", "answer"),
        EdgeDefinition("answer", "quality_check"),
        EdgeDefinition("quality_check", "project_answer", "accept"),
        EdgeDefinition("quality_check", "answer", "defect"),
    ),
    catalog_version="production-catalog-v1",
    provider_policy_version="deepseek-direct-v1",
    checkpoint_schema_version="tutor-context-v3",
    max_rework_attempts=1,
    metadata={"defect_routes": {code: ("answer",) for code in _REWORKABLE_QUALITY_CODES}},
)


__all__ = ["TUTOR_ROUTING_V3"]
