# Status: [planned]

"""Compatibility shim — v1 ``knowledge_points`` was renamed to ``knowledge_nodes``
in data-layer v2. ``KnowledgePoint`` is now an alias for :class:`KnowledgeNode`,
so existing imports keep working but new code should reference
``KnowledgeNode`` directly.
"""

from app.db.models.knowledge.knowledge_node import KnowledgeNode

# Class-level alias keeps ``KnowledgePoint(...)`` callable, while ``__tablename__``
# resolves to ``knowledge_nodes`` (the v2 table).
KnowledgePoint = KnowledgeNode

__all__ = ["KnowledgePoint", "KnowledgeNode"]
