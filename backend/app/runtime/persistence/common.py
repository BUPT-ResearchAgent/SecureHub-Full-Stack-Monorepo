# Status: real

"""Small shared helpers for fenced durable Runtime persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID


class PersistenceConflictError(RuntimeError):
    """A compare-and-swap write lost a concurrent update."""


class LeaseFencedError(PersistenceConflictError):
    """A stale worker attempted to write after its lease epoch was replaced."""


class RunNotFoundError(KeyError):
    """Requested durable root does not exist."""


class EventValidationError(ValueError):
    """An event violates the fixed public SSE or redaction contract."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def lease_is_active(expires_at: datetime | None) -> bool:
    """Compare lease timestamps across PostgreSQL and SQLite test dialects."""
    if expires_at is None:
        return False
    normalized = (
        expires_at.replace(tzinfo=timezone.utc)
        if expires_at.tzinfo is None
        else expires_at
    )
    return normalized > utcnow()


def as_uuid(value: UUID | str, *, field: str = "id") -> UUID:
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a UUID") from exc


def optional_uuid(value: UUID | str | None, *, field: str = "id") -> UUID | None:
    if value is None or value == "":
        return None
    return as_uuid(value, field=field)


def enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def mapping(value: Any, *, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a JSON object")
    return dict(value)


def compact_error(error: BaseException | str | None, *, limit: int = 400) -> str | None:
    if error is None:
        return None
    text = str(error).replace("\n", " ").strip()
    return text[:limit] or None


FORBIDDEN_EVENT_KEYS = frozenset(
    {
        "prompt",
        "full_prompt",
        "messages",
        "reasoning",
        "reasoning_content",
        "api_key",
        "authorization",
        "secret",
        "secret_key",
    }
)


def validate_event_payload(value: Any) -> dict[str, Any]:
    """Reject prompt/reasoning/secrets recursively before the outbox commits."""
    payload = mapping(value, field="event payload")

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                if str(key).lower() in FORBIDDEN_EVENT_KEYS:
                    raise EventValidationError(f"event payload includes forbidden key: {key!r}")
                walk(nested)
        elif isinstance(item, (list, tuple)):
            for nested in item:
                walk(nested)

    walk(payload)
    return payload


def as_snapshot_mapping(value: Any) -> dict[str, Any]:
    """Normalise compact citation/source/rights values into JSON objects."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    return {"value": str(value)}
