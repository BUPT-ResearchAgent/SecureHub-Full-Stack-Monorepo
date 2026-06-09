# Status: [planned]

"""Compatibility shim — real model lives in ``app.db.models.knowledge.course``."""

from app.db.models.knowledge.course import Course

__all__ = ["Course"]
