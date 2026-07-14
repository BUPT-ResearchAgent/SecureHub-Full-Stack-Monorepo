# Status: real

"""Tutor workflow with a learner-facing terminal projection.

``tutor_routing_v1`` remains intact for existing durable roots. Version 2
keeps the same explicit quality gate, then terminates at a deterministic action
that exposes the accepted answer rather than the QualityCheck internals.
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


class TutorRoutingV2Input(BaseModel):
    user_id: str
    course_id: str
    question: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    domain: str = "course_websec"


class TutorRoutingV2Output(BaseModel):
    content: str = ""
    resources: list[dict[str, Any]] = Field(default_factory=list)
    quality_score: float | None = None


def _base_input(root: dict[str, Any], _state: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": root["user_id"],
        "query": root["question"],
        "domain": root.get("domain", "course_websec"),
    }


def _route_input(root: dict[str, Any], _state: dict[str, Any]) -> dict[str, Any]:
    return {**_base_input(root, _state), "question": root["question"]}


def _quality_input(root: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    return {
        **_base_input(root, state),
        "artifact": {key: value.get("output", value) for key, value in state.items()},
    }


TUTOR_ROUTING_V2 = WorkflowDefinition(
    name="tutor_routing_v2",
    version=1,
    input_model=TutorRoutingV2Input,
    output_model=TutorRoutingV2Output,
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
    max_rework_attempts=1,
    metadata={"defect_routes": {code: ("answer",) for code in _REWORKABLE_QUALITY_CODES}},
)


__all__ = ["TUTOR_ROUTING_V2"]
