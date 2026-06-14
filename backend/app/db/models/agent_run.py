# Status: [planned]

"""Compatibility shim — real model lives in ``app.db.models.agent.agent_run``."""

from app.db.models.agent.agent_run import AgentRun

__all__ = ["AgentRun"]
