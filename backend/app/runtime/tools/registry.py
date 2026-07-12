# Status: real

"""Strict registry for explicitly model-callable low-level tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    risk_level: Literal["low", "medium", "high"] = "low"
    permission: Literal["ALLOW", "ASK", "DENY"] = "DENY"
    timeout_seconds: float = 15.0
    idempotency_required: bool = True
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.name or self.timeout_seconds <= 0:
            raise ValueError("tool requires a name and positive timeout")


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._tools:
            raise ValueError(f"tool already registered: {definition.name}")
        self._tools[definition.name] = definition

    def get(self, name: str) -> ToolDefinition:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"model tool is not registered: {name}") from exc

    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(self._tools.values())


__all__ = ["ToolDefinition", "ToolRegistry"]
