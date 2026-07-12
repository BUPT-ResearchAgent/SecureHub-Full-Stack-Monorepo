# Status: real

"""ALLOW/ASK/DENY policy for model tools, never Runtime ports or actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.runtime.tools.registry import ToolDefinition


class ToolPolicyError(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    outcome: Literal["ALLOW", "ASK", "DENY"]
    reason: str


class PolicyEngine:
    """Central deterministic policy with no shell/filesystem escape hatch."""

    _FORBIDDEN_NAMES = frozenset({"shell", "filesystem", "browser", "runtime_port", "workflow_action"})

    def decide(self, tool: ToolDefinition, *, owner_matches: bool = True) -> PolicyDecision:
        lowered = tool.name.lower()
        if any(token in lowered for token in self._FORBIDDEN_NAMES):
            return PolicyDecision("DENY", "production agents cannot select shell, filesystem, browser, port, or action tools")
        if not owner_matches:
            return PolicyDecision("DENY", "cross-owner access is denied")
        if tool.risk_level == "high":
            return PolicyDecision("ASK", "high-risk model tool requires explicit approval")
        if tool.permission == "DENY":
            return PolicyDecision("DENY", "tool definition denies model invocation")
        if tool.permission == "ASK" or tool.risk_level == "medium":
            return PolicyDecision("ASK", "tool policy requires explicit approval")
        return PolicyDecision("ALLOW", "low-risk tool is explicitly allowed")

    def require_allowed(self, tool: ToolDefinition, *, owner_matches: bool = True) -> None:
        decision = self.decide(tool, owner_matches=owner_matches)
        if decision.outcome != "ALLOW":
            raise ToolPolicyError(decision.reason)


__all__ = ["PolicyDecision", "PolicyEngine", "ToolPolicyError"]
