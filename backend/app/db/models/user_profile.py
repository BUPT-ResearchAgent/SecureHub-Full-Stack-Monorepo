# Status: [planned]

"""Compatibility shim — real model lives in ``app.db.models.identity.user_profile``."""

from app.db.models.identity.user_profile import UserProfile

__all__ = ["UserProfile"]
