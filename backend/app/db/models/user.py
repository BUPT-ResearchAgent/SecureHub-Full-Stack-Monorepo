# Status: [planned]

"""Compatibility shim — v1 callers import ``from app.db.models.user import User``.
The real model now lives in ``app.db.models.identity.user``.
"""

from app.db.models.identity.user import User

__all__ = ["User"]
