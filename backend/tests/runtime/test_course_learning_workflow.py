# Status: real

"""课程学习工作流图结构校验：确保 DAG 节点和边与文档设计一致。"""

from __future__ import annotations

import pytest

from app.runtime.graphs.course_learning import (
    CourseState,
    build_course_learning_graph,
    quality_branch,
)


def test_graph_builds_without_error():
    graph = build_course_learning_graph()
    assert graph is not None
    # LangGraph compiled graph 有 get_graph 方法
    drawable = graph.get_graph()
    assert drawable is not None


def test_graph_nodes_match_7_stage_contract():
    graph = build_course_learning_graph()
    node_names = list(graph.get_graph().nodes.keys())
    expected = {"build_persona", "plan", "generate_resources", "quality", "recommend", "update"}
    for name in expected:
        assert name in node_names, f"missing node: {name}"


def test_quality_branch_accept_leads_to_recommend():
    state: CourseState = {"quality": {"accept": True}}
    assert quality_branch(state) == "recommend"


def test_quality_branch_reject_within_retry_leads_to_regen():
    state: CourseState = {"quality": {"accept": False}, "iteration": 0}
    assert quality_branch(state) == "regen"


def test_quality_branch_reject_max_retries_leads_to_recommend():
    state: CourseState = {"quality": {"accept": False}, "iteration": 3}
    assert quality_branch(state) == "recommend"
