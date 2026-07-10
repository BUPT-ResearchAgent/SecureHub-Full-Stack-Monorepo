# Status: real

"""Harness base class.

A Harness wraps the canonical skill execution chain:

    validate -> rag.retrieve -> evidence_floor -> compose prompt -> LLM ->
    parse output -> safety review -> quality_check -> log_run

It is the single entry point used by:
- agent skill classes via ``BaseSkill.run`` (through ``run_skill``)
- the LangGraph workflow nodes that orchestrate multi-agent flows
- API endpoints that need a one-shot call

The harness intentionally accepts mock LLM / RAG implementations, so the rest of
SecureHub keeps running in fixture mode when no external API key is configured.
"""

from __future__ import annotations

import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ValidationError

from app.runtime.harness.context import HarnessContext
from app.llm.embeddings.errors import EmbeddingError
from app.runtime.harness.errors import (
    AgentRunPersistenceFailed,
    CancellationRequested,
    HarnessError,
    InsufficientEvidence,
    LLMOutputInvalid,
    QualityCheckFailed,
    QualityRejected,
    SafetyBlocked,
    ToolUnavailable,
)
from app.runtime.harness.fixtures import default_evidence_fixtures, default_llm_output
from app.runtime.harness.types import (
    BaseSkill,
    EvidenceCard,
    HarnessTelemetry,
    RunStatus,
    TokenUsage,
)

InputModel = TypeVar("InputModel", bound=BaseModel)
OutputModel = TypeVar("OutputModel", bound=BaseModel)


