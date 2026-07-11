# Status: real

"""Deterministic root/node/provider budget accounting.

Budget decisions stay inside RuntimeEngine.  A provider never gets a chance to
silently lower QualityCheck requirements after a budget threshold is reached.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.runtime.contracts import BudgetLimits, BudgetUsage, ErrorCode


class BudgetExceeded(RuntimeError):
    code = ErrorCode.BUDGET_EXCEEDED


@dataclass(frozen=True, slots=True)
class BudgetSnapshot:
    limits: BudgetLimits
    usage: BudgetUsage
    node_usage: dict[str, BudgetUsage]
    provider_usage: dict[str, BudgetUsage]


class BudgetController:
    """Reads/writes the JSON budget ledger without accepting opaque fields."""

    @staticmethod
    def snapshot(raw: dict[str, Any] | None) -> BudgetSnapshot:
        value = dict(raw or {})
        limits = BudgetLimits.model_validate(value.get("limits") or value.get("root_limits") or {})
        usage = BudgetUsage.model_validate(value.get("usage") or {})
        node_usage = {
            str(key): BudgetUsage.model_validate(item or {})
            for key, item in dict(value.get("node_usage") or {}).items()
            if isinstance(item, dict)
        }
        provider_usage = {
            str(key): BudgetUsage.model_validate(item or {})
            for key, item in dict(value.get("provider_usage") or {}).items()
            if isinstance(item, dict)
        }
        return BudgetSnapshot(limits, usage, node_usage, provider_usage)

    @classmethod
    def assert_can_start_node(
        cls,
        raw: dict[str, Any] | None,
        *,
        node_id: str,
        estimated_tokens: int,
        node_limit_tokens: int | None = None,
    ) -> None:
        snapshot = cls.snapshot(raw)
        cls._assert_tokens(snapshot.usage, snapshot.limits.max_tokens, estimated_tokens, "root")
        node = snapshot.node_usage.get(node_id, BudgetUsage())
        cls._assert_tokens(node, node_limit_tokens, estimated_tokens, f"node:{node_id}")
        if snapshot.limits.max_nodes is not None and snapshot.usage.nodes + 1 > snapshot.limits.max_nodes:
            raise BudgetExceeded("root node budget exhausted")

    @classmethod
    def assert_can_start_provider(
        cls,
        raw: dict[str, Any] | None,
        *,
        provider: str,
        estimated_tokens: int,
    ) -> None:
        snapshot = cls.snapshot(raw)
        cls._assert_tokens(snapshot.usage, snapshot.limits.max_tokens, estimated_tokens, "root")
        provider_usage = snapshot.provider_usage.get(provider, BudgetUsage())
        cls._assert_tokens(
            provider_usage,
            snapshot.limits.provider_max_tokens.get(provider),
            estimated_tokens,
            f"provider:{provider}",
        )
        if (
            snapshot.limits.max_provider_calls is not None
            and snapshot.usage.provider_calls + 1 > snapshot.limits.max_provider_calls
        ):
            raise BudgetExceeded("root provider-call budget exhausted")

    @classmethod
    def reserve_node(
        cls,
        raw: dict[str, Any] | None,
        *,
        node_id: str,
        estimated_tokens: int,
    ) -> dict[str, Any]:
        snapshot = cls.snapshot(raw)
        node = snapshot.node_usage.get(node_id, BudgetUsage())
        return cls._write(
            raw,
            usage=snapshot.usage.model_copy(
                update={
                    "nodes": snapshot.usage.nodes + 1,
                    "reserved_tokens": snapshot.usage.reserved_tokens + max(0, estimated_tokens),
                }
            ),
            node_usage={
                **snapshot.node_usage,
                node_id: node.model_copy(
                    update={
                        "nodes": node.nodes + 1,
                        "reserved_tokens": node.reserved_tokens + max(0, estimated_tokens),
                    }
                ),
            },
        )

    @classmethod
    def record_provider_usage(
        cls,
        raw: dict[str, Any] | None,
        *,
        node_id: str,
        provider: str,
        usage: dict[str, Any] | None,
        cost_usd: float = 0.0,
    ) -> dict[str, Any]:
        snapshot = cls.snapshot(raw)
        incoming = cls._usage(usage, cost_usd=cost_usd)
        previous_node = snapshot.node_usage.get(node_id, BudgetUsage())
        reserved = previous_node.reserved_tokens
        root = cls._add(snapshot.usage, incoming, provider_call=True).model_copy(
            update={"reserved_tokens": max(0, snapshot.usage.reserved_tokens - reserved)}
        )
        node = cls._add(previous_node, incoming).model_copy(update={"reserved_tokens": 0})
        provider_usage = cls._add(snapshot.provider_usage.get(provider, BudgetUsage()), incoming, provider_call=True)
        if snapshot.limits.max_tokens is not None and root.total_tokens > snapshot.limits.max_tokens:
            raise BudgetExceeded("root token budget exhausted")
        if snapshot.limits.max_cost_usd is not None and root.cost_usd > snapshot.limits.max_cost_usd:
            raise BudgetExceeded("root cost budget exhausted")
        return cls._write(
            raw,
            usage=root,
            node_usage={**snapshot.node_usage, node_id: node},
            provider_usage={**snapshot.provider_usage, provider: provider_usage},
        )

    @staticmethod
    def _assert_tokens(usage: BudgetUsage, limit: int | None, estimated: int, scope: str) -> None:
        if limit is not None and usage.total_tokens + usage.reserved_tokens + max(0, estimated) > limit:
            raise BudgetExceeded(f"{scope} token budget exhausted")

    @staticmethod
    def _usage(usage: dict[str, Any] | None, *, cost_usd: float) -> BudgetUsage:
        value = dict(usage or {})
        total = int(value.get("total_tokens") or 0)
        prompt = int(value.get("prompt_tokens") or 0)
        completion = int(value.get("completion_tokens") or 0)
        if total <= 0:
            total = prompt + completion
        return BudgetUsage(
            prompt_tokens=max(0, prompt),
            completion_tokens=max(0, completion),
            total_tokens=max(0, total),
            cost_usd=max(0.0, float(cost_usd)),
        )

    @staticmethod
    def _add(current: BudgetUsage, incoming: BudgetUsage, *, provider_call: bool = False) -> BudgetUsage:
        return BudgetUsage(
            prompt_tokens=current.prompt_tokens + incoming.prompt_tokens,
            completion_tokens=current.completion_tokens + incoming.completion_tokens,
            total_tokens=current.total_tokens + incoming.total_tokens,
            cost_usd=current.cost_usd + incoming.cost_usd,
            provider_calls=current.provider_calls + (1 if provider_call else 0),
            nodes=current.nodes,
            reserved_tokens=current.reserved_tokens,
        )

    @staticmethod
    def _write(
        raw: dict[str, Any] | None,
        *,
        usage: BudgetUsage,
        node_usage: dict[str, BudgetUsage],
        provider_usage: dict[str, BudgetUsage] | None = None,
    ) -> dict[str, Any]:
        value = dict(raw or {})
        value["usage"] = usage.model_dump(mode="json")
        value["node_usage"] = {key: item.model_dump(mode="json") for key, item in node_usage.items()}
        if provider_usage is not None:
            value["provider_usage"] = {
                key: item.model_dump(mode="json") for key, item in provider_usage.items()
            }
        return value


__all__ = ["BudgetController", "BudgetExceeded", "BudgetSnapshot"]
