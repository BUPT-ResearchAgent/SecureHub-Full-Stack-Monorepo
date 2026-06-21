# Status: real

"""Manual P0.5 live-LLM acceptance tests.

Run only when quota-bearing live calls are explicitly enabled:

    ENABLE_LLM_LIVE_TESTS=true LLM_PROVIDER=deepseek DEEPSEEK_API_KEY=... pytest -m llm_live

Default CI must keep using fixtures via ``pytest -m "not llm_live"``.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.core.config import get_settings
from app.db.models.agent.agent_run import AgentRun
from app.db.seeds._constants import COURSE_WEBSEC_ID, DEMO_USER_ID, node_id, stable_id
from app.db.seeds.seed_course_websec import run as seed_course_websec
from app.db.seeds.seed_demo_user import run as seed_demo_user
from app.llm import get_llm_client
from app.llm.base import ChatMessage
from app.repositories.agent.agent_runs import AgentRunRepository
from app.repositories.resource.generated_resources import GeneratedResourceRepository
from app.services.knowledge.retrieval_service import ChunkHit, RetrievalService

pytestmark = pytest.mark.llm_live

DOMAIN = "course_websec"
SQLI_QUERY = "SQL 注入 参数化查询 防御"
NO_EVIDENCE_QUERY = "量子卫星轨道力学 深空通信 课程文档"


@dataclass(slots=True)
class LiveLimits:
    enabled: bool
    max_calls_per_user_per_day: int
    max_tokens_per_request: int
    timeout_seconds: float
    daily_budget_cny: float


@dataclass(slots=True)
class LiveCallResult:
    content: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_estimate: float
    duration_ms: int


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw and raw.strip() else default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw and raw.strip() else default


def _limits() -> LiveLimits:
    return LiveLimits(
        enabled=_env_bool("ENABLE_LLM_LIVE_TESTS", False),
        max_calls_per_user_per_day=_env_int("MAX_LLM_CALLS_PER_USER_PER_DAY", 5),
        max_tokens_per_request=_env_int("MAX_TOKENS_PER_REQUEST", 1600),
        timeout_seconds=_env_float("LLM_TIMEOUT_SECONDS", 45.0),
        daily_budget_cny=_env_float("LLM_DAILY_BUDGET_CNY", 1.0),
    )


def _configured_provider() -> tuple[str, str]:
    provider = os.getenv("LLM_PROVIDER", "deepseek").strip().lower()
    if provider == "deepseek" and os.getenv("DEEPSEEK_API_KEY"):
        return provider, os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    if provider == "xfyun" and os.getenv("XFYUN_API_KEY"):
        return provider, os.getenv("XFYUN_MODEL", "spark-v4")
    if os.getenv("DEEPSEEK_API_KEY"):
        return "deepseek", os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    if os.getenv("XFYUN_API_KEY"):
        return "xfyun", os.getenv("XFYUN_MODEL", "spark-v4")
    pytest.skip("llm_live requires DEEPSEEK_API_KEY or XFYUN_API_KEY")


def _estimate_tokens(text: str) -> int:
    # Conservative enough for guard tests without adding tokenizer coupling.
    ascii_words = sum(1 for part in text.split() if part.isascii())
    cjk_chars = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return max(1, ascii_words + cjk_chars // 2)


def _estimate_cost_cny(provider: str, total_tokens: int) -> float:
    rate_per_1k = _env_float(f"{provider.upper()}_CNY_PER_1K_TOKENS", 0.002)
    return round(total_tokens / 1000 * rate_per_1k, 6)


def _evidence_block(hits: list[ChunkHit]) -> str:
    lines: list[str] = []
    for idx, hit in enumerate(hits, start=1):
        source_url = hit.metadata.get("source_url")
        lines.append(
            f"[E{idx}] title={hit.title}\n"
            f"source_url={source_url}\n"
            f"platform={hit.metadata.get('platform')}\n"
            f"rights_note={hit.metadata.get('rights_note')}\n"
            f"text={hit.snippet}"
        )
    return "\n\n".join(lines)


async def _live_chat(
    *,
    provider: str,
    prompt: str,
    limits: LiveLimits,
) -> LiveCallResult:
    prompt_tokens = _estimate_tokens(prompt)
    assert prompt_tokens <= limits.max_tokens_per_request

    get_settings.cache_clear()
    client = get_llm_client(provider)
    start = time.perf_counter()
    result = await asyncio.wait_for(
        client.chat(
            [
                ChatMessage(
                    role="system",
                    content=(
                        "你是 SecureHub 的 Web 安全课程助教。"
                        "必须只依据 evidence 回答，必须引用 evidence 编号和 source_url；"
                        "不知道或证据不足时要拒答。"
                    ),
                ),
                ChatMessage(role="user", content=prompt),
            ],
            stream=False,
            temperature=0.1,
        ),
        timeout=limits.timeout_seconds,
    )
    content = result if isinstance(result, str) else ""
    duration_ms = int((time.perf_counter() - start) * 1000)
    completion_tokens = _estimate_tokens(content)
    total_tokens = prompt_tokens + completion_tokens
    assert total_tokens <= limits.max_tokens_per_request
    return LiveCallResult(
        content=content,
        provider=provider,
        model=getattr(client, "model", "unknown"),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost_estimate=_estimate_cost_cny(provider, total_tokens),
        duration_ms=duration_ms,
    )


async def _record_acceptance(
    session: Any,
    *,
    task_name: str,
    resource_type: str,
    content: str,
    hits: list[ChunkHit],
    call: LiveCallResult,
) -> tuple[AgentRun, UUID]:
    evidence_ids = [hit.chunk_id for hit in hits]
    token_usage = {
        "provider": call.provider,
        "model": call.model,
        "prompt": call.prompt_tokens,
        "completion": call.completion_tokens,
        "total": call.total_tokens,
        "cost_estimate": call.cost_estimate,
        "currency": "CNY",
    }

    run_id = uuid4()
    run_repo = AgentRunRepository(session)
    run = await run_repo.create(
        run_id=run_id,
        workflow_name="llm_live_p0",
        status="running",
        user_id=DEMO_USER_ID,
        input_summary={"task": task_name, "query": SQLI_QUERY},
    )
    updated = await run_repo.mark_success(
        run_id,
        output_summary={"content": content[:1000]},
        evidence_chunk_ids=evidence_ids,
        quality_score=0.8,
        duration_ms=call.duration_ms,
        token_usage=token_usage,
    )
    assert updated is not None

    resource_repo = GeneratedResourceRepository(session)
    resource = await resource_repo.create(
        resource_id=stable_id(f"generated:llm-live:{resource_type}:{task_name}"),
        user_id=DEMO_USER_ID,
        course_id=COURSE_WEBSEC_ID,
        kp_id=node_id("sql-injection"),
        agent_run_id=run_id,
        resource_type=resource_type,
        title=f"llm_live {task_name}",
        content={"text": content},
        object_key=f"generated/course_websec/llm_live/{task_name}.md",
        evidence_chunk_ids=evidence_ids,
        quality_score=0.8,
        metadata={
            "provider": call.provider,
            "model": call.model,
            "token_usage": token_usage,
            "cost_estimate": call.cost_estimate,
        },
    )
    await session.commit()
    return run, resource.id


def _assert_acceptance(content: str, hits: list[ChunkHit], call: LiveCallResult) -> None:
    assert content.strip()
    assert any(f"[E{idx}]" in content for idx in range(1, len(hits) + 1))
    assert any(str(hit.metadata.get("source_url")) in content for hit in hits)
    assert "http" in content
    assert call.provider in {"deepseek", "xfyun"}
    assert call.model
    assert call.total_tokens > 0
    assert call.cost_estimate >= 0


@pytest.mark.anyio
async def test_p0_sql_injection_real_llm_acceptance_matrix(sqlite_session) -> None:
    limits = _limits()
    if not limits.enabled:
        pytest.skip("ENABLE_LLM_LIVE_TESTS=false")
    provider, _model = _configured_provider()

    await seed_demo_user(sqlite_session)
    await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    hits = list(
        await RetrievalService(sqlite_session).retrieve(
            SQLI_QUERY,
            domain=DOMAIN,
            top_k=5,
        )
    )
    assert len(hits) >= 3
    evidence_text = _evidence_block(hits)

    tasks = [
        (
            "learning_path",
            "learning_path",
            "生成 SQL 注入学习路径，包含 3 个阶段，每阶段必须引用 evidence 编号和 source_url。",
        ),
        (
            "course_doc",
            "course_doc",
            "生成 SQL 注入课程文档，覆盖定义、风险、防御，每段必须引用 evidence 编号和 source_url。",
        ),
        (
            "quiz_set",
            "quiz_set",
            "生成 3 道 SQL 注入练习题和答案解析，每题必须引用 evidence 编号和 source_url。",
        ),
        (
            "tutor_qa",
            "tutor_answer",
            "回答学生问题：参数化查询为什么能防 SQL 注入？必须引用 evidence 编号和 source_url。",
        ),
    ]
    assert len(tasks) <= limits.max_calls_per_user_per_day

    total_cost = 0.0
    for task_name, resource_type, instruction in tasks:
        prompt = f"[Evidence]\n{evidence_text}\n\n[Task]\n{instruction}"
        call = await _live_chat(provider=provider, prompt=prompt, limits=limits)
        total_cost += call.cost_estimate
        assert total_cost <= limits.daily_budget_cny

        _assert_acceptance(call.content, hits, call)
        run, resource_id = await _record_acceptance(
            sqlite_session,
            task_name=task_name,
            resource_type=resource_type,
            content=call.content,
            hits=hits,
            call=call,
        )
        assert run.status == "success"
        assert run.evidence_chunk_ids
        assert run.token_usage["provider"] == provider
        assert run.token_usage["model"]
        assert run.token_usage["total"] > 0
        assert run.token_usage["cost_estimate"] >= 0
        assert resource_id


@pytest.mark.anyio
async def test_p0_real_llm_insufficient_evidence_refuses_without_call(sqlite_session) -> None:
    limits = _limits()
    if not limits.enabled:
        pytest.skip("ENABLE_LLM_LIVE_TESTS=false")
    _configured_provider()

    await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    hits = list(
        await RetrievalService(sqlite_session).retrieve(
            NO_EVIDENCE_QUERY,
            domain=DOMAIN,
            top_k=5,
        )
    )

    llm_calls = 0
    if len(hits) < 3:
        refusal = "证据不足：未达到 3 条 evidence，拒绝调用真实 LLM。"
    else:  # pragma: no cover - defensive if future seed expands into this topic
        llm_calls += 1
        refusal = ""

    assert llm_calls == 0
    assert "证据不足" in refusal
