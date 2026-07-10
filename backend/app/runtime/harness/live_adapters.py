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
JSON_RESPONSE_FORMAT = {"type": "json_object"}
STREAM_TOKEN_EVENT_MIN_CHARS = 64


class StrictProviderUnavailable(ToolUnavailable):
    """Real mode may not substitute another provider or a fixture."""

    code = "PROVIDER_UNAVAILABLE"


class StrictLLMOutputInvalid(HarnessError):
    """DeepSeek returned content that cannot be used as strict JSON output."""

    code = "LLM_OUTPUT_INVALID"

    def __init__(
        self,
        message: str = "DeepSeek output failed strict JSON validation",
        *,
        phase: str = "parse",
        finish_reason: str | None = None,
        content_length: int = 0,
        has_final_content: bool = False,
        parse_category: str = "invalid_json",
    ) -> None:
        safe_finish_reason = finish_reason if finish_reason in {
            "stop",
            "length",
            "tool_calls",
            "content_filter",
        } else "other" if finish_reason else "unknown"
        self.diagnostics = {
            "phase": phase,
            "finish_reason": safe_finish_reason,
            "content_length": max(0, int(content_length)),
            "has_final_content": bool(has_final_content),
            "parse_category": parse_category,
        }
        detail = "; ".join(f"{key}={value}" for key, value in self.diagnostics.items())
        super().__init__(f"{message}; {detail}")


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
        self._uses_default_retriever = retrieve_fn is None
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
        source_urls = await self._document_source_urls(hits) if self._uses_default_retriever else {}
        cards = [
            self._evidence_card(hit, document_source_url=source_urls.get(str(getattr(hit, "document_id", ""))))
            for hit in hits
        ]
        incomplete = [
            card
            for card in cards
            if (card.metadata.get("platform") or "manual") != "manual" and not card.source
        ]
        if incomplete:
            raise StrictProviderUnavailable("real evidence source metadata is incomplete")
        return cards

    async def _document_source_urls(self, hits: list[Any]) -> dict[str, str]:
        document_ids = {
            str(getattr(hit, "document_id", ""))
            for hit in hits
            if getattr(hit, "document_id", None)
        }
        if not document_ids:
            return {}
        try:
            from sqlalchemy import select

            from app.db.models.knowledge.document import Document
            from app.db.session import get_sessionmaker

            async with get_sessionmaker()() as session:
                rows = (
                    await session.execute(
                        select(Document.id, Document.url, Document.metadata_).where(
                            Document.id.in_(document_ids)
                        )
                    )
                ).all()
        except Exception as exc:
            raise StrictProviderUnavailable("real evidence source metadata is unavailable") from exc
        source_urls: dict[str, str] = {}
        for document_id, document_url, document_metadata in rows:
            metadata = document_metadata or {}
            source_url = document_url or metadata.get("source_url") or metadata.get("url")
            if source_url:
                source_urls[str(document_id)] = str(source_url)
        return source_urls

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
                pending_event_parts: list[str] = []
                pending_event_chars = 0
                finish_reason: str | None = None

                async def flush_token_event() -> None:
                    nonlocal pending_event_chars
                    if emit is None or not pending_event_parts:
                        return
                    self._raise_if_cancelled()
                    content = "".join(pending_event_parts)
                    pending_event_parts.clear()
                    pending_event_chars = 0
                    await emit({"event": "token", "content": content})
                    self._raise_if_cancelled()

                async for chunk in self._provider.stream_generate(
                    messages,
                    temperature=0.2,
                    max_tokens=self._max_tokens,
                    response_format=JSON_RESPONSE_FORMAT,
                ):
                    self._raise_if_cancelled()
                    if chunk.finish_reason is not None:
                        finish_reason = chunk.finish_reason
                    if chunk.content:
                        parts.append(chunk.content)
                        if emit is not None:
                            pending_event_parts.append(chunk.content)
                            pending_event_chars += len(chunk.content)
                            if pending_event_chars >= STREAM_TOKEN_EVENT_MIN_CHARS:
                                await flush_token_event()
                    self._raise_if_cancelled()
                await flush_token_event()
                raw_content = "".join(parts)
                prompt_tokens = self._provider.estimate_tokens(prompt)
                completion_tokens = self._provider.estimate_tokens(raw_content)
                total_tokens = prompt_tokens + completion_tokens
            else:
                response = await self._provider.generate(
                    messages,
                    temperature=0.2,
                    max_tokens=self._max_tokens,
                    response_format=JSON_RESPONSE_FORMAT,
                )
                raw_content = response.content
                finish_reason = response.finish_reason
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
        payload = self._parse_json(raw_content, finish_reason=finish_reason)
        payload["provider"] = self.provider_name
        payload["model"] = self.model_name
        payload["prompt_tokens"] = int(prompt_tokens or 0)
        payload["completion_tokens"] = int(completion_tokens or 0)
        payload["total_tokens"] = int(total_tokens or 0)
        return payload

    @staticmethod
    def _evidence_card(hit: Any, *, document_source_url: str | None = None) -> EvidenceCard:
        if isinstance(hit, EvidenceCard):
            if hit.source or not document_source_url:
                return hit
            return hit.model_copy(update={"source": document_source_url})
        metadata = dict(getattr(hit, "metadata", {}) or {})
        return EvidenceCard(
            chunk_id=str(hit.chunk_id),
            document_id=str(hit.document_id) if getattr(hit, "document_id", None) else None,
            domain=str(hit.domain),
            source=(
                getattr(hit, "source", None)
                or metadata.get("source_url")
                or metadata.get("url")
                or document_source_url
            ),
            excerpt=str(getattr(hit, "chunk_text", getattr(hit, "excerpt", "")))[:500],
            reliability=float(getattr(hit, "reliability", 0.0)),
            score=float(getattr(hit, "score", 0.0)),
            metadata=metadata,
        )

    @staticmethod
    def _parse_json(raw_content: str, *, finish_reason: str | None = None) -> dict[str, Any]:
        has_final_content = isinstance(raw_content, str) and bool(raw_content.strip())
        content_length = len(raw_content) if isinstance(raw_content, str) else 0
        if not has_final_content:
            raise StrictLLMOutputInvalid(
                phase="parse",
                finish_reason=finish_reason,
                content_length=content_length,
                has_final_content=False,
                parse_category="no_final_content",
            )
        try:
            payload = json.loads(raw_content)
        except (TypeError, json.JSONDecodeError) as exc:
            raise StrictLLMOutputInvalid(
                phase="parse",
                finish_reason=finish_reason,
                content_length=content_length,
                has_final_content=True,
                parse_category="invalid_json",
            ) from exc
        if not isinstance(payload, dict):
            raise StrictLLMOutputInvalid(
                phase="parse",
                finish_reason=finish_reason,
                content_length=content_length,
                has_final_content=True,
                parse_category="non_object_json",
            )
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
