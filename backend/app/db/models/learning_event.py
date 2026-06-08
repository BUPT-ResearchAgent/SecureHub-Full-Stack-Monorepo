# Status: [planned]

"""Compatibility shim — real model lives in ``app.db.models.learning.learning_event``.
v2 retargets ``kp_id`` FK from ``knowledge_points`` to ``knowledge_nodes``.
"""

from app.db.models.learning.learning_event import LearningEvent

__all__ = ["LearningEvent"]
