# Status: real

"""Strict live adapters for the controlled Agent Run real mode.

These adapters intentionally bypass the Harness defaults because those
defaults are allowed to use fixture fallbacks for development compatibility.
The real workflow can only use the real retriever and a DeepSeek provider that
was actually constructed by ``get_llm_provider("deepseek")``.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from app.llm.provider import BaseLLMProvider, LLMMessage, get_llm_provider
from app.runtime.harness.errors import (
    AgentRunPersistenceFailed,
    CancellationRequested,
    HarnessError,
    ToolUnavailable,
)
from app.runtime.harness.types import EvidenceCard


JSON_ONLY_SYSTEM_MESSAGE = (
    "Return exactly one valid JSON object matching the requested schema. "
    "Do not use Markdown fences or prose outside the JSON object. "
    "The server, not the model, owns evidence_chunk_ids."
)


class StrictProviderUnavailable(ToolUnavailable):
    """Real mode may not substitute another provider or a fixture."""

    code = "PROVIDER_UNAVAILABLE"


class StrictLLMOutputInvalid(HarnessError):
    """DeepSeek returned content that cannot be used as strict JSON output."""

    code = "LLM_OUTPUT_INVALID"


RetrieveFn = Callable[..., Awaitable[list[Any]]]
EventEmitter = Callable[[dict[str, Any]], Awaitable[None]]
CancellationCheck = Callable[[], bool]


def get_strict_deepseek_provider() -> BaseLLMProvider:
    """Return only a real DeepSeek provider; reject development fixture fallback."""
    try:
        provider = get_llm_provider("deepseek")
    except Exception as exc:
        raise StrictProviderUnavailable("DeepSeek provider is unavailable") from exc
    if getattr(provider, "provider_name", None) != "deepseek":
        raise StrictProviderUnavailable("DeepSeek provider is unavailable")
    return provider


class StrictLiveAdapters:
    """Narrow RAG/LLM callbacks used exclusively by ``mode=real`` workflows."""

    def __init__(
        self,
        *,
        provider: BaseLLMProvider | None = None,
        retrieve_fn: RetrieveFn | None = None,
        cancellation_requested: CancellationCheck | None = None,
        max_tokens: int | None = None,
    ) -> None:
        from app.core.config import get_settings
        from app.rag.retriever import retrieve

        self._provider = provider or get_strict_deepseek_provider()
        if getattr(self._provider, "provider_name", None) != "deepseek":
            raise StrictProviderUnavailable("real mode requires provider=deepseek")
        settings = get_settings()
        self._retrieve_fn = retrieve_fn or retrieve
        self._cancellation_requested = cancellation_requested or (lambda: False)
        self._max_tokens = max_tokens or settings.AGENT_RUN_REAL_MAX_TOKENS

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    @property
    def model_name(self) -> str:
        return self._provider.model_name

    def _raise_if_cancelled(self) -> None:
        if self._cancellation_requested():
            raise CancellationRequested("workflow cancellation requested")

    async def rag_retrieve(
        self,
        query: str,
        *,
        domain: str,
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[EvidenceCard]:
        """Call the real retriever directly and never add fixture evidence."""
        self._raise_if_cancelled()
        try:
            hits = await self._retrieve_fn(
                query,
                domain=domain,
                top_k=top_k,
                filter=filters,
            )
        except CancellationRequested:
            raise
        except Exception as exc:
            raise StrictProviderUnavailable("real RAG retrieval is unavailable") from exc
        self._raise_if_cancelled()
        return [self._evidence_card(hit) for hit in hits]

    async def llm_complete(
        self,
        prompt: str,
        *,
        skill_name: str,
        stream: bool = False,
        emit: EventEmitter | None = None,
    ) -> dict[str, Any]:
        """Call DeepSeek and accept only a single JSON object as output."""
        del skill_name
        self._raise_if_cancelled()
        messages = [
            LLMMessage(role="system", content=JSON_ONLY_SYSTEM_MESSAGE),
            LLMMessage(role="user", content=prompt),
        ]

        try:
            if stream:
                parts: list[str] = []
                async for chunk in self._provider.stream_generate(
                    messages,
                    temperature=0.2,
                    max_tokens=self._max_tokens,
                ):
                    self._raise_if_cancelled()
                    parts.append(chunk.content)
                    if emit is not None:
                        await emit({"event": "token", "content": chunk.content})
                    self._raise_if_cancelled()
                raw_content = "".join(parts)
                prompt_tokens = self._provider.estimate_tokens(prompt)
                completion_tokens = self._provider.estimate_tokens(raw_content)
                total_tokens = prompt_tokens + completion_tokens
            else:
                response = await self._provider.generate(
                    messages,
                    temperature=0.2,
                    max_tokens=self._max_tokens,
                )
                raw_content = response.content
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                total_tokens = response.usage.total_tokens
        except CancellationRequested:
            raise
        except StrictLLMOutputInvalid:
            raise
        except Exception as exc:
            raise StrictProviderUnavailable("DeepSeek generation is unavailable") from exc

        self._raise_if_cancelled()
        payload = self._parse_json(raw_content)
        payload["provider"] = self.provider_name
        payload["model"] = self.model_name
        payload["prompt_tokens"] = int(prompt_tokens or 0)
        payload["completion_tokens"] = int(completion_tokens or 0)
        payload["total_tokens"] = int(total_tokens or 0)
        return payload

    @staticmethod
    def _evidence_card(hit: Any) -> EvidenceCard:
        if isinstance(hit, EvidenceCard):
            return hit
        return EvidenceCard(
            chunk_id=str(hit.chunk_id),
            document_id=str(hit.document_id) if getattr(hit, "document_id", None) else None,
            domain=str(hit.domain),
            source=getattr(hit, "source", None),
            excerpt=str(getattr(hit, "chunk_text", getattr(hit, "excerpt", "")))[:500],
            reliability=float(getattr(hit, "reliability", 0.0)),
            score=float(getattr(hit, "score", 0.0)),
            metadata=dict(getattr(hit, "metadata", {}) or {}),
        )

    @staticmethod
    def _parse_json(raw_content: str) -> dict[str, Any]:
        try:
            payload = json.loads(raw_content)
        except (TypeError, json.JSONDecodeError) as exc:
            raise StrictLLMOutputInvalid("DeepSeek output is not valid JSON") from exc
        if not isinstance(payload, dict):
            raise StrictLLMOutputInvalid("DeepSeek output must be a JSON object")
        return payload


def _strict_uuid(value: UUID | str, *, field_name: str) -> UUID:
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise AgentRunPersistenceFailed(f"{field_name} is not a UUID") from exc


async def persist_strict_agent_run(
    *,
    run_id: UUID,
    workflow_run_id: UUID,
    workflow_name: str,
    user_id: UUID | str,
    agent_name: str,
    skill_name: str,
    input_summary: dict[str, Any],
    output_summary: dict[str, Any],
    evidence_chunk_ids: list[UUID | str],
    quality_score: float | None,
    status: str,
    duration_ms: int | None,
    token_usage: dict[str, Any],
) -> None:
    """Persist one real child run and verify its caller-supplied primary key."""
    if str(input_summary.get("workflow_run_id")) != str(workflow_run_id):
        raise AgentRunPersistenceFailed("workflow_run_id is missing from input_summary")

    user_uuid = _strict_uuid(user_id, field_name="user_id")
    evidence_ids = [
        _strict_uuid(chunk_id, field_name="evidence_chunk_id")
        for chunk_id in evidence_chunk_ids
    ]

    try:
        from app.db.session import get_sessionmaker
        from app.services.agent.agent_run_service import AgentRunService

        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            service = AgentRunService(session)
            stored_id = await service.begin_run(
                run_id=run_id,
                workflow_name=workflow_name,
                agent_name=agent_name,
                skill_name=skill_name,
                user_id=user_uuid,
                input_summary=input_summary,
                require_resolution=True,
            )
            if stored_id != run_id:
                raise AgentRunPersistenceFailed("agent_runs primary key mismatch")
            if status == "success":
                await service.finish_success(
                    run_id,
                    output_summary=output_summary,
                    evidence_chunk_ids=evidence_ids,
                    quality_score=quality_score,
                    duration_ms=duration_ms,
                    token_usage=token_usage,
                )
            else:
                await service.finish_failed(
                    run_id,
                    error_summary=output_summary,
                    duration_ms=duration_ms,
                )
            await session.commit()
    except AgentRunPersistenceFailed:
        raise
    except Exception as exc:
        raise AgentRunPersistenceFailed(
            "agent_runs persistence could not be verified"
        ) from exc


__all__ = [
    "AgentRunPersistenceFailed",
    "StrictLLMOutputInvalid",
    "StrictLiveAdapters",
    "StrictProviderUnavailable",
    "get_strict_deepseek_provider",
    "persist_strict_agent_run",
]
