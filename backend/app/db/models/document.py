# Status: [planned]

"""Compatibility shim — real model lives in ``app.db.models.knowledge.document``
after the data-layer v2 reshuffle (``raw_text`` is now nullable, plus
``content_hash`` / ``status`` columns).
"""

from app.db.models.knowledge.document import Document

__all__ = ["Document"]