def _compact_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Build a deterministic, valid schema hint without string truncation.

    Skill output models are intentionally small, but their Pydantic schema can
    contain titles, descriptions and definitions that are unnecessary in a
    provider prompt.  This projection keeps types, properties, required fields
    and collection constraints while resolving local ``$ref`` values.  The
    result remains a JSON object at every depth, so the prompt cannot contain a
    schema cut in the middle of a JSON token.
    """
    raw_schema = model.model_json_schema()
    definitions = raw_schema.get("$defs", {}) if isinstance(raw_schema, dict) else {}

    def compact(node: Any, active_refs: tuple[str, ...] = ()) -> dict[str, Any]:
        if not isinstance(node, dict):
            return {}
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            ref_name = ref.rsplit("/", 1)[-1]
            if ref_name in active_refs:
                return {"type": "object"}
            return compact(definitions.get(ref_name, {}), (*active_refs, ref_name))

        result: dict[str, Any] = {}
        for key in (
            "type",
            "format",
            "enum",
            "const",
            "minimum",
            "maximum",
            "exclusiveMinimum",
            "exclusiveMaximum",
            "minLength",
            "maxLength",
            "minItems",
            "maxItems",
            "pattern",
        ):
            if key in node:
                result[key] = node[key]

        properties = node.get("properties")
        if isinstance(properties, dict):
            result["type"] = result.get("type", "object")
            result["properties"] = {
                name: compact(properties[name], active_refs)
                for name in sorted(properties)
            }
        required = node.get("required")
        if isinstance(required, list) and required:
            result["required"] = sorted(str(name) for name in required)

        if "additionalProperties" in node:
            additional = node["additionalProperties"]
            result["additionalProperties"] = (
                compact(additional, active_refs) if isinstance(additional, dict) else bool(additional)
            )
        if "items" in node:
            result["items"] = compact(node["items"], active_refs)

        for key in ("anyOf", "oneOf", "allOf"):
            variants = node.get(key)
            if isinstance(variants, list):
                result[key] = [compact(item, active_refs) for item in variants]
        return result

    return compact(raw_schema)


def _summarize(obj: Any, max_chars: int = 800) -> dict[str, Any]:
    """Best-effort JSON-safe summary suitable for agent_runs storage."""
    if isinstance(obj, BaseModel):
        payload = obj.model_dump(mode="json")
    elif isinstance(obj, dict):
        payload = obj
    else:
        payload = {"value": str(obj)}
    text = json.dumps(payload, ensure_ascii=False)
    if len(text) > max_chars:
        return {"truncated": True, "preview": text[:max_chars]}
    return payload


def _context_run_id(ctx: HarnessContext) -> UUID:
    """Use a workflow-supplied child id when strict persistence requires it."""
    raw_run_id = ctx.extras.get("agent_run_id")
    if isinstance(raw_run_id, UUID):
        return raw_run_id
    if raw_run_id is not None:
        try:
            return UUID(str(raw_run_id))
        except (TypeError, ValueError):
            pass
    return uuid4()


@dataclass
class SkillSpec(Generic[InputModel, OutputModel]):
    """Static skill description consumed by the harness.

    Keeping this as a plain dataclass (rather than a Pydantic model) makes it
    cheap to attach callables for ``rag`` / ``llm`` / ``quality`` injection.
    """

    name: str
    agent_name: str
    input_model: type[InputModel]
    output_model: type[OutputModel]
    prompt_template: str
    applicable_domains: list[str] = field(default_factory=lambda: ["course_websec"])
    required_tools: list[str] = field(default_factory=lambda: ["rag.retrieve", "llm.xfyun"])
    evidence_floor: int = 3
    require_evidence: bool = True
    quality_check: bool = True
    log_run: bool = True
    timeout_sec: float = 60.0
    fallback: str = "mock"  # mock | error
    strict_output: bool = False
    strict_log_run: bool = False
    strict_quality_check: bool = False
    capability_dim: str = "doc"

    # Optional pluggable hooks (default to in-process implementations resolved
    # at run time by the Harness)
    rag_retrieve: Callable[..., Awaitable[list[EvidenceCard]]] | None = None
    llm_complete: Callable[..., Awaitable[dict[str, Any]]] | None = None
    quality_check_fn: Callable[..., Awaitable[dict[str, Any]]] | None = None

    agent_id: UUID | str | None = None
    skill_id: UUID | str | None = None


# --- default tool resolvers ---------------------------------------------


async def _default_rag_retrieve(
    query: str,
    *,
    domain: str,
    top_k: int,
    filters: dict[str, Any] | None = None,
) -> list[EvidenceCard]:
    """Fallback RAG retriever: dispatches to app.rag.retriever and degrades to fixtures.

    The real retriever lives in ``app.rag.retriever`` and is wired up there to
    pgvector once chunks exist. When the database is empty (fresh deploy) the
    retriever returns no rows; we then degrade to canned fixtures so the demo
    path stays runnable.
    """
    from app.rag.retriever import retrieve  # late import to avoid cycles

    try:
        hits = await retrieve(query, domain=domain, top_k=top_k, filter=filters)
    except EmbeddingError:
        raise
    except Exception:
        # Real retriever failed before reaching the embedding provider.
        hits = []
    if hits:
        return [
            EvidenceCard(
                chunk_id=str(hit.chunk_id),
                document_id=str(hit.document_id) if hit.document_id else None,
                domain=hit.domain,
                source=hit.source,
                excerpt=hit.chunk_text[:500],
                reliability=hit.reliability,
                score=hit.score,
                metadata=hit.metadata,
            )
            for hit in hits
        ]
    return [EvidenceCard(**hit) for hit in default_evidence_fixtures(domain)]


async def _default_llm_complete(
    prompt: str,
    *,
    skill_name: str,
    stream: bool = False,
    emit: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
) -> dict[str, Any]:
    """Fallback LLM caller.

    Routes through ``app.llm.xfyun.xfyun_chat`` when credentials are configured,
    otherwise returns a canned skill-specific fixture so the demo path is
    deterministic without external API keys.
    """
    try:
        from app.core.config import get_settings
        from app.llm.xfyun import xfyun_chat

        settings = get_settings()
        if settings.XFYUN_API_KEY:
            raw = await xfyun_chat(prompt, stream=stream)
            try:
                return json.loads(raw)
            except (TypeError, ValueError):
                return {"content": raw, "quality_score": 0.7}
    except (NotImplementedError, Exception):  # pragma: no cover - real provider path
        pass

    fixture = default_llm_output(skill_name)
    if stream and emit is not None:
        await emit(
            {
                "event": "token",
                "content": fixture.get("content", ""),
            }
        )
    return fixture


async def _default_quality_check(
    *,
    skill_name: str,
    input_payload: dict[str, Any],
    output_payload: dict[str, Any],
    evidence: list[EvidenceCard],
) -> dict[str, Any]:
    """Lightweight rule-based quality check used when outcome_evaluator is offline.

    Rules:
    - evidence list must be non-empty (already guaranteed by harness)
    - output_payload must declare a ``quality_score`` or one is computed
    - if ``QualityCheck`` itself is the skill, we trust its own output
    """
    if skill_name == "QualityCheck":
        return {"accept": True, "quality_score": output_payload.get("quality_score", 0.9)}
    score = output_payload.get("quality_score")
    if score is None:
        # heuristic: ratio of evidence_chunk_ids referenced vs available
        score = 0.7 if len(evidence) >= 3 else 0.5
    return {"accept": score >= 0.5, "quality_score": float(score)}


# --- harness -------------------------------------------------------------


class Harness:
    """Stateless harness that executes a skill spec.

    Instances are cheap to construct; tests typically build a fresh one per skill
    while production code reuses a module-level singleton.
    """

    def __init__(
        self,
        *,
        rag_retrieve: Callable[..., Awaitable[list[EvidenceCard]]] | None = None,
        llm_complete: Callable[..., Awaitable[dict[str, Any]]] | None = None,
        quality_check_fn: Callable[..., Awaitable[dict[str, Any]]] | None = None,
        retriever: Any | None = None,
        llm: Any | None = None,
        quality_checker: Any | None = None,
        storage_service: Any | None = None,
    ) -> None:
        self._rag_retrieve = rag_retrieve or _default_rag_retrieve
        self._llm_complete = llm_complete or _default_llm_complete
        self._quality_check = quality_check_fn or _default_quality_check
        self.retriever = retriever
        self.llm = llm
        self.quality_checker = quality_checker
        self.storage_service = storage_service

    async def run(
        self,
        spec: SkillSpec[InputModel, OutputModel] | BaseSkill,
        inp: InputModel | dict[str, Any],
        ctx: HarnessContext,
    ) -> OutputModel | BaseModel:
        if not isinstance(spec, SkillSpec):
            return await self._run_legacy(spec, inp, ctx)

        if not isinstance(inp, spec.input_model):
            try:
                inp = spec.input_model.model_validate(
                    inp.model_dump() if isinstance(inp, BaseModel) else inp
                )
            except ValidationError as exc:
                raise HarnessError(f"input validation failed: {exc}") from exc

        run_id = _context_run_id(ctx)
        start = time.perf_counter()
        telemetry = HarnessTelemetry(agent_id=spec.agent_id, skill_id=spec.skill_id)
        await self._emit_progress(ctx, spec, status="started", percentage=5)

        # === 1. retrieve evidence ===
        domain = getattr(inp, "domain", spec.applicable_domains[0] if spec.applicable_domains else "course_websec")
        query = getattr(inp, "query", None) or getattr(inp, "topic", None) or spec.name
        try:
            evidence = await (spec.rag_retrieve or self._rag_retrieve)(
                query,
                domain=domain,
                top_k=max(spec.evidence_floor, getattr(ctx.config, "RETRIEVAL_TOP_K", 8)),
                filters=getattr(inp, "filters", None),
            )
        except Exception as exc:  # pragma: no cover - safety net
            if isinstance(exc, CancellationRequested):
                raise
            code = getattr(exc, "code", "tool_unavailable")
            await self._fail(ctx, spec, run_id, telemetry, str(code), str(exc))
            if isinstance(exc, HarnessError):
                raise
            raise ToolUnavailable(f"RAG retrieval failed: {exc}") from exc

        if spec.require_evidence and len(evidence) < spec.evidence_floor:
            await self._fail(
                ctx,
                spec,
                run_id,
                telemetry,
                "insufficient_evidence",
                f"need {spec.evidence_floor}, got {len(evidence)}",
            )
            raise InsufficientEvidence(
                f"skill {spec.name} requires {spec.evidence_floor} evidence chunks; got {len(evidence)}"
            )

        await self._emit_evidence(ctx, evidence)
        ctx.last_evidence = evidence
        telemetry.evidence_count = len(evidence)

        # === 2. compose prompt ===
        prompt = self._compose_prompt(spec, inp, ctx, evidence)

        # === 3. LLM call ===
        await self._emit_progress(ctx, spec, status="generating", percentage=40)
        try:
            llm_output = await (spec.llm_complete or self._llm_complete)(
                prompt,
                skill_name=spec.name,
                stream=ctx.stream,
                emit=ctx.emit,
            )
        except Exception as exc:
            if isinstance(exc, CancellationRequested):
                raise
            if spec.fallback == "mock":
                llm_output = default_llm_output(spec.name)
            else:
                code = getattr(exc, "code", "tool_unavailable")
                await self._fail(ctx, spec, run_id, telemetry, str(code), str(exc))
                if isinstance(exc, HarnessError):
                    raise
                raise ToolUnavailable(f"LLM call failed: {exc}") from exc

        # === 4. parse output ===
        evidence_ids = [card.chunk_id for card in evidence]
        try:
            output = self._parse_output(spec, llm_output, evidence_ids)
        except (TypeError, ValueError, ValidationError) as exc:
            if spec.strict_output:
                await self._fail(ctx, spec, run_id, telemetry, "LLM_OUTPUT_INVALID", str(exc))
                raise LLMOutputInvalid("strict LLM output did not match the skill schema") from exc
            # Fallback: build the output by filling in known fields + defaults
            output = self._coerce_output(spec, llm_output, evidence_ids)
            if output is None:
                await self._fail(ctx, spec, run_id, telemetry, "output_parse_failed", str(exc))
                raise HarnessError(f"output parse failed: {exc}") from exc

        # === 5. safety review ===
        try:
            output = self._safety_review(output)
        except SafetyBlocked as exc:
            await self._fail(ctx, spec, run_id, telemetry, "safety_blocked", str(exc))
            raise

        # === 6. quality check ===
        quality_result: dict[str, Any] = {"accept": True, "quality_score": getattr(output, "quality_score", None) or 0.0}
        if spec.quality_check:
            await self._emit_progress(ctx, spec, status="quality_check", percentage=80)
            try:
                quality_result = await (spec.quality_check_fn or self._quality_check)(
                    skill_name=spec.name,
                    input_payload=inp.model_dump(),
                    output_payload=output.model_dump(),
                    evidence=evidence,
                )
            except Exception as exc:  # noqa: BLE001 - fixture compatibility path
                if spec.strict_quality_check:
                    code = getattr(exc, "code", "tool_unavailable")
                    await self._fail(ctx, spec, run_id, telemetry, str(code), str(exc))
                    if isinstance(exc, HarnessError):
                        raise
                    raise ToolUnavailable(f"quality check failed: {exc}") from exc
                quality_result = {"accept": True, "quality_score": 0.6, "error": str(exc)}
            if not quality_result.get("accept", True):
                await self._fail(
                    ctx,
                    spec,
                    run_id,
                    telemetry,
                    "quality_check_failed",
                    quality_result.get("reason", "rejected"),
                )
                raise QualityCheckFailed(quality_result.get("reason", "quality check rejected"))

        # Propagate quality_score into the typed output if the model exposes the field
        new_quality = float(quality_result.get("quality_score") or 0.0)
        if hasattr(output, "quality_score"):
            try:
                setattr(output, "quality_score", new_quality)
            except Exception:  # noqa: BLE001 - immutable model
                pass

        # === 7. log_run ===
        telemetry.duration_ms = int((time.perf_counter() - start) * 1000)
        telemetry.quality_score = new_quality
        telemetry.token_usage = TokenUsage(
            prompt=int(llm_output.get("prompt_tokens", 0)) if isinstance(llm_output, dict) else 0,
            completion=int(llm_output.get("completion_tokens", 0)) if isinstance(llm_output, dict) else 0,
            total=int(llm_output.get("total_tokens", 0)) if isinstance(llm_output, dict) else 0,
            model=str(llm_output.get("model", "fixture")) if isinstance(llm_output, dict) else "fixture",
        )
        telemetry.status = RunStatus.success

        if spec.log_run:
            try:
                await ctx.log_run(
                    run_id=run_id,
                    workflow_name=ctx.workflow_name,
                    user_id=ctx.user_id,
                    agent_id=spec.agent_id,
                    skill_id=spec.skill_id,
                    parent_run_id=ctx.parent_run_id,
                    input_summary=_summarize(inp),
                    output_summary=_summarize(output),
                    evidence_chunk_ids=evidence_ids,
                    quality_score=new_quality,
                    status=telemetry.status.value,
                    duration_ms=telemetry.duration_ms,
                    token_usage=telemetry.token_usage.model_dump(),
                )
            except Exception as exc:  # noqa: BLE001 - fixture compatibility path
                if spec.strict_log_run:
                    await self._emit_persistence_error(ctx)
                    raise AgentRunPersistenceFailed(
                        "strict agent_runs persistence could not be verified"
                    ) from exc

        await self._emit_done(ctx, spec, run_id, new_quality)
        return output

    async def _run_legacy(
        self,
        skill: BaseSkill,
        raw_input: BaseModel | dict[str, Any],
        ctx: HarnessContext,
    ) -> BaseModel:
        """Run the dev-era BaseSkill contract on top of the PR 24 harness shell."""
        contract = skill.contract
        run_id = uuid4()
        start = time.perf_counter()

        await ctx.emit("progress", {"node_name": "validate", "status": "running"})
        try:
            inp = contract.input_schema.model_validate(
                raw_input.model_dump() if isinstance(raw_input, BaseModel) else raw_input
            )
        except ValidationError as exc:
            raise HarnessError(f"input validation failed: {exc}") from exc

        query = getattr(inp, "query", None) or getattr(inp, "topic", None) or skill.name
        domain = (
            getattr(inp, "domain", None)
            or (contract.required_domains[0] if contract.required_domains else "course_websec")
        )
        floor = max(
            int(getattr(ctx.config, "min_evidence", 0) or 0),
            int(getattr(ctx.config, "MIN_EVIDENCE", 0) or 0),
            int(contract.evidence_floor or 0),
        )
        top_k = max(floor, int(getattr(ctx.config, "RETRIEVAL_TOP_K", 8) or 8))

        await ctx.emit("progress", {"node_name": "retrieve", "status": "running"})
        if self.retriever is not None:
            evidence = await self.retriever.retrieve(query, domain=domain, top_k=top_k, filters=None)
        else:
            evidence = await self._rag_retrieve(query, domain=domain, top_k=top_k, filters=None)

        if len(evidence) < floor:
            raise InsufficientEvidence(
                f"skill {skill.name} requires {floor} evidence chunks; got {len(evidence)}"
            )

        evidence_ids = [str(getattr(card, "chunk_id", "")) for card in evidence]
        ctx.evidence_chunk_ids = evidence_ids
        ctx.last_evidence = [
            card
            if isinstance(card, EvidenceCard)
            else EvidenceCard(
                chunk_id=str(getattr(card, "chunk_id", "")),
                document_id=(
                    str(getattr(card, "document_id", ""))
                    if getattr(card, "document_id", None)
                    else None
                ),
                domain=domain,
                source=getattr(card, "source_url", None) or getattr(card, "source", None),
                excerpt=str(getattr(card, "excerpt", "")),
                score=float(getattr(card, "score", 0.0) or 0.0),
                metadata=dict(getattr(card, "metadata", {}) or {}),
            )
            for card in evidence
        ]

        from app.schemas.evidence import evidence_card_to_dto

        await ctx.emit(
            "evidence",
            {
                "chunks": [
                    evidence_card_to_dto(card).model_dump(mode="json")
                    for card in ctx.last_evidence
                ],
            },
        )

        ctx.llm = self.llm or ctx.llm
        ctx.quality_checker = self.quality_checker or ctx.quality_checker
        ctx.storage_service = self.storage_service or ctx.storage_service

        await ctx.emit("progress", {"node_name": "compose", "status": "running"})
        output = await skill.run(inp, ctx)

        quality_score = float(getattr(output, "quality_score", 0.0) or 0.0)
        if contract.quality_check:
            await ctx.emit("progress", {"node_name": "quality_check", "status": "running"})
            checker = ctx.quality_checker
            if checker is not None and hasattr(checker, "check"):
                result = await checker.check(
                    skill_name=skill.name,
                    input_payload=inp.model_dump(),
                    output_payload=output.model_dump()
                    if isinstance(output, BaseModel)
                    else {"value": str(output)},
                    evidence=ctx.last_evidence,
                )
                if not result.get("accept", True):
                    raise QualityRejected(result.get("reason", "quality check rejected"))
                quality_score = float(result.get("quality_score", quality_score) or quality_score)
                if hasattr(output, "quality_score"):
                    try:
                        setattr(output, "quality_score", quality_score)
                    except Exception:
                        pass

        duration_ms = int((time.perf_counter() - start) * 1000)
        if contract.log_run:
            await ctx.log_run(
                run_id=run_id,
                workflow_name=ctx.workflow_name,
                user_id=ctx.user_id,
                agent_id=getattr(skill, "agent_name", None),
                skill_id=getattr(skill, "name", None),
                parent_run_id=ctx.parent_run_id,
                input_summary=_summarize(inp),
                output_summary=_summarize(output),
                evidence_chunk_ids=evidence_ids,
                quality_score=quality_score,
                status=RunStatus.success.value,
                duration_ms=duration_ms,
                token_usage={},
            )

        await ctx.emit(
            "trace",
            {
                "agent_name": skill.agent_name,
                "skill_name": skill.name,
                "status": "success",
                "run_id": str(run_id),
                "quality_score": quality_score,
            },
        )
        await ctx.emit("done", {"run_id": str(run_id), "quality_score": quality_score})
        return output

    # === helpers ===

    def _compose_prompt(
        self,
        spec: SkillSpec[InputModel, OutputModel],
        inp: InputModel,
        ctx: HarnessContext,
        evidence: list[EvidenceCard],
    ) -> str:
        evidence_text = "\n\n".join(
            f"[{i + 1}] {card.source or 'unknown'}\n{card.excerpt}"
            for i, card in enumerate(evidence)
        )
        task_instruction = getattr(inp, "query", "") or getattr(inp, "topic", "") or spec.name
        input_payload = inp.model_dump(mode="json")
        artifact_payload = input_payload.get("artifact")
        artifact_text = json.dumps(
            artifact_payload if artifact_payload is not None else {},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        try:
            return spec.prompt_template.format(
                evidence_text=evidence_text,
                persona_text=ctx.persona_summary or "(persona not provided)",
                task_instruction=task_instruction,
                artifact_text=artifact_text,
                input_payload_text=json.dumps(
                    input_payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                output_schema_hint=json.dumps(
                    _compact_json_schema(spec.output_model),
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
            )
        except KeyError:
            # The skill template uses an unknown placeholder; fall back to a generic envelope
            return (
                f"You are agent {spec.agent_name} running skill {spec.name}.\n"
                f"Evidence:\n{evidence_text}\n\nPersona:\n{ctx.persona_summary}\n\n"
                f"Task: {task_instruction}\n"
            )

    def _parse_output(
        self,
        spec: SkillSpec[InputModel, OutputModel],
        llm_output: dict[str, Any],
        evidence_ids: list[str],
    ) -> OutputModel:
        merged = dict(llm_output)
        merged["evidence_chunk_ids"] = evidence_ids
        merged.setdefault("content", llm_output.get("content", ""))
        return spec.output_model.model_validate(merged)

    def _coerce_output(
        self,
        spec: SkillSpec[InputModel, OutputModel],
        llm_output: dict[str, Any],
        evidence_ids: list[str],
    ) -> OutputModel | None:
        """Best-effort second-chance parse using only fields the model knows about."""
        try:
            allowed: dict[str, Any] = {}
            schema = spec.output_model.model_fields
            for name in schema:
                if name in llm_output:
                    allowed[name] = llm_output[name]
            allowed["evidence_chunk_ids"] = evidence_ids
            allowed.setdefault("content", llm_output.get("content", ""))
            allowed.setdefault("quality_score", llm_output.get("quality_score", 0.6))
            return spec.output_model.model_validate(allowed)
        except ValidationError:
            return None

    def _safety_review(self, output: OutputModel) -> OutputModel:
        from app.runtime.guardrails.output_filter import safety_review

        return safety_review(output)

    async def _emit_progress(
        self,
        ctx: HarnessContext,
        spec: SkillSpec[InputModel, OutputModel],
        *,
        status: str,
        percentage: int,
    ) -> None:
        await ctx.emit(
            {
                "event": "progress",
                "node_name": spec.name,
                "status": status,
                "agent_id": str(spec.agent_id) if spec.agent_id else None,
                "skill_id": str(spec.skill_id) if spec.skill_id else None,
                "percentage": percentage,
            }
        )

    async def _emit_evidence(self, ctx: HarnessContext, evidence: list[EvidenceCard]) -> None:
        from app.schemas.evidence import evidence_card_to_dto

        await ctx.emit(
            {
                "event": "evidence",
                "chunks": [
                    evidence_card_to_dto(card).model_dump(mode="json")
                    for card in evidence
                ],
            }
        )

    async def _emit_done(
        self,
        ctx: HarnessContext,
        spec: SkillSpec[InputModel, OutputModel],
        run_id: UUID,
        quality_score: float,
    ) -> None:
        await ctx.emit(
            {
                "event": "progress",
                "node_name": spec.name,
                "status": "success",
                "agent_id": str(spec.agent_id) if spec.agent_id else None,
                "skill_id": str(spec.skill_id) if spec.skill_id else None,
                "percentage": 100,
            }
        )
        await ctx.emit(
            {
                "event": "trace",
                "agent_name": spec.agent_name,
                "skill_name": spec.name,
                "status": "success",
                "run_id": str(run_id),
                "quality_score": quality_score,
            }
        )

    async def _emit_persistence_error(self, ctx: HarnessContext) -> None:
        await ctx.emit(
            {
                "event": "error",
                "code": "AGENT_RUN_PERSIST_FAILED",
                "message": "agent_runs persistence could not be verified",
                "recoverable": False,
            }
        )

    async def _fail(
        self,
        ctx: HarnessContext,
        spec: SkillSpec[InputModel, OutputModel],
        run_id: UUID,
        telemetry: HarnessTelemetry,
        code: str,
        message: str,
    ) -> None:
        telemetry.status = RunStatus.failed if code != "safety_blocked" else RunStatus.blocked
        await ctx.emit(
            {
                "event": "error",
                "code": code,
                "message": message,
                "recoverable": str(code).lower()
                in {"tool_unavailable", "insufficient_evidence", "provider_unavailable"},
            }
        )
        if spec.log_run:
            try:
                await ctx.log_run(
                    run_id=run_id,
                    workflow_name=ctx.workflow_name,
                    user_id=ctx.user_id,
                    agent_id=spec.agent_id,
                    skill_id=spec.skill_id,
                    parent_run_id=ctx.parent_run_id,
                    input_summary={"failure": message, "skill": spec.name},
                    output_summary={"code": code},
                    evidence_chunk_ids=[],
                    quality_score=None,
                    status=telemetry.status.value,
                    duration_ms=None,
                    token_usage={},
                )
            except Exception as exc:
                if spec.strict_log_run:
                    await self._emit_persistence_error(ctx)
                    raise AgentRunPersistenceFailed(
                        "strict agent_runs persistence could not be verified"
                    ) from exc


# Default process-wide harness used by skill helper functions.
DEFAULT_HARNESS = Harness()


async def run_skill(
    spec: SkillSpec[InputModel, OutputModel],
    inp: InputModel,
    ctx: HarnessContext,
    *,
    harness: Harness | None = None,
) -> OutputModel:
    """Convenience wrapper used inside ``BaseSkill.run`` implementations."""
    return await (harness or DEFAULT_HARNESS).run(spec, inp, ctx)
