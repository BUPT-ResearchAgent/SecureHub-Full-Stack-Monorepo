# Status: [planned]

from dataclasses import dataclass

from app.agents.base import BaseAgent, BaseSkill
from app.runtime.capability_manifest import list_agents


@dataclass(frozen=True)
class RouterWeights:
    cap: float = 0.35
    ctx: float = 0.25
    tool: float = 0.10
    risk: float = 0.10
    hist: float = 0.20


@dataclass(frozen=True)
class RouteTask:
    query: str
    domain: str = "course_websec"
    required_tools: tuple[str, ...] = ("rag.retrieve", "llm.xfyun")
    risk_tolerance: str = "medium"


@dataclass(frozen=True)
class AgentSkillRoute:
    agent: type[BaseAgent]
    skill_name: str
    skill: type[BaseSkill]
    score: float


def score_agent(agent: type[BaseAgent], task: RouteTask, weights: RouterWeights | None = None) -> float:
    selected_weights = weights or RouterWeights()
    capability = sum(agent.capability_vector.as_vector()[:9]) / 9
    tool_score = 1.0 if all(tool in agent.tools for tool in task.required_tools) else 0.0
    risk_score = 1.0 if agent.risk_level in {"low", task.risk_tolerance} else 0.5
    context_score = 1.0 if task.domain in {"course_websec", "policy", "paper", "job", "competition", "fund"} else 0.4
    history_score = 0.5
    return (
        selected_weights.cap * capability
        + selected_weights.ctx * context_score
        + selected_weights.tool * tool_score
        + selected_weights.risk * risk_score
        + selected_weights.hist * history_score
    )


def route(task: RouteTask, *, min_score: float = 0.4) -> AgentSkillRoute:
    candidates: list[AgentSkillRoute] = []
    for agent in list_agents():
        agent_score = score_agent(agent, task)
        for skill_name, skill in agent.skills.items():
            if not skill.applicable_domains or task.domain in skill.applicable_domains:
                candidates.append(AgentSkillRoute(agent=agent, skill_name=skill_name, skill=skill, score=agent_score))
    if not candidates:
        raise ValueError("No available agent skill candidates")
    best = max(candidates, key=lambda candidate: candidate.score)
    if best.score < min_score:
        raise ValueError(f"No route reached minimum score: {best.score:.3f}")
    return best
