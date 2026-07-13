# Status: real

"""Canonical, fail-closed SkillExecutor.

It has one job: turn an accepted step attempt into a strict CandidateOutput.
QualityCheck routing and artifact persistence intentionally remain in
RuntimeEngine workflow nodes.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from app.llm.provider import BaseLLMProvider, LLMMessage, get_llm_provider
from app.rag.retriever import retrieve
from app.runtime.context_builder import ContextBuilder
from app.runtime.contracts import ErrorCode, ExecutionMode, EvidenceRef
from app.runtime.harness.contracts import CandidateOutput, SkillDefinition
from app.runtime.harness.context import ExecutionCancelled, ExecutionContext
from app.runtime.harness.fixtures import default_evidence_fixtures
from app.runtime.provider_policy import ProviderPolicy, ProviderPolicyError
from app.runtime.guardrails.input_filter import review_input
from app.runtime.guardrails.output_filter import safety_review
from app.runtime.guardrails.prompt_injection_check import detect_prompt_injection


class SkillExecutionError(RuntimeError):
    def __init__(self, code: ErrorCode | str, message: str, *, recoverable: bool = False) -> None:
        self.code = str(code)
        self.recoverable = recoverable
        super().__init__(message)


class ProviderStreamUnavailable(SkillExecutionError):
    """An observed provider failure that is eligible for real fallback."""

    def __init__(self, message: str, *, visible_tokens: int = 0) -> None:
        self.visible_tokens = visible_tokens
        super().__init__(ErrorCode.PROVIDER_UNAVAILABLE, message, recoverable=True)


class RetrieverPort(Protocol):
    async def retrieve(self, query: str, *, domain: str, top_k: int, filters: dict[str, Any] | None = None) -> list[Any]: ...


ProviderResolver = Callable[[ExecutionContext], BaseLLMProvider]
FallbackProviderResolver = Callable[[str, ExecutionContext], BaseLLMProvider]


class SkillExecutor:
    def __init__(
        self,
        *,
        retriever: RetrieverPort | None = None,
        provider_resolver: ProviderResolver | None = None,
        evidence_snapshot_store: Any | None = None,
        provider_call_store: Any | None = None,
        context_builder: ContextBuilder | None = None,
        provider_policy: ProviderPolicy | None = None,
        fallback_provider_resolver: FallbackProviderResolver | None = None,
    ) -> None:
        self._retriever = retriever
        self._provider_resolver = provider_resolver or self._default_provider
        self._evidence_snapshot_store = evidence_snapshot_store
        self._provider_call_store = provider_call_store
        self._context_builder = context_builder or ContextBuilder()
        self._provider_policy = provider_policy or ProviderPolicy()
        self._fallback_provider_resolver = fallback_provider_resolver or self._default_fallback_provider

    async def execute(
        self,
        definition: SkillDefinition,
        raw_input: BaseModel | dict[str, Any],
        context: ExecutionContext,
    ) -> CandidateOutput:
        """Run the only legal Skill lifecycle and return a pre-quality candidate."""
        await context.require_not_cancelled()
        try:
            input_value = (
                raw_input
                if isinstance(raw_input, definition.input_model)
                else definition.input_model.model_validate(
                    raw_input.model_dump(mode="json") if isinstance(raw_input, BaseModel) else raw_input
                )
            )
        except ValidationError as exc:
            raise SkillExecutionError(ErrorCode.INVALID_INPUT, "skill input validation failed") from exc

        if "input" in definition.guardrails:
            self._assert_safe_text(
                json.dumps(input_value.model_dump(mode="json"), ensure_ascii=False, default=str),
                boundary="input",
            )
        await self._emit(context, "progress", {"node_status": "retrieving", "percentage": 15})
        evidence_items = await self._retrieve(definition, input_value, context)
        if len(evidence_items) < definition.evidence_floor:
            raise SkillExecutionError(
                ErrorCode.INSUFFICIENT_EVIDENCE,
                f"skill {definition.name} requires {definition.evidence_floor} evidence chunks",
            )
        if "retrieved_prompt" in definition.guardrails:
            self._assert_safe_text(
                "\n".join(str(item.get("excerpt") or "") for item in evidence_items),
                boundary="retrieved_evidence",
            )
        await context.require_not_cancelled()
        evidence_refs = await self._snapshot_evidence(evidence_items, definition, context)
        await self._emit(
            context,
            "evidence",
            {
                # ``items`` is the frozen public SSE shape.  It is assembled
                # from the retrieved records plus the durable snapshot IDs;
                # fixture evidence is never used for a real context.
                "items": [
                    self._evidence_event_item(record, snapshot)
                    for record, snapshot in zip(evidence_items, evidence_refs, strict=False)
                ],
                "evidence_snapshot_ids": [str(item.evidence_snapshot_id) for item in evidence_refs],
            },
        )

        prompt = self._context_builder.build(
            prompt_template=definition.prompt_template,
            input_value=input_value,
            evidence=evidence_items,
            persona_summary=context.persona_summary,
            output_model=definition.output_model,
        )
        request_digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        try:
            raw_text, usage, provider_call_id, actual_provider, stream_attempt = await self._call_with_fallback(
                definition=definition,
                context=context,
                prompt=prompt,
                request_digest=request_digest,
            )
        except ProviderPolicyError as exc:
            raise SkillExecutionError(ErrorCode.PROVIDER_UNAVAILABLE, "provider policy rejected this real call") from exc

        try:
            payload = json.loads(raw_text)
            if not isinstance(payload, dict):
                raise TypeError("provider returned non-object JSON")
            # The model cannot choose or fabricate evidence linkage.
            if "evidence_chunk_ids" in definition.output_model.model_fields:
                payload["evidence_chunk_ids"] = [str(item.chunk_id) for item in evidence_refs]
            output = definition.output_model.model_validate(payload)
        except (TypeError, ValueError, ValidationError, json.JSONDecodeError) as exc:
            category = self._strict_parse_category(exc)
            await self._complete_provider_call(
                provider_call_id,
                outcome="known_error",
                usage=usage,
                lease_epoch=context.lease_epoch,
                response_ref={
                    "parse_category": category,
                    "validation_errors": self._validation_error_summary(exc),
                    "content_length": len(raw_text),
                    "response_digest": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
                },
            )
            raise SkillExecutionError(ErrorCode.STRICT_PARSE_FAILED, "provider output failed strict schema parsing") from exc

        if "output" in definition.guardrails:
            try:
                reviewed_output = safety_review(output)
                if not isinstance(reviewed_output, definition.output_model):
                    raise TypeError("output guardrail changed the validated schema type")
                output = reviewed_output
            except Exception as exc:
                await self._complete_provider_call(
                    provider_call_id,
                    outcome="known_error",
                    usage=usage,
                    lease_epoch=context.lease_epoch,
                    response_ref={"guardrail": "output", "response_digest": hashlib.sha256(raw_text.encode("utf-8")).hexdigest()},
                )
                raise SkillExecutionError(ErrorCode.GUARDRAIL_BLOCKED, "output guardrail rejected provider output") from exc

        await context.require_not_cancelled()
        output_payload = output.model_dump(mode="json")
        # This is a strictly parsed candidate, not the provider's raw text or
        # reasoning. Persisting it with the completed journal entry lets a
        # recovery worker finish the durable step without issuing a duplicate
        # external request after a local crash.
        await self._complete_provider_call(
            provider_call_id,
            outcome="success",
            usage=usage,
            lease_epoch=context.lease_epoch,
            response_ref={
                "candidate_output": output_payload,
                "candidate_output_digest": hashlib.sha256(
                    json.dumps(output_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest(),
                "evidence_snapshot_ids": [str(item.evidence_snapshot_id) for item in evidence_refs],
            },
        )
        await self._emit(context, "progress", {"node_status": "candidate_ready", "percentage": 75})
        return CandidateOutput(
            output=output,
            evidence=tuple(evidence_refs),
            provider_call_id=str(provider_call_id),
            actual_provider=getattr(actual_provider, "provider_name", None),
            actual_model=getattr(actual_provider, "model_name", None),
            usage=usage,
            stream_attempt=stream_attempt,
        )

    async def _call_with_fallback(
        self,
        *,
        definition: SkillDefinition,
        context: ExecutionContext,
        prompt: str,
        request_digest: str,
    ) -> tuple[str, dict[str, int], str, BaseLLMProvider, int]:
        """Call one real provider, then transparently switch to another real one.

        The replacement starts a fresh journal row and stream attempt.  When a
        user has already seen primary tokens, the trace and first replacement
        token tell the reducer to discard the old draft rather than append it.
        """
        route = self._provider_policy.route_for(
            mode=context.mode,
            requested_provider=context.provider_selection.requested_provider,
        )
        provider = self._provider_resolver(context)
        provider_name = str(getattr(provider, "provider_name", "unknown"))
        if context.mode == ExecutionMode.REAL and provider_name == "fixture":
            raise SkillExecutionError(ErrorCode.PROVIDER_UNAVAILABLE, "real mode cannot use fixture provider")
        stream_attempt = 1
        call_id = await self._start_provider_call(
            definition=definition,
            context=context,
            provider=provider,
            request_digest=request_digest,
            stream_attempt=stream_attempt,
        )
        try:
            self._assert_provider_available(provider_name)
            raw, usage = await self._call_provider(
                provider,
                prompt,
                definition,
                context,
                call_id,
                stream_attempt=stream_attempt,
            )
            self._provider_policy.record_success(provider_name)
            return raw, usage, call_id, provider, stream_attempt
        except ExecutionCancelled:
            await self._complete_provider_call(call_id, outcome="cancelled", usage={}, lease_epoch=context.lease_epoch)
            raise
        except ProviderStreamUnavailable as exc:
            await self._complete_provider_call(
                call_id,
                outcome="unavailable",
                usage={},
                lease_epoch=context.lease_epoch,
                response_ref={"failure_code": str(exc.code)},
            )
            self._provider_policy.record_failure(provider_name)
            if context.mode != ExecutionMode.REAL or definition.fallback_policy != "explicit-real-provider-only":
                raise
            # A3 S2-S4 intentionally run direct DeepSeek. Spark is an S8
            # external gate and must not be attempted as an implicit fallback
            # merely because a DeepSeek call is temporarily unavailable.
            fallback_name = (
                None
                if context.provider_selection.policy_version == "deepseek-direct-v1"
                else route.fallback
            )
            if not fallback_name or fallback_name == provider_name:
                raise
            try:
                fallback = self._fallback_provider_resolver(fallback_name, context)
            except Exception as fallback_resolution_error:
                raise SkillExecutionError(
                    ErrorCode.PROVIDER_UNAVAILABLE,
                    "declared real fallback provider is unavailable",
                    recoverable=True,
                ) from fallback_resolution_error
            actual_fallback = str(getattr(fallback, "provider_name", "unknown"))
            if actual_fallback in {"fixture", "unknown"}:
                raise SkillExecutionError(ErrorCode.PROVIDER_UNAVAILABLE, "fallback provider is not a declared real provider")
            self._assert_provider_available(actual_fallback)
            replacement = exc.visible_tokens > 0
            if replacement:
                await self._emit(
                    context,
                    "trace",
                    {
                        "provider_call_id": call_id,
                        "stream_attempt": stream_attempt,
                        "actual_provider": provider_name,
                        "actual_model": getattr(provider, "model_name", None),
                        "provider_switch": {
                            "from_provider": provider_name,
                            "from_model": getattr(provider, "model_name", None),
                            "to_provider": actual_fallback,
                            "to_model": getattr(fallback, "model_name", None),
                            "reason": ErrorCode.PROVIDER_UNAVAILABLE.value,
                            "replace_draft": True,
                        },
                        "replace_draft": True,
                    },
                )
            stream_attempt = 2
            fallback_call_id = await self._start_provider_call(
                definition=definition,
                context=context,
                provider=fallback,
                request_digest=request_digest,
                stream_attempt=stream_attempt,
            )
            try:
                raw, usage = await self._call_provider(
                    fallback,
                    prompt,
                    definition,
                    context,
                    fallback_call_id,
                    stream_attempt=stream_attempt,
                    replace_draft=replacement,
                    replaces_stream_attempt=1 if replacement else None,
                )
                self._provider_policy.record_success(actual_fallback)
                return raw, usage, fallback_call_id, fallback, stream_attempt
            except ExecutionCancelled:
                await self._complete_provider_call(
                    fallback_call_id,
                    outcome="cancelled",
                    usage={},
                    lease_epoch=context.lease_epoch,
                )
                raise
            except ProviderStreamUnavailable as fallback_error:
                await self._complete_provider_call(
                    fallback_call_id,
                    outcome="unavailable",
                    usage={},
                    lease_epoch=context.lease_epoch,
                    response_ref={"failure_code": str(fallback_error.code)},
                )
                self._provider_policy.record_failure(actual_fallback)
                raise fallback_error
            except Exception as fallback_error:  # an opaque fallback boundary remains unknown
                await self._unknown_provider_call(
                    fallback_call_id,
                    message=str(fallback_error),
                    lease_epoch=context.lease_epoch,
                )
                raise SkillExecutionError(
                    ErrorCode.PROVIDER_UNKNOWN_OUTCOME,
                    "fallback provider outcome is unknown; explicit retry or approval is required",
                    recoverable=True,
                ) from fallback_error
        except SkillExecutionError:
            await self._complete_provider_call(
                call_id,
                outcome="unavailable",
                usage={},
                lease_epoch=context.lease_epoch,
            )
            raise
        except Exception as exc:  # an opaque upstream boundary is not safe to retry automatically
            await self._unknown_provider_call(call_id, message=str(exc), lease_epoch=context.lease_epoch)
            raise SkillExecutionError(
                ErrorCode.PROVIDER_UNKNOWN_OUTCOME,
                "provider outcome is unknown; explicit retry or approval is required",
                recoverable=True,
            ) from exc

    def _assert_provider_available(self, provider_name: str) -> None:
        decision = self._provider_policy.can_call(provider_name)
        if decision == "RATE_LIMITED":
            raise ProviderStreamUnavailable("provider rate limit is active")
        if decision == "CIRCUIT_OPEN":
            raise ProviderStreamUnavailable("provider circuit breaker is open")

    async def _retrieve(
        self,
        definition: SkillDefinition,
        input_value: BaseModel,
        context: ExecutionContext,
    ) -> list[dict[str, Any]]:
        domain = str(getattr(input_value, "domain", None) or definition.required_domains[0])
        query = str(getattr(input_value, "query", None) or definition.name)
        filters = getattr(input_value, "filters", None)
        try:
            if context.mode == ExecutionMode.FIXTURE:
                raw_items = default_evidence_fixtures(domain)
            elif self._retriever is not None:
                raw_items = await self._retriever.retrieve(
                    query,
                    domain=domain,
                    top_k=max(definition.evidence_floor, 3),
                    filters=filters,
                )
            else:
                raw_items = await retrieve(
                    query,
                    domain=domain,
                    top_k=max(definition.evidence_floor, 3),
                    filter=filters,
                )
        except ExecutionCancelled:
            raise
        except Exception as exc:
            raise SkillExecutionError(ErrorCode.PROVIDER_UNAVAILABLE, "RAG retrieval is unavailable") from exc
        normalised = [self._normalise_evidence(item, domain) for item in raw_items]
        if context.mode == ExecutionMode.REAL:
            # A real snapshot must point at an actual retrieved knowledge
            # chunk. Generating an ID here would manufacture provenance and
            # make a later audit indistinguishable from genuine evidence.
            if any(not item["chunk_id"] for item in normalised):
                raise SkillExecutionError(
                    ErrorCode.INSUFFICIENT_EVIDENCE,
                    "real retrieved evidence is missing a durable chunk identity",
                )
        return normalised

    @staticmethod
    def _normalise_evidence(item: Any, domain: str) -> dict[str, Any]:
        if isinstance(item, dict):
            raw = dict(item)
        elif hasattr(item, "model_dump"):
            raw = item.model_dump(mode="json")
        else:
            raw = {
                "chunk_id": getattr(item, "chunk_id", ""),
                "document_id": getattr(item, "document_id", None),
                "chunk_text": getattr(item, "chunk_text", getattr(item, "excerpt", "")),
                "source": getattr(item, "source", None),
                "metadata": getattr(item, "metadata", {}),
            }
        excerpt = str(raw.get("excerpt") or raw.get("chunk_text") or "")[:1_000]
        return {
            "chunk_id": str(raw.get("chunk_id") or raw.get("id") or ""),
            "document_id": str(raw["document_id"]) if raw.get("document_id") else None,
            "excerpt": excerpt,
            "source": raw.get("source") or (raw.get("metadata") or {}).get("source_url"),
            "citation": raw.get("citation") or raw.get("source"),
            "rights": (raw.get("metadata") or {}).get("rights_note"),
            "score": raw.get("score", 0.0),
            "metadata": dict(raw.get("metadata") or {}),
            "domain": str(raw.get("domain") or domain),
        }

    @staticmethod
    def _strict_parse_category(exc: BaseException) -> str:
        if isinstance(exc, json.JSONDecodeError):
            return "invalid_json"
        if isinstance(exc, ValidationError):
            return "schema_validation"
        if isinstance(exc, TypeError):
            return "non_object_json"
        return "invalid_payload"

    @staticmethod
    def _validation_error_summary(exc: BaseException) -> list[dict[str, str]]:
        """Keep field-level schema diagnostics without retaining model output."""
        if not isinstance(exc, ValidationError):
            return []
        return [
            {
                "location": ".".join(str(part) for part in error.get("loc", ())),
                "type": str(error.get("type", "validation_error")),
            }
            for error in exc.errors(include_url=False)
        ]

    @staticmethod
    def _assert_safe_text(text: str, *, boundary: str) -> None:
        """Apply the same fail-closed policy before text reaches a prompt."""
        review = review_input(text)
        if not review.allowed:
            raise SkillExecutionError(ErrorCode.GUARDRAIL_BLOCKED, f"{boundary} guardrail rejected request")
        injection = detect_prompt_injection(review.normalized_text)
        if injection.detected:
            raise SkillExecutionError(ErrorCode.GUARDRAIL_BLOCKED, f"{boundary} guardrail detected prompt injection")

    @staticmethod
    def _evidence_event_item(record: dict[str, Any], snapshot: EvidenceRef) -> dict[str, Any]:
        """Build the public evidence card without exposing a prompt or model output."""
        metadata = dict(record.get("metadata") or {})
        source_url = record.get("source") or metadata.get("source_url") or metadata.get("url")
        score = record.get("score", 0.0)
        try:
            score_value = float(score)
        except (TypeError, ValueError):
            score_value = 0.0
        return {
            "evidence_snapshot_id": str(snapshot.evidence_snapshot_id),
            "chunk_id": str(snapshot.chunk_id),
            "document_id": str(snapshot.document_id or ""),
            "chunk_text": str(record.get("excerpt") or ""),
            "excerpt": str(record.get("excerpt") or ""),
            "score": score_value,
            "platform": str(metadata.get("platform") or "manual"),
            "rights_note": str(snapshot.rights or metadata.get("rights_note") or ""),
            "source_url": str(source_url) if source_url else None,
            "title": str(metadata.get("title")) if metadata.get("title") else None,
            "author": str(metadata.get("author")) if metadata.get("author") else None,
            "license": str(metadata.get("license")) if metadata.get("license") else None,
            "collection_mode": str(metadata.get("collection_mode")) if metadata.get("collection_mode") else None,
            "asset_type": str(metadata.get("asset_type")) if metadata.get("asset_type") else None,
            "page_no": metadata.get("page_no"),
            "reliability": metadata.get("reliability"),
        }

    async def _snapshot_evidence(
        self,
        items: list[dict[str, Any]],
        definition: SkillDefinition,
        context: ExecutionContext,
    ) -> list[EvidenceRef]:
        records = [
            {
                "workflow_run_id": context.workflow_run_id,
                "step_attempt_id": context.step_attempt_id,
                "agent_run_id": context.agent_run_id,
                "chunk_id": item["chunk_id"],
                "document_id": item["document_id"],
                "content_digest": hashlib.sha256(item["excerpt"].encode("utf-8")).hexdigest(),
                "citation": item["citation"],
                "source": item["source"],
                "rights": item["rights"],
                "skill_definition_digest": definition.definition_digest,
            }
            for item in items
        ]
        stored: list[Any] | None = None
        if self._evidence_snapshot_store is not None:
            stored = await self._invoke_port(
                self._evidence_snapshot_store,
                ("save_many", "create_many", "create_snapshots"),
                records=records,
                snapshots=records,
            )
        if stored is None:
            if context.mode == ExecutionMode.REAL:
                raise SkillExecutionError(ErrorCode.AGENT_RUN_PERSIST_FAILED, "real evidence snapshots could not be persisted")
            stored = [{**record, "id": str(uuid4())} for record in records]
        result: list[EvidenceRef] = []
        for record, saved in zip(records, stored, strict=False):
            data = saved if isinstance(saved, dict) else {"id": getattr(saved, "id", None)}
            result.append(
                EvidenceRef(
                    evidence_snapshot_id=data.get("id") or data.get("evidence_snapshot_id") or uuid4(),
                    chunk_id=record["chunk_id"],
                    document_id=record["document_id"],
                    content_digest=record["content_digest"],
                    citation=record["citation"],
                    source=record["source"],
                    rights=record["rights"],
                )
            )
        return result

    async def _start_provider_call(
        self,
        *,
        definition: SkillDefinition,
        context: ExecutionContext,
        provider: BaseLLMProvider,
        request_digest: str,
        stream_attempt: int = 1,
    ) -> str:
        payload = {
            "workflow_run_id": context.workflow_run_id,
            "step_attempt_id": context.step_attempt_id,
            "agent_run_id": context.agent_run_id,
            # A retried WorkflowStepAttempt represents a new, explicitly
            # authorised provider attempt. It must never reuse the journal
            # identity of a previous unknown external call.
            "attempt": int(context.extras.get("provider_attempt", 1)),
            "stream_attempt": stream_attempt,
            "provider": getattr(provider, "provider_name", "unknown"),
            "model": getattr(provider, "model_name", "unknown"),
            "provider_policy_version": context.provider_selection.policy_version,
            "request_digest": request_digest,
            "status": "started",
            "lease_epoch": context.lease_epoch,
        }
        if self._provider_call_store is not None:
            value = await self._invoke_port(
                self._provider_call_store,
                ("start", "create_started", "create"),
                **payload,
            )
            if value is not None:
                return str(value.get("id") if isinstance(value, dict) else getattr(value, "id", value))
        if context.mode == ExecutionMode.REAL:
            raise SkillExecutionError(ErrorCode.AGENT_RUN_PERSIST_FAILED, "real provider call journal could not be persisted")
        return str(uuid4())

    async def _complete_provider_call(
        self,
        provider_call_id: str,
        *,
        outcome: str,
        usage: dict[str, int],
        response_ref: dict[str, Any] | None = None,
        lease_epoch: int | None = None,
    ) -> None:
        if self._provider_call_store is None:
            return
        await self._invoke_port(
            self._provider_call_store,
            ("complete", "mark_completed"),
            provider_call_id=provider_call_id,
            call_id=provider_call_id,
            outcome=outcome,
            usage=usage,
            response_ref=response_ref,
            lease_epoch=lease_epoch,
        )

    async def _unknown_provider_call(
        self,
        provider_call_id: str,
        *,
        message: str,
        lease_epoch: int | None = None,
    ) -> None:
        if self._provider_call_store is None:
            return
        await self._invoke_port(
            self._provider_call_store,
            ("mark_unknown", "unknown"),
            provider_call_id=provider_call_id,
            call_id=provider_call_id,
            error_message=message[:400],
            lease_epoch=lease_epoch,
        )

    async def _record_visible_tokens(
        self,
        provider_call_id: str,
        *,
        lease_epoch: int,
    ) -> None:
        if self._provider_call_store is None:
            return
        await self._invoke_port(
            self._provider_call_store,
            ("add_visible_tokens",),
            provider_call_id=provider_call_id,
            count=1,
            lease_epoch=lease_epoch,
        )

    async def _call_provider(
        self,
        provider: BaseLLMProvider,
        prompt: str,
        definition: SkillDefinition,
        context: ExecutionContext,
        provider_call_id: str,
        *,
        stream_attempt: int = 1,
        replace_draft: bool = False,
        replaces_stream_attempt: int | None = None,
    ) -> tuple[str, dict[str, int]]:
        messages = [
            LLMMessage(
                role="system",
                content=(
                    "Return exactly one valid JSON object. The first non-whitespace character must be { "
                    "and the last must be }. Do not include reasoning, analysis tags, Markdown fences, "
                    "or any text outside the JSON object. Obey the supplied JSON schema exactly."
                ),
            ),
            LLMMessage(role="user", content=prompt),
        ]
        await context.require_not_cancelled()
        await self._emit(context, "progress", {"node_status": "generating", "percentage": 45, "provider_call_id": provider_call_id})
        if context.stream:
            parts: list[str] = []
            finish_reason: str | None = None
            stream = self._provider_stream(
                provider,
                messages,
                max_tokens=int(context.extras.get("max_tokens", 800)),
            )
            try:
                async for chunk in stream:
                    await context.require_not_cancelled()
                    if chunk.content:
                        parts.append(chunk.content)
                        await self._record_visible_tokens(
                            provider_call_id,
                            lease_epoch=context.lease_epoch,
                        )
                        await self._emit(
                            context,
                            "token",
                            {
                                "content": chunk.content,
                                "provider_call_id": provider_call_id,
                                "stream_attempt": stream_attempt,
                                "token_index": chunk.index,
                                "actual_provider": getattr(provider, "provider_name", None),
                                "actual_model": getattr(provider, "model_name", None),
                                "replace_draft": replace_draft and len(parts) == 1,
                                "replaces_stream_attempt": replaces_stream_attempt,
                            },
                        )
                    if chunk.finish_reason:
                        finish_reason = chunk.finish_reason
            except ExecutionCancelled:
                raise
            except Exception as exc:
                raise ProviderStreamUnavailable(
                    "provider stream interrupted",
                    visible_tokens=len(parts),
                ) from exc
            raw = "".join(parts)
            usage = {
                "prompt_tokens": provider.estimate_tokens(prompt),
                "completion_tokens": provider.estimate_tokens(raw),
                "total_tokens": provider.estimate_tokens(prompt) + provider.estimate_tokens(raw),
            }
            if not raw:
                raise ProviderStreamUnavailable(
                    f"provider stream ended without final content ({finish_reason or 'unknown'})",
                    visible_tokens=0,
                )
            return raw, usage
        try:
            response = await self._provider_generate(
                provider,
                messages,
                max_tokens=int(context.extras.get("max_tokens", 800)),
            )
        except ExecutionCancelled:
            raise
        except Exception as exc:
            raise ProviderStreamUnavailable("provider request failed", visible_tokens=0) from exc
        return response.content, {
            "prompt_tokens": int(response.usage.prompt_tokens or 0),
            "completion_tokens": int(response.usage.completion_tokens or 0),
            "total_tokens": int(response.usage.total_tokens or 0),
        }

    @staticmethod
    def _default_provider(context: ExecutionContext) -> BaseLLMProvider:
        requested = context.provider_selection.requested_provider
        return get_llm_provider(requested)

    @staticmethod
    def _default_fallback_provider(provider_name: str, _context: ExecutionContext) -> BaseLLMProvider:
        return get_llm_provider(provider_name)

    @staticmethod
    def _provider_stream(
        provider: BaseLLMProvider,
        messages: list[LLMMessage],
        *,
        max_tokens: int,
    ) -> Any:
        """Prefer JSON mode when a provider supports it without adding a second API."""
        try:
            return provider.stream_generate(
                messages,
                temperature=0.2,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except TypeError:
            return provider.stream_generate(messages, temperature=0.2, max_tokens=max_tokens)

    @staticmethod
    async def _provider_generate(
        provider: BaseLLMProvider,
        messages: list[LLMMessage],
        *,
        max_tokens: int,
    ) -> Any:
        try:
            return await provider.generate(
                messages,
                temperature=0.2,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
        except TypeError:
            return await provider.generate(messages, temperature=0.2, max_tokens=max_tokens)

    async def _emit(self, context: ExecutionContext, event_type: str, payload: dict[str, Any]) -> None:
        await context.emit(
            event_type,
            {
                "step_attempt_id": str(context.step_attempt_id),
                "agent_run_id": str(context.agent_run_id),
                **payload,
            },
        )

    @staticmethod
    async def _invoke_port(port: Any, names: tuple[str, ...], **kwargs: Any) -> Any:
        import inspect

        for name in names:
            method = getattr(port, name, None)
            if method is None:
                continue
            signature = inspect.signature(method)
            accepted = {
                key: value
                for key, value in kwargs.items()
                if key in signature.parameters or any(
                    parameter.kind == parameter.VAR_KEYWORD
                    for parameter in signature.parameters.values()
                )
            }
            value = method(**accepted)
            return await value if inspect.isawaitable(value) else value
        return None


__all__ = ["SkillExecutionError", "SkillExecutor"]
