# Status: [planned]

"""Compatibility shim — real model lives in ``app.db.models.knowledge.chunk``
after the data-layer v2 reshuffle (``embedding`` is now nullable, plus
``embedding_status`` / ``token_count`` columns).
"""

from app.db.models.knowledge.chunk import Chunk

__all__ = ["Chunk"]
