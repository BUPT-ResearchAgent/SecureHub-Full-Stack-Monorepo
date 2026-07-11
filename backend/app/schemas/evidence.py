# Status: real

"""Wire-format evidence DTO.

Single source of truth in code; the document is ``docs/api/evidence-contract.md``.
Anything that crosses the network (SSE ``evidence`` events, ``POST /api/v1/rag/search``)
must round-trip through ``EvidenceChunkDTO``.

Internal types (``EvidenceCard``, ``ChunkHit``) stay as-is and project into this DTO
at the boundary; see ``app.schemas.evidence.evidence_card_to_dto`` for the canonical
projection.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class CollectionMode(str, Enum):
    """Closed enum for ``collection_mode``; see contract §4.2."""

    MANUAL = "manual"
    API = "api"
    SCRAPLING = "scrapling"
    MEDIACRAWLER = "mediacrawler"
    MINDSPIDER_REFERENCE = "mindspider_reference"


class EvidenceChunkDTO(BaseModel):
    """Wire-format evidence chunk — see ``docs/api/evidence-contract.md``."""

    # —— identity (always required) ——
    chunk_id: str
    document_id: str

    # —— body (always required) ——
    chunk_text: str
    score: float = Field(ge=0.0, le=1.0)

    # —— source identity (always required) ——
    platform: str
    rights_note: str

    # —— source link (conditionally required; nullable iff platform == "manual") ——
    source_url: str | None = None

    # —— optional display fields ——
    title: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime | None = None
    collection_mode: CollectionMode | None = None
    asset_type: str | None = None
    page_no: int | None = None
    chapter: str | None = None
    timestamp: float | None = None
    license: str | None = None
    reliability: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _source_url_required_unless_manual(self) -> "EvidenceChunkDTO":
        """``source_url`` is required for every platform except ``manual``."""
        if self.platform != "manual" and not self.source_url:
            raise ValueError(
                "source_url is required when platform != 'manual' "
                f"(got platform={self.platform!r}, source_url={self.source_url!r})",
            )
        return self


# === Projection helpers ===================================================
#
# Internal flow:
#   ChunkHit / EvidenceCard  →  EvidenceChunkDTO
#
# Callers should not hand-roll dict assembly; use these helpers so contract
# evolution stays mechanical.


def _coerce_collection_mode(value: Any) -> CollectionMode | None:
    if value is None or value == "":
        return None
    try:
        return CollectionMode(value)
    except ValueError:
        return None


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _clamp_unit(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f < 0.0:
        return 0.0
    if f > 1.0:
        return 1.0
    return f


def evidence_card_to_dto(card: Any, *, default_platform: str = "manual") -> EvidenceChunkDTO:
    """Project an ``EvidenceCard`` (or any object with the same attrs / dict) to a DTO.

    The argument is intentionally typed as ``Any`` — we accept both
    retrieval records and the dict shape returned by explicit fixture injection.
    ``getattr`` + ``dict.get`` are unified through
    ``_lookup``.
    """

    def _lookup(name: str, default: Any = None) -> Any:
        if isinstance(card, dict):
            return card.get(name, default)
        return getattr(card, name, default)

    metadata = _lookup("metadata") or {}

    def meta(key: str, default: Any = None) -> Any:
        if isinstance(metadata, dict):
            return metadata.get(key, default)
        return default

    platform = meta("platform") or _lookup("platform") or default_platform
    source_url = (
        meta("source_url")
        or _lookup("source_url")
        or _lookup("source")
    )
    if platform == "manual" and not source_url:
        source_url = None  # explicit null per contract

    score = _clamp_unit(_lookup("score", 0.0)) or 0.0
    reliability = _clamp_unit(meta("reliability") or _lookup("reliability"))

    return EvidenceChunkDTO(
        chunk_id=str(_lookup("chunk_id")),
        document_id=str(_lookup("document_id") or ""),
        chunk_text=str(_lookup("chunk_text") or _lookup("excerpt") or ""),
        score=score,
        platform=str(platform),
        rights_note=str(meta("rights_note") or _lookup("rights_note") or ""),
        source_url=source_url,
        title=meta("title") or _lookup("title"),
        author=meta("author") or _lookup("author"),
        published_at=_coerce_datetime(meta("published_at") or _lookup("published_at")),
        fetched_at=_coerce_datetime(meta("fetched_at") or _lookup("fetched_at")),
        collection_mode=_coerce_collection_mode(meta("collection_mode") or _lookup("collection_mode")),
        asset_type=meta("asset_type") or _lookup("asset_type"),
        page_no=meta("page_no") or _lookup("page_no"),
        chapter=meta("chapter") or _lookup("chapter"),
        timestamp=meta("timestamp") or _lookup("timestamp"),
        license=meta("license") or _lookup("license"),
        reliability=reliability,
    )
