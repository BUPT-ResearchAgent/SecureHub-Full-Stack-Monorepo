# Status: [planned]

from typing import TypeVar

from app.agents.base import BaseAgent

AgentT = TypeVar("AgentT", bound=type[BaseAgent])

_AGENTS: dict[str, type[BaseAgent]] = {}


def register_agent(agent_cls: AgentT) -> AgentT:
    if agent_cls.name in _AGENTS:
        raise ValueError(f"Agent already registered: {agent_cls.name}")
    _AGENTS[agent_cls.name] = agent_cls
    if len(_AGENTS) > 9:
        raise ValueError("SecureHub must keep exactly 9 agent roles; refusing a 10th role")
    return agent_cls


def get_agent(name: str) -> type[BaseAgent]:
    try:
        return _AGENTS[name]
    except KeyError as exc:
        raise KeyError(f"Agent not registered: {name}") from exc


def list_agents() -> list[type[BaseAgent]]:
    return list(_AGENTS.values())


def register_agents() -> list[type[BaseAgent]]:
    from app.agents.policy_interpreter.agent import PolicyInterpreterAgent
    from app.agents.hot_analyst.agent import HotAnalystAgent
    from app.agents.job_analyst.agent import JobAnalystAgent
    from app.agents.competition_advisor.agent import CompetitionAdvisorAgent
    from app.agents.career_planner.agent import CareerPlannerAgent
    from app.agents.topic_explorer.agent import TopicExplorerAgent
    from app.agents.doc_archivist.agent import DocArchivistAgent
    from app.agents.task_orchestrator.agent import TaskOrchestratorAgent
    from app.agents.outcome_evaluator.agent import OutcomeEvaluatorAgent

    for agent_cls in [
        PolicyInterpreterAgent,
        HotAnalystAgent,
        JobAnalystAgent,
        CompetitionAdvisorAgent,
        CareerPlannerAgent,
        TopicExplorerAgent,
        DocArchivistAgent,
        TaskOrchestratorAgent,
        OutcomeEvaluatorAgent,
    ]:
        if agent_cls.name not in _AGENTS:
            register_agent(agent_cls)
    return list_agents()
