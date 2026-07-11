# Status: real

"""Framework-neutral definitions for the five product adapters.

They are intentionally small: product HTTP routes map DTOs to these inputs and
return the durable root ID.  RuntimeEngine performs all execution.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.runtime.workflow_definition import EdgeDefinition, NodeDefinition, WorkflowDefinition


class ProfileBuildInput(BaseModel):
    user_id: str
    message: str
    dialogue_turns: list[dict[str, str]] = Field(default_factory=list)
    domain: str = "course_websec"


class CoursePlanInput(BaseModel):
    user_id: str
    course_id: str
    target_node_id: str | None = None
    query: str = "Generate a personalised learning path"
    domain: str = "course_websec"


class TutorRoutingInput(BaseModel):
    user_id: str
    course_id: str
    question: str
    context: dict[str, Any] = Field(default_factory=dict)
    domain: str = "course_websec"


class AssessmentUpdateInput(BaseModel):
    user_id: str
    course_id: str
    answers: list[dict[str, Any]] = Field(default_factory=list)
    domain: str = "course_websec"


class GenericWorkflowOutput(BaseModel):
    output: dict[str, Any] = Field(default_factory=dict)


def _basic_input(root: dict[str, Any], _state: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": root["user_id"],
        "query": root.get("query") or root.get("message") or root.get("question") or "SecureHub workflow request",
        "domain": root.get("domain", "course_websec"),
    }


def _profile_input(root: dict[str, Any], _state: dict[str, Any]) -> dict[str, Any]:
    return {
        **_basic_input(root, _state),
        "dialogue_turns": root.get("dialogue_turns", []),
    }


def _path_input(root: dict[str, Any], _state: dict[str, Any]) -> dict[str, Any]:
    return {**_basic_input(root, _state), "course_id": root.get("course_id")}


def _route_input(root: dict[str, Any], _state: dict[str, Any]) -> dict[str, Any]:
    return {**_basic_input(root, _state), "question": root.get("question", "")}


def _assessment_input(root: dict[str, Any], _state: dict[str, Any]) -> dict[str, Any]:
    return {**_basic_input(root, _state), "answers": root.get("answers", [])}


def _quality_input(root: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    return {
        **_basic_input(root, state),
        "artifact": {key: value.get("output", value) for key, value in state.items()},
    }


PROFILE_BUILD_V1 = WorkflowDefinition(
    name="profile_build_v1",
    version=1,
    input_model=ProfileBuildInput,
    output_model=GenericWorkflowOutput,
    nodes=(
        NodeDefinition("build_persona", "skill", "career_planner", "BuildLearningPersona", input_mapper=_profile_input, quality_policy="workflow_node"),
        NodeDefinition("quality_check", "skill", "outcome_evaluator", "QualityCheck", input_mapper=_quality_input),
        NodeDefinition("persist_profile", "action", action_name="PersistProfile"),
    ),
    edges=(EdgeDefinition("build_persona", "quality_check"), EdgeDefinition("quality_check", "persist_profile", "accept")),
    catalog_version="production-catalog-v1",
)

COURSE_PLAN_V1 = WorkflowDefinition(
    name="course_plan_v1",
    version=1,
    input_model=CoursePlanInput,
    output_model=GenericWorkflowOutput,
    nodes=(
        NodeDefinition("generate_path", "skill", "task_orchestrator", "GenerateLearningPath", input_mapper=_path_input, quality_policy="workflow_node"),
        NodeDefinition("quality_check", "skill", "outcome_evaluator", "QualityCheck", input_mapper=_quality_input),
        NodeDefinition("persist_learning_path", "action", action_name="PersistLearningPath"),
    ),
    edges=(EdgeDefinition("generate_path", "quality_check"), EdgeDefinition("quality_check", "persist_learning_path", "accept")),
    catalog_version="production-catalog-v1",
)

TUTOR_ROUTING_V1 = WorkflowDefinition(
    name="tutor_routing_v1",
    version=1,
    input_model=TutorRoutingInput,
    output_model=GenericWorkflowOutput,
    nodes=(
        NodeDefinition("route_question", "skill", "career_planner", "RouteTutorQuestion", input_mapper=_route_input, quality_policy="workflow_node"),
        NodeDefinition("answer", "skill", "career_planner", "RecommendResources", input_mapper=_basic_input, quality_policy="workflow_node"),
        NodeDefinition("quality_check", "skill", "outcome_evaluator", "QualityCheck", input_mapper=_quality_input),
    ),
    edges=(EdgeDefinition("route_question", "answer"), EdgeDefinition("answer", "quality_check")),
    catalog_version="production-catalog-v1",
)

ASSESSMENT_UPDATE_V1 = WorkflowDefinition(
    name="assessment_update_v1",
    version=1,
    input_model=AssessmentUpdateInput,
    output_model=GenericWorkflowOutput,
    nodes=(
        NodeDefinition("run_assessment", "skill", "outcome_evaluator", "RunAssessment", input_mapper=_assessment_input, quality_policy="workflow_node"),
        NodeDefinition("quality_check", "skill", "outcome_evaluator", "QualityCheck", input_mapper=_quality_input),
        NodeDefinition("update_capability", "skill", "outcome_evaluator", "UpdateCapability", input_mapper=_basic_input, quality_policy="workflow_node"),
        # These writes are deliberately separate deterministic actions.  The
        # model may propose a delta/persona, but it cannot claim that either
        # has been applied until RuntimeEngine executes and persists it.
        NodeDefinition("persist_capability", "action", action_name="PersistCapability"),
        NodeDefinition("update_persona", "skill", "career_planner", "UpdatePersona", input_mapper=_basic_input, quality_policy="workflow_node"),
        NodeDefinition("persist_profile", "action", action_name="PersistProfile"),
    ),
    edges=(
        EdgeDefinition("run_assessment", "quality_check"),
        EdgeDefinition("quality_check", "update_capability", "accept"),
        EdgeDefinition("update_capability", "persist_capability"),
        EdgeDefinition("persist_capability", "update_persona"),
        EdgeDefinition("update_persona", "persist_profile"),
    ),
    catalog_version="production-catalog-v1",
)


PRODUCT_WORKFLOWS = (PROFILE_BUILD_V1, COURSE_PLAN_V1, TUTOR_ROUTING_V1, ASSESSMENT_UPDATE_V1)


__all__ = [
    "ASSESSMENT_UPDATE_V1",
    "COURSE_PLAN_V1",
    "PRODUCT_WORKFLOWS",
    "PROFILE_BUILD_V1",
    "TUTOR_ROUTING_V1",
]
