# Status: real

"""Agent 路由评分的单元测试：验证 score_agent 和 route 函数行为。"""

from __future__ import annotations

import pytest

from app.agents.career_planner.agent import CareerPlannerAgent
from app.runtime.capability_manifest import register_agents
from app.runtime.router import (
    RouteTask,
    RouterWeights,
    route,
    score_agent,
)

# 在测试前确保所有 9 智能体已注册
register_agents()


def test_score_agent_returns_nonzero_for_career_planner():
    task = RouteTask(query="SQL injection", domain="course_websec")
    score = score_agent(CareerPlannerAgent, task)
    assert score > 0.0, "career_planner should score > 0 for course_websec"


def test_score_agent_uses_weights():
    task = RouteTask(query="SQL injection", domain="course_websec")
    custom_weights = RouterWeights(cap=1.0, ctx=0.0, tool=0.0, risk=0.0, hist=0.0)
    score = score_agent(CareerPlannerAgent, task, weights=custom_weights)
    assert score > 0.0


def test_route_returns_best_candidate_for_course_domain():
    task = RouteTask(query="generate doc on SQL injection", domain="course_websec")
    candidate = route(task)
    assert candidate.skill_name
    assert candidate.agent
    assert candidate.score > 0.0


def test_route_raises_on_unmatched_domain():
    task = RouteTask(query="something", domain="nonexistent_domain")
    with pytest.raises(ValueError):
        route(task, min_score=1.0)


def test_all_9_agents_have_valid_capability_vectors():
    from app.runtime.capability_manifest import list_agents

    agents = list_agents()
    assert len(agents) == 9
    for agent in agents:
        vec = agent.capability_vector.as_vector()
        assert len(vec) == 64
        assert all(0.0 <= v <= 1.0 for v in vec[:9])
