# Status: [planned]

"""Compatibility shim — v1 ``kp_prerequisites`` was replaced by
``knowledge_edges`` (PK widened from ``(kp_id, prereq_kp_id)`` to
``(source_id, target_id, edge_type)``) in data-layer v2.

The column rename is **not** backward compatible at the row level: callers
that used ``KpPrerequisite(kp_id=..., prereq_kp_id=...)`` must migrate to
``KnowledgeEdge(source_id=..., target_id=..., edge_type='prerequisite')``.
The class alias below keeps ``isinstance(...)`` / type-import sites green,
but constructing rows with the old keyword arguments will raise ``TypeError``
— that is intentional, so the migration cannot silently leak.
"""

from app.db.models.knowledge.knowledge_edge import KnowledgeEdge

KpPrerequisite = KnowledgeEdge

__all__ = ["KpPrerequisite", "KnowledgeEdge"]
