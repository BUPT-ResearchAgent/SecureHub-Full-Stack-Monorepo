# Status: real

"""Skill Execution Service — B 调用的稳定 service 层接口。

提供 6 个函数供 B 的 endpoint 薄适配调用：
- build_learning_persona()
- generate_learning_path()
- generate_course_doc()
- generate_quiz()
- ask_tutor()
- run_assessment()

设计原则：
- B 无需了解 Harness / SkillSpec 内部，只传入业务参数，拿回结构化结果。
- 所有函数在 fixture 模式下可运行（无需真实 API Key）。
- 证据不足时抛出 InsufficientEvidence，不调用 LLM。
- 每次 skill 运行自动写入 agent_runs（通过 HarnessContext.log_run）。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.harness import Harness, HarnessContext, SkillSpec
from app.runtime.harness.context import HarnessConfig

logger = logging.getLogger(__name__)


# ── Shared helpers ───────────────────────────────────────────────────────────


def _make_ctx(
    user_id: str | UUID | None = None,
    workflow_name: str = "course_learning",
    session: AsyncSession | None = None,
    persona_summary: str = "",
    stream: bool = False,
) -> HarnessContext:
    """构造 HarnessContext，接入 DB session 的 log_run hook。"""
    from app.core.config import get_settings

    settings = get_settings()
    ctx = HarnessContext(
        user_id=str(user_id) if user_id else None,
        workflow_name=workflow_name,
        persona_summary=persona_summary,
        stream=stream,
        config=HarnessConfig(
            min_evidence=settings.MIN_EVIDENCE,
            mock_mode=(not settings.XFYUN_API_KEY and not settings.DEEPSEEK_API_KEY),
            llm_provider=settings.LLM_PROVIDER,
        ),
    )
    if session is not None:
        ctx = _inject_db_log_run(ctx, session, workflow_name)
    return ctx


def _inject_db_log_run(ctx: HarnessContext, session: AsyncSession, workflow_name: str) -> HarnessContext:
    """将 ctx.log_run 替换为写 agent_runs 表的实现。"""
    from app.services.agent.agent_run_service import AgentRunService

    svc = AgentRunService(session)

    async def _log_run(**kwargs: Any) -> str:
        run_id = await svc.begin_run(
            workflow_name=workflow_name,
            agent_name=kwargs.get("agent_name"),
            skill_name=kwargs.get("skill_name"),
            user_id=UUID(ctx.user_id) if ctx.user_id else None,
        )
        status = kwargs.get("status", "success")
        if status == "success":
            await svc.finish_success(
                run_id,
                output_summary=kwargs.get("output_summary", {}),
                evidence_chunk_ids=[UUID(c) for c in kwargs.get("evidence_chunk_ids", []) if _is_uuid(c)],
                quality_score=kwargs.get("quality_score"),
                duration_ms=kwargs.get("duration_ms"),
                token_usage=kwargs.get("token_usage"),
            )
        else:
            await svc.finish_failed(
                run_id,
                error_summary=kwargs.get("output_summary", {"error": kwargs.get("status")}),
                duration_ms=kwargs.get("duration_ms"),
            )
        await session.commit()
        return str(run_id)

    ctx.log_run = _log_run  # type: ignore[method-assign]
    return ctx


def _is_uuid(val: str) -> bool:
    try:
        UUID(val)
        return True
    except (ValueError, AttributeError):
        return False


def _harness() -> Harness:
    return Harness()


# ── build_learning_persona ───────────────────────────────────────────────────


async def build_learning_persona(
    *,
    user_id: str | UUID,
    message: str,
    dialogue_turns: list[dict[str, str]] | None = None,
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """对话式画像构建（A3 关键能力：≥6 维画像）。

    Args:
        user_id: 学生 ID
        message: 当前对话消息
        dialogue_turns: 历史对话轮次
        session: DB session（如提供则写入 agent_runs）

    Returns:
        {dimensions: dict, next_question: str, evidence_chunk_ids: list, quality_score: float}
    """
    from app.agents.career_planner.skills.build_learning_persona import (
        BuildLearningPersona,
        BuildLearningPersonaInput,
    )

    skill = BuildLearningPersona()
    inp = BuildLearningPersonaInput(
        user_id=str(user_id),
        query=message,
        dialogue_turns=dialogue_turns or [],
    )
    ctx = _make_ctx(user_id=user_id, workflow_name="profile_chat", session=session)
    from app.agents.base import SkillContext

    skill_ctx = SkillContext(
        user_id=str(user_id),
        workflow_name="profile_chat",
        persona_summary=ctx.persona_summary,
        config=ctx.config,
    )
    out = await skill.run(inp, skill_ctx)
    return out.model_dump()


# ── generate_learning_path ───────────────────────────────────────────────────


async def generate_learning_path(
    *,
    user_id: str | UUID,
    course_id: str,
    selected_kp_ids: list[str] | None = None,
    persona_summary: str = "",
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """个性化学习路径规划（A3 关键能力）。

    Returns:
        {nodes: list, edges: list, milestones: list, evidence_chunk_ids: list}
    """
    from app.agents.task_orchestrator.skills.generate_learning_path import (
        GenerateLearningPath,
        GenerateLearningPathInput,
    )
    from app.agents.base import SkillContext

    skill = GenerateLearningPath()
    inp = GenerateLearningPathInput(
        user_id=str(user_id),
        query=f"学习路径规划: {course_id}",
        selected_kp_ids=selected_kp_ids or [],
    )
    ctx = _make_ctx(user_id=user_id, workflow_name="course_learning", session=session, persona_summary=persona_summary)
    skill_ctx = SkillContext(
        user_id=str(user_id),
        workflow_name="course_learning",
        persona_summary=persona_summary,
        config=ctx.config,
    )
    out = await skill.run(inp, skill_ctx)
    return out.model_dump()


# ── generate_course_doc ──────────────────────────────────────────────────────


async def generate_course_doc(
    *,
    user_id: str | UUID,
    course_id: str,
    kp_id: str | None = None,
    query: str = "课程讲解文档",
    persona_summary: str = "",
    session: AsyncSession | None = None,
    resource_session: AsyncSession | None = None,
) -> dict[str, Any]:
    """生成课程讲解文档（A3 资源类型 1）。

    Returns:
        {markdown: str, sections: list, evidence_chunk_ids: list, resource_id?: str}
    """
    from app.agents.doc_archivist.skills.generate_course_doc import (
        GenerateCourseDoc,
        GenerateCourseDocInput,
    )
    from app.agents.base import SkillContext

    skill = GenerateCourseDoc()
    inp = GenerateCourseDocInput(user_id=str(user_id), query=query, kp_id=kp_id)
    ctx = _make_ctx(user_id=user_id, workflow_name="course_learning", session=session, persona_summary=persona_summary)
    skill_ctx = SkillContext(
        user_id=str(user_id),
        workflow_name="course_learning",
        persona_summary=persona_summary,
        config=ctx.config,
    )
    out = await skill.run(inp, skill_ctx)
    result = out.model_dump()

    if resource_session is not None and out.evidence_chunk_ids:
        resource_id = await _register_resource(
            session=resource_session,
            resource_type="course_doc",
            title=f"课程文档 — {query}",
            user_id=user_id,
            course_id=course_id,
            kp_id=kp_id,
            content={"markdown": out.markdown, "sections": out.sections},
            evidence_chunk_ids=out.evidence_chunk_ids,
            quality_score=out.quality_score,
        )
        result["resource_id"] = str(resource_id)

    return result


# ── generate_quiz ────────────────────────────────────────────────────────────


async def generate_quiz(
    *,
    user_id: str | UUID,
    course_id: str,
    kp_id: str | None = None,
    query: str = "知识点练习题",
    difficulty: int = 3,
    session: AsyncSession | None = None,
    resource_session: AsyncSession | None = None,
) -> dict[str, Any]:
    """生成练习题目（A3 资源类型 3）。

    Returns:
        {quiz_items: list, evidence_chunk_ids: list, resource_id?: str}
    """
    from app.agents.competition_advisor.skills.generate_quiz import (
        GenerateQuiz,
        GenerateQuizInput,
    )
    from app.agents.base import SkillContext

    skill = GenerateQuiz()
    inp = GenerateQuizInput(user_id=str(user_id), query=query, kp_id=kp_id, difficulty=difficulty)
    ctx = _make_ctx(user_id=user_id, workflow_name="course_learning", session=session)
    skill_ctx = SkillContext(user_id=str(user_id), workflow_name="course_learning", config=ctx.config)
    out = await skill.run(inp, skill_ctx)
    result = out.model_dump()

    if resource_session is not None and out.evidence_chunk_ids:
        resource_id = await _register_resource(
            session=resource_session,
            resource_type="quiz",
            title=f"练习题 — {query}",
            user_id=user_id,
            course_id=course_id,
            kp_id=kp_id,
            content={"quiz_items": out.quiz_items},
            evidence_chunk_ids=out.evidence_chunk_ids,
            quality_score=out.quality_score,
        )
        result["resource_id"] = str(resource_id)

    return result


# ── ask_tutor ────────────────────────────────────────────────────────────────


async def ask_tutor(
    *,
    user_id: str | UUID,
    message: str,
    course_id: str | None = None,
    persona_summary: str = "",
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """智能辅导意图路由（P1 功能）。

    RouteTutorQuestion → 识别意图 → 路由到对应 skill。

    Returns:
        {answer: str, intent: str, routed_agent: str, evidence_chunk_ids: list}
    """
    from app.agents.career_planner.skills.route_tutor_question import (
        RouteTutorQuestion,
        RouteTutorQuestionInput,
    )
    from app.agents.base import SkillContext

    skill = RouteTutorQuestion()
    inp = RouteTutorQuestionInput(user_id=str(user_id), query=message)
    ctx = _make_ctx(user_id=user_id, workflow_name="tutor", session=session, persona_summary=persona_summary)
    skill_ctx = SkillContext(
        user_id=str(user_id),
        workflow_name="tutor",
        persona_summary=persona_summary,
        config=ctx.config,
    )
    out = await skill.run(inp, skill_ctx)
    return out.model_dump()


# ── run_assessment ───────────────────────────────────────────────────────────


async def run_assessment(
    *,
    user_id: str | UUID,
    course_id: str,
    answers: list[dict[str, Any]],
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """学习效果评估（A3 关键能力：多维评估 + 画像演化）。

    Returns:
        {score: float, weak_kp_ids: list, next_recommendation: str,
         capability_delta: dict, evidence_chunk_ids: list}
    """
    from app.agents.outcome_evaluator.skills.run_assessment import (
        RunAssessment,
        RunAssessmentInput,
    )
    from app.agents.base import SkillContext

    skill = RunAssessment()
    inp = RunAssessmentInput(
        user_id=str(user_id),
        query=f"学习效果评估: {course_id}",
        answers=answers,
    )
    ctx = _make_ctx(user_id=user_id, workflow_name="assessment", session=session)
    skill_ctx = SkillContext(user_id=str(user_id), workflow_name="assessment", config=ctx.config)
    out = await skill.run(inp, skill_ctx)
    return out.model_dump()


# ── helpers ──────────────────────────────────────────────────────────────────


async def _register_resource(
    *,
    session: AsyncSession,
    resource_type: str,
    title: str,
    user_id: str | UUID,
    course_id: str | None,
    kp_id: str | None,
    content: dict[str, Any],
    evidence_chunk_ids: list[str],
    quality_score: float | None,
) -> UUID:
    from app.services.resource.resource_generation_service import ResourceGenerationService

    svc = ResourceGenerationService(session)
    resource_id = await svc.register(
        resource_type=resource_type,
        title=title,
        user_id=UUID(str(user_id)) if user_id else None,
        course_id=UUID(course_id) if course_id and _is_uuid(course_id) else None,
        kp_id=UUID(kp_id) if kp_id and _is_uuid(kp_id) else None,
        agent_run_id=None,
        content=content,
        object_key=None,
        evidence_chunk_ids=[UUID(c) for c in evidence_chunk_ids if _is_uuid(c)],
        quality_score=quality_score,
    )
    await session.commit()
    return resource_id
