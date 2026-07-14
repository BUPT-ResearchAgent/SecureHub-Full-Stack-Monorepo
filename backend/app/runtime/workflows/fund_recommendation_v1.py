# Status: real

"""Independent, framework-neutral fund recommendation workflow.

The definition deliberately has a new workflow identity and a deterministic
terminal projection. It reuses existing business Agents and frozen Skills;
only the domain is additive.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.runtime.workflow_definition import EdgeDefinition, NodeDefinition, WorkflowDefinition
from app.schemas.fund_recommendation import FundCourseContext, FundProfileSnapshot, FundRecommendationResult


class FundRecommendationV1Input(BaseModel):
    user_id: str
    query: str = Field(min_length=8, max_length=600)
    domain: str = "fund"
    course_context: FundCourseContext = Field(default_factory=FundCourseContext)
    # This snapshot is populated by the authenticated adapter from the sole
    # user_profiles/user_capabilities sources. It is never browser supplied.
    profile_snapshot: FundProfileSnapshot = Field(default_factory=FundProfileSnapshot)
    persona_summary: str = Field(default="", max_length=800)


def _base_input(root: dict[str, Any], _state: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": root["user_id"],
        # Include stable retrieval terms so the minimal three-document fund
        # corpus remains discoverable even when the learner's own query is
        # short or uses a different research-direction synonym.
        "query": f"{root['query']} 科研基金 网络安全 官方来源 申报",
        "domain": "fund",
    }


def _landscape_input(root: dict[str, Any], _state: dict[str, Any]) -> dict[str, Any]:
    return {
        **_base_input(root, _state),
        "target_role": "网络安全科研项目申请与研究实践",
        "fund_context": {
            "course_context": root.get("course_context", {}),
            "profile_dimensions": [
                item.get("dimension")
                for item in dict(root.get("profile_snapshot") or {}).get("capabilities", [])
                if isinstance(item, dict) and isinstance(item.get("dimension"), str)
            ],
        },
    }


def _recommendation_input(root: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    landscape = dict((state.get("analyse_fund_landscape") or {}).get("output") or {})
    snapshot = dict(root.get("profile_snapshot") or {})
    return {
        **_base_input(root, state),
        "learning_context": {
            "profile_snapshot": snapshot,
            "course_context": root.get("course_context", {}),
            "fund_landscape": landscape.get("fund_landscape", []),
            "market_trend": landscape.get("trend", ""),
            "top_skills": landscape.get("top_skills", []),
        },
    }


def _quality_input(root: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    landscape = dict((state.get("analyse_fund_landscape") or {}).get("output") or {})
    recommendation = dict((state.get("recommend_funds") or {}).get("output") or {})
    return {
        **_base_input(root, state),
        "query": "Audit fund opportunity recommendations against official-source evidence and the persisted learner profile.",
        "artifact": {
            "landscape": {
                "trend": landscape.get("trend"),
                "fund_landscape": landscape.get("fund_landscape", []),
                "evidence_snapshot_ids": list((state.get("analyse_fund_landscape") or {}).get("evidence_snapshot_ids") or []),
            },
            "recommendations": {
                "content": recommendation.get("content"),
                "fund_recommendations": recommendation.get("fund_recommendations", []),
                "evidence_snapshot_ids": list((state.get("recommend_funds") or {}).get("evidence_snapshot_ids") or []),
            },
        },
    }


FUND_RECOMMENDATION_V1 = WorkflowDefinition(
    name="fund_recommendation_v1",
    version=1,
    input_model=FundRecommendationV1Input,
    output_model=FundRecommendationResult,
    nodes=(
        NodeDefinition(
            node_id="analyse_fund_landscape",
            kind="skill",
            agent_name="job_analyst",
            skill_name="AnalyzeJobMarket",
            input_mapper=_landscape_input,
            quality_policy="workflow_node",
            input_sources=(),
        ),
        NodeDefinition(
            node_id="recommend_funds",
            kind="skill",
            agent_name="career_planner",
            skill_name="RecommendResources",
            input_mapper=_recommendation_input,
            quality_policy="workflow_node",
            input_sources=("analyse_fund_landscape",),
        ),
        NodeDefinition(
            node_id="quality_check",
            kind="skill",
            agent_name="outcome_evaluator",
            skill_name="QualityCheck",
            input_mapper=_quality_input,
            quality_policy="none",
            input_sources=("analyse_fund_landscape", "recommend_funds"),
            budget_tokens=360,
        ),
        NodeDefinition(
            node_id="project_fund_recommendation",
            kind="action",
            action_name="ProjectFundRecommendation",
            input_sources=("analyse_fund_landscape", "recommend_funds", "quality_check"),
        ),
    ),
    edges=(
        EdgeDefinition("analyse_fund_landscape", "recommend_funds"),
        EdgeDefinition("recommend_funds", "quality_check"),
        EdgeDefinition("quality_check", "project_fund_recommendation", "accept"),
        EdgeDefinition("quality_check", "recommend_funds", "defect"),
    ),
    catalog_version="production-catalog-v1",
    provider_policy_version="deepseek-direct-v1",
    checkpoint_schema_version="fund-recommendation-v1",
    required_domains=("fund",),
    max_rework_attempts=1,
    metadata={
        "defect_routes": {
            "evidence_missing": ("recommend_funds",),
            "fact_conflict": ("recommend_funds",),
            "schema_invalid": ("recommend_funds",),
            "citation_mismatch": ("recommend_funds",),
            "instructional_mismatch": ("recommend_funds",),
        },
        "blocked_defect_codes": ("safety_violation",),
        "lineage": {
            "landscape": {"agent_name": "job_analyst", "skill_name": "AnalyzeJobMarket"},
            "recommendation": {"agent_name": "career_planner", "skill_name": "RecommendResources"},
            "quality": {"agent_name": "outcome_evaluator", "skill_name": "QualityCheck"},
            "terminal_action": "ProjectFundRecommendation",
        },
        "evidence_floor": 3,
        "profile_source": "user_profiles/user_capabilities",
        "course_root_reuse": False,
    },
)


__all__ = ["FUND_RECOMMENDATION_V1", "FundRecommendationV1Input"]
