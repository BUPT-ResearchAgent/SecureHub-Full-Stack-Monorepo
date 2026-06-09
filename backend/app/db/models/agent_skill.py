# Status: [planned]

"""Compatibility shim — real model lives in ``app.db.models.agent.agent_skill``."""

from app.db.models.agent.agent_skill import AgentSkill

__all__ = ["AgentSkill"]
