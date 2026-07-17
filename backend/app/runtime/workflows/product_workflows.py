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


class AssessmentUpdateV2Input(AssessmentUpdateInput):
    """Versioned assessment input with an optional durable quiz artifact."""

    quiz_artifact_id: str | None = None
    # The typed course command supplies bounded navigation context (not raw
    # learner content). The final action includes its knowledge-point ID in
    # the durable assessment audit, so it must survive Engine revalidation.
    context: dict[str, Any] = Field(default_factory=dict)
    # These fields are overwritten by WorkflowApplicationService from the
    # authenticated user's persisted profile. They must survive RuntimeEngine's
    # input-model revalidation, but callers never own their values.
    capability_dimensions: list[str] = Field(default_factory=list)
    persona_dimension_keys: list[str] = Field(default_factory=list)


class GenericWorkflowOutput(BaseModel):
    output: dict[str, Any] = Field(default_factory=dict)


_REWORKABLE_QUALITY_CODES = (
    "evidence_missing",
    "fact_conflict",
    "schema_invalid",
    "instructional_mismatch",
    "citation_mismatch",
)


def _quality_rework_metadata(target_node: str) -> dict[str, dict[str, tuple[str, ...]]]:
    return {
        "defect_routes": {
            code: (target_node,)
            for code in _REWORKABLE_QUALITY_CODES
        }
    }


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
    answers = root.get("answers", [])
    return {
        **_basic_input(root, _state),
        # ``answers`` is already part of the typed Skill input. Repeating the
        # whole list inside ``query`` used to consume the global guardrail
        # budget twice and forced a lossy four-character transport projection.
        # For a server-verified published submission, the embedded summary
        # contains immutable objective scoring facts; answer excerpts must not
        # by themselves be interpreted as an incomplete submission.
        "query": (
            "Assess the learner's server-verified published course submission. "
            "Use assessment_summary.scoring.objective_floor_score as the "
            "minimum score justified by frozen objective items. Answers may be "
            "bounded only for prompt transport; do not call them incomplete "
            "solely because of an excerpt. Evaluate any remaining subjective "
            "content with the linked Evidence."
        ),
        "answers": answers,
    }


