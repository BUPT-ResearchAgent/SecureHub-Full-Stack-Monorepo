"""Focused contract checks for the independent S7 fund workflow."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.runtime.actions import WorkflowActionService
from app.runtime.skill_catalog import build_production_skill_catalog
from app.runtime.workflows.fund_recommendation_v1 import FUND_RECOMMENDATION_V1
from app.schemas.agent_control import WorkflowRunStartRequest
from app.services.workflow_application_service import WorkflowApplicationService, build_default_workflow_registry


def test_fund_recommendation_is_an_independent_three_agent_workflow() -> None:
    definition = FUND_RECOMMENDATION_V1
    nodes = {node.node_id: node for node in definition.nodes}

    assert definition.name == "fund_recommendation_v1"
    assert definition.version == 1
    assert definition.required_domains == ("fund",)
    assert definition.checkpoint_schema_version == "fund-recommendation-v1"
    assert nodes["analyse_fund_landscape"].agent_name == "job_analyst"
    assert nodes["analyse_fund_landscape"].skill_name == "AnalyzeJobMarket"
    assert nodes["recommend_funds"].agent_name == "career_planner"
    assert nodes["recommend_funds"].skill_name == "RecommendResources"
    assert nodes["quality_check"].agent_name == "outcome_evaluator"
    assert nodes["quality_check"].skill_name == "QualityCheck"
    assert nodes["project_fund_recommendation"].action_name == "ProjectFundRecommendation"
    assert definition.metadata["course_root_reuse"] is False
    assert definition.metadata["evidence_floor"] == 3


def test_fund_workflow_uses_only_existing_frozen_skill_bindings() -> None:
    catalog = build_production_skill_catalog()

    assert len(catalog) == 28
    assert ("job_analyst", "AnalyzeJobMarket") in catalog
    assert ("career_planner", "RecommendResources") in catalog
    assert ("outcome_evaluator", "QualityCheck") in catalog
    assert "fund" in catalog[("job_analyst", "AnalyzeJobMarket")].required_domains
    assert "fund" in catalog[("career_planner", "RecommendResources")].required_domains
    assert "fund" in catalog[("outcome_evaluator", "QualityCheck")].required_domains
    assert build_default_workflow_registry().get("fund_recommendation_v1") is FUND_RECOMMENDATION_V1


def test_fund_recommendation_maps_profile_and_landscape_without_course_root() -> None:
    nodes = {node.node_id: node for node in FUND_RECOMMENDATION_V1.nodes}
    root = {
        "user_id": "user-1",
        "query": "推荐网络安全科研机会",
        "domain": "fund",
        "course_context": {"course_id": "course-only-context", "knowledge_point_id": "kp-only-context"},
        "profile_snapshot": {
            "dimensions": {"career_goal": "安全工程"},
            "capabilities": [{"dimension": "web_security", "score": 0.8, "confidence": 0.7}],
        },
    }
    landscape_input = nodes["analyse_fund_landscape"].input_mapper(root, {})
    assert landscape_input["domain"] == "fund"
    assert landscape_input["fund_context"]["course_context"] == root["course_context"]
    assert landscape_input["fund_context"]["profile_dimensions"] == ["web_security"]

    recommendation_input = nodes["recommend_funds"].input_mapper(
        root,
        {"analyse_fund_landscape": {"output": {"fund_landscape": [{"fund_name": "official"}]}}},
    )
    assert recommendation_input["learning_context"]["profile_snapshot"] == root["profile_snapshot"]
    assert recommendation_input["learning_context"]["fund_landscape"] == [{"fund_name": "official"}]


def test_generic_start_drops_browser_owned_fund_profile_fields() -> None:
    request = WorkflowRunStartRequest(
        workflow="fund_recommendation_v1",
        user_id=str(uuid4()),
        input={
            "query": "推荐网络安全科研机会",
            "profile_snapshot": {"dimensions": {"forged": True}},
            "persona_summary": "forged",
        },
        mode="real",
    )

    normalised = WorkflowApplicationService._normalise_input("fund_recommendation_v1", request)

    assert normalised["domain"] == "fund"
    assert "profile_snapshot" not in normalised
    assert "persona_summary" not in normalised


def test_fund_terminal_action_requires_profile_backed_recommendations_and_evidence_floor() -> None:
    evidence_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
    candidate = {
        "fund_name": "官方基金",
        "source_name": "官方机构",
        "source_url": "https://fund.example.invalid/official",
        "deadline": "以官方通知为准",
        "level": "国家级",
        "direction": "网络安全",
        "fit_score": 0.82,
        "matched_profile_dimensions": ["web_security"],
        "reason": "能力画像与方向匹配。",
        "gaps_or_risks": ["以官方通知为准"],
        "next_action": "核验官方通知。",
    }
    state = {
        "quality_check": {"output": {"accept": True}},
        "recommend_funds": {
            "output": {"content": "官方来源整理", "fund_recommendations": [candidate]},
            "evidence_snapshot_ids": evidence_ids,
        },
        "analyse_fund_landscape": {"output": {"trend": "网络安全方向"}},
    }
    root = {"profile_snapshot": {"dimensions": {}, "capabilities": [{"dimension": "web_security"}]}}
    actions = WorkflowActionService(None, storage_service=SimpleNamespace())

    result = asyncio.run(actions.project_fund_recommendation(root, state, SimpleNamespace()))

    assert result["profile_dimensions_used"] == ["web_security"]
    assert result["recommendations"][0]["evidence_snapshot_ids"] == evidence_ids

    state["recommend_funds"]["evidence_snapshot_ids"] = evidence_ids[:2]
    with pytest.raises(ValueError, match="evidence floor"):
        asyncio.run(actions.project_fund_recommendation(root, state, SimpleNamespace()))
