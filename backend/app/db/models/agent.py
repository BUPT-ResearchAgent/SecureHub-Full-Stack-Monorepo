# Status: [planned]

"""Compatibility shim — real model lives in ``app.db.models.agent.agent``."""

from app.db.models.agent.agent import Agent

__all__ = ["Agent"]