def _update_capability_input(root: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    assessment = dict((state.get("run_assessment") or {}).get("output") or {})
    score = assessment.get("score")
    feedback = str(assessment.get("feedback") or "")[:1_200]
    proposed_delta = assessment.get("capability_delta")
    score_vector = proposed_delta if isinstance(proposed_delta, dict) else {}
    capability_dimensions = sorted(
        {
            str(value).strip()
            for value in root.get("capability_dimensions", [])
            if isinstance(value, str) and value.strip()
        }
    )
    return {
        **_basic_input(root, state),
        "query": (
            f"Update capabilities from assessment score={score}; feedback={feedback}; "
            f"authorized_capability_dimensions={capability_dimensions}"
        ),
        "score_vector": score_vector,
        "capability_dimensions": capability_dimensions,
    }


def _update_persona_from_assessment_input(root: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Give the persona skill accepted assessment facts, never raw answers."""
    assessment = dict((state.get("run_assessment") or {}).get("output") or {})
    capability = dict((state.get("update_capability") or {}).get("output") or {})
    context = root.get("context") if isinstance(root.get("context"), dict) else {}
    delta = capability.get("capability_delta") or capability.get("delta") or assessment.get("capability_delta") or {}
    persona_dimension_keys = sorted(
        {
            str(value).strip()
            for value in root.get("persona_dimension_keys", [])
            if isinstance(value, str) and value.strip()
        }
    )
    return {
        **_basic_input(root, state),
        "query": (
            "Update only learner persona dimensions supported by the accepted assessment; "
            f"authorized_persona_dimension_keys={persona_dimension_keys}"
        ),
        "learning_events": [{
            "assessment_score": assessment.get("score"),
            "weak_kp_ids": assessment.get("weak_kp_ids") if isinstance(assessment.get("weak_kp_ids"), list) else [],
            "capability_delta": delta if isinstance(delta, dict) else {},
            "course_id": root.get("course_id"),
            "kp_id": context.get("kp_id"),
        }],
        "persona_dimension_keys": persona_dimension_keys,
    }


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
        NodeDefinition("build_persona", "skill", "career_planner", "BuildLearningPersona", input_mapper=_profile_input, quality_policy="workflow_node", input_sources=()),
        NodeDefinition("quality_check", "skill", "outcome_evaluator", "QualityCheck", input_mapper=_quality_input, input_sources=("build_persona",)),
        NodeDefinition("persist_profile", "action", action_name="PersistProfile", input_sources=("build_persona", "quality_check")),
    ),
    edges=(
        EdgeDefinition("build_persona", "quality_check"),
        EdgeDefinition("quality_check", "persist_profile", "accept"),
        EdgeDefinition("quality_check", "build_persona", "defect"),
    ),
    catalog_version="production-catalog-v1",
    max_rework_attempts=1,
    metadata=_quality_rework_metadata("build_persona"),
)

COURSE_PLAN_V1 = WorkflowDefinition(
    name="course_plan_v1",
    version=1,
    input_model=CoursePlanInput,
    output_model=GenericWorkflowOutput,
    nodes=(
        NodeDefinition("generate_path", "skill", "task_orchestrator", "GenerateLearningPath", input_mapper=_path_input, quality_policy="workflow_node", input_sources=()),
        NodeDefinition("quality_check", "skill", "outcome_evaluator", "QualityCheck", input_mapper=_quality_input, input_sources=("generate_path",)),
        NodeDefinition("persist_learning_path", "action", action_name="PersistLearningPath", input_sources=("generate_path", "quality_check")),
    ),
    edges=(
        EdgeDefinition("generate_path", "quality_check"),
        EdgeDefinition("quality_check", "persist_learning_path", "accept"),
        EdgeDefinition("quality_check", "generate_path", "defect"),
    ),
    catalog_version="production-catalog-v1",
    max_rework_attempts=1,
    metadata=_quality_rework_metadata("generate_path"),
)

TUTOR_ROUTING_V1 = WorkflowDefinition(
    name="tutor_routing_v1",
    version=1,
    input_model=TutorRoutingInput,
    output_model=GenericWorkflowOutput,
    nodes=(
        NodeDefinition("route_question", "skill", "career_planner", "RouteTutorQuestion", input_mapper=_route_input, quality_policy="workflow_node", input_sources=()),
        NodeDefinition("answer", "skill", "career_planner", "RecommendResources", input_mapper=_basic_input, quality_policy="workflow_node", input_sources=("route_question",)),
        NodeDefinition("quality_check", "skill", "outcome_evaluator", "QualityCheck", input_mapper=_quality_input, input_sources=("answer",)),
    ),
    edges=(
        EdgeDefinition("route_question", "answer"),
        EdgeDefinition("answer", "quality_check"),
        EdgeDefinition("quality_check", "answer", "defect"),
    ),
    catalog_version="production-catalog-v1",
    max_rework_attempts=1,
    metadata=_quality_rework_metadata("answer"),
)

ASSESSMENT_UPDATE_V1 = WorkflowDefinition(
    name="assessment_update_v1",
    version=1,
    input_model=AssessmentUpdateInput,
    output_model=GenericWorkflowOutput,
    nodes=(
        NodeDefinition("run_assessment", "skill", "outcome_evaluator", "RunAssessment", input_mapper=_assessment_input, quality_policy="workflow_node", input_sources=()),
        NodeDefinition("quality_check", "skill", "outcome_evaluator", "QualityCheck", input_mapper=_quality_input, input_sources=("run_assessment",)),
        NodeDefinition("update_capability", "skill", "outcome_evaluator", "UpdateCapability", input_mapper=_update_capability_input, quality_policy="workflow_node", input_sources=("run_assessment", "quality_check")),
        # These writes are deliberately separate deterministic actions.  The
        # model may propose a delta/persona, but it cannot claim that either
        # has been applied until RuntimeEngine executes and persists it.
        NodeDefinition("persist_capability", "action", action_name="PersistCapability", input_sources=("update_capability",)),
        NodeDefinition("update_persona", "skill", "career_planner", "UpdatePersona", input_mapper=_basic_input, quality_policy="workflow_node", input_sources=("persist_capability",)),
        NodeDefinition("persist_profile", "action", action_name="PersistProfile", input_sources=("run_assessment", "persist_capability", "update_persona")),
    ),
    edges=(
        EdgeDefinition("run_assessment", "quality_check"),
        EdgeDefinition("quality_check", "update_capability", "accept"),
        EdgeDefinition("update_capability", "persist_capability"),
        EdgeDefinition("persist_capability", "update_persona"),
        EdgeDefinition("update_persona", "persist_profile"),
        EdgeDefinition("quality_check", "run_assessment", "defect"),
    ),
    catalog_version="production-catalog-v1",
    max_rework_attempts=1,
    metadata=_quality_rework_metadata("run_assessment"),
)


# V1 commits two independent actions and therefore cannot promise that a
# later persona failure leaves no capability mutation. New roots use V2; old
# V1 roots retain their original definition digest and checkpoint semantics.
ASSESSMENT_UPDATE_V2 = WorkflowDefinition(
    name="assessment_update_v2",
    version=2,
    input_model=AssessmentUpdateV2Input,
    output_model=GenericWorkflowOutput,
    nodes=(
        NodeDefinition("run_assessment", "skill", "outcome_evaluator", "RunAssessment", input_mapper=_assessment_input, quality_policy="workflow_node", input_sources=()),
        NodeDefinition("quality_check", "skill", "outcome_evaluator", "QualityCheck", input_mapper=_quality_input, input_sources=("run_assessment",)),
        NodeDefinition("update_capability", "skill", "outcome_evaluator", "UpdateCapability", input_mapper=_update_capability_input, quality_policy="workflow_node", input_sources=("run_assessment", "quality_check")),
        NodeDefinition("update_persona", "skill", "career_planner", "UpdatePersona", input_mapper=_update_persona_from_assessment_input, quality_policy="workflow_node", input_sources=("run_assessment", "update_capability", "quality_check")),
        NodeDefinition("persist_assessment_feedback", "action", action_name="PersistAssessmentFeedback", input_sources=("run_assessment", "quality_check", "update_capability", "update_persona")),
    ),
    edges=(
        EdgeDefinition("run_assessment", "quality_check"),
        EdgeDefinition("quality_check", "update_capability", "accept"),
        EdgeDefinition("update_capability", "update_persona"),
        EdgeDefinition("update_persona", "persist_assessment_feedback"),
        EdgeDefinition("quality_check", "run_assessment", "defect"),
    ),
    catalog_version="production-catalog-v1",
    provider_policy_version="deepseek-direct-v1",
    checkpoint_schema_version="assessment-feedback-v2",
    max_rework_attempts=1,
    metadata=_quality_rework_metadata("run_assessment"),
)


PRODUCT_WORKFLOWS = (PROFILE_BUILD_V1, COURSE_PLAN_V1, TUTOR_ROUTING_V1, ASSESSMENT_UPDATE_V1, ASSESSMENT_UPDATE_V2)


__all__ = [
    "ASSESSMENT_UPDATE_V1",
    "ASSESSMENT_UPDATE_V2",
    "COURSE_PLAN_V1",
    "PRODUCT_WORKFLOWS",
    "PROFILE_BUILD_V1",
    "TUTOR_ROUTING_V1",
]
