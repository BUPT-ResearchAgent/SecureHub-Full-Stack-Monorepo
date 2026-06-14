# Status: [planned]

"""Compatibility shim — real model lives in ``app.db.models.learning.quiz_item``.
v2 retargets ``kp_id`` FK from ``knowledge_points`` to ``knowledge_nodes``.
"""

from app.db.models.learning.quiz_item import QuizItem

__all__ = ["QuizItem"]
