# Status: real

"""LangGraph 课程学习多智能体工作流。

DAG（来源：A3赛题规划.md §3.1 P0-5、SecureHub_智能体开发计划.md §7.2）：

    build_persona → plan → generate_resources (fan-out) → quality_check
                                                                ↓
                                                       (regen | recommend)
                                                                ↓
                                                              update

每个节点：
- 通过 Harness 调用对应 skill；
- emit ``progress`` / ``evidence`` / ``trace`` / ``token`` SSE 事件；
- 输出写入下一节点的 state；
- 必要时把生成物登记到 ``generated_resources``（最小化：fixture 模式跳过 DB）。
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.career_planner.skills.build_learning_persona import (
    BuildLearningPersona,
    BuildLearningPersonaInput,
)
from app.agents.career_planner.skills.recommend_resources import (
    RecommendResources,
    RecommendResourcesInput,
)
from app.agents.career_planner.skills.update_persona import (
    UpdatePersona,
    UpdatePersonaInput,
)
from app.agents.competition_advisor.skills.generate_quiz import (
    GenerateQuiz,
    GenerateQuizInput,
)
from app.agents.doc_archivist.skills.generate_course_doc import (
    GenerateCourseDoc,
    GenerateCourseDocInput,
)
from app.agents.doc_archivist.skills.generate_course_ppt import (
    GenerateCoursePPT,
    GenerateCoursePPTInput,
)
from app.agents.doc_archivist.skills.generate_mindmap import (
    GenerateMindmap,
    GenerateMindmapInput,
)
from app.agents.doc_archivist.skills.generate_video_storyboard import (
    GenerateVideoStoryboard,
    GenerateVideoStoryboardInput,
)
from app.agents.outcome_evaluator.skills.quality_check import (
    QualityCheck,
    QualityCheckInput,
)
from app.agents.outcome_evaluator.skills.update_capability import (
    UpdateCapability,
    UpdateCapabilityInput,
)
from app.agents.task_orchestrator.skills.generate_learning_path import (
    GenerateLearningPath,
    GenerateLearningPathInput,
)
from app.agents.topic_explorer.skills.generate_hands_on_lab import (
    GenerateHandsOnLab,
    GenerateHandsOnLabInput,
)
from app.runtime.harness import HarnessContext


class CourseState(TypedDict, total=False):
    user_id: str
    course_id: str
    selected_kp_ids: list[str]
    query: str
    persona: dict[str, Any]
    path: dict[str, Any]
    resources: dict[str, Any]
    quality: dict[str, Any]
    recommendations: list[dict[str, Any]]
    iteration: int
    ctx: HarnessContext


def _ctx(state: CourseState) -> HarnessContext:
    ctx = state.get("ctx")
    if ctx is None:
        raise RuntimeError("course_learning state missing HarnessContext; api endpoint must inject it")
    return ctx


def _query(state: CourseState, fallback: str) -> str:
    return state.get("query") or fallback


async def n1_build_persona(state: CourseState) -> CourseState:
    ctx = _ctx(state)
    skill = BuildLearningPersona()
    inp = BuildLearningPersonaInput(
        user_id=state.get("user_id", "demo"),
        query=_query(state, "构建网络安全学习画像"),
        dialogue_turns=state.get("persona", {}).get("dialogue_turns", []),
    )
    out = await skill.run(inp, ctx)
    state["persona"] = out.model_dump()
    ctx.persona_summary = out.content or ctx.persona_summary
    return state


async def n2_plan(state: CourseState) -> CourseState:
    ctx = _ctx(state)
    skill = GenerateLearningPath()
    inp = GenerateLearningPathInput(
        user_id=state.get("user_id", "demo"),
        query=_query(state, "生成 Web 安全个性化学习路径"),
        course_id=state.get("course_id"),
    )
    out = await skill.run(inp, ctx)
    state["path"] = out.model_dump()
    return state


async def n3_generate_resources(state: CourseState) -> CourseState:
    ctx = _ctx(state)
    user = state.get("user_id", "demo")
    base_query = _query(state, "SQL 注入知识点")
    kp_id = (state.get("selected_kp_ids") or [None])[0]
    resources: dict[str, Any] = {}

    pairs: list[tuple[str, Any, Any]] = [
        ("doc", GenerateCourseDoc(), GenerateCourseDocInput(user_id=user, query=base_query, kp_id=kp_id)),
        ("ppt", GenerateCoursePPT(), GenerateCoursePPTInput(user_id=user, query=base_query, kp_id=kp_id)),
        ("mindmap", GenerateMindmap(), GenerateMindmapInput(user_id=user, query=base_query, kp_id=kp_id)),
        (
            "video",
            GenerateVideoStoryboard(),
            GenerateVideoStoryboardInput(user_id=user, query=base_query, kp_id=kp_id),
        ),
        ("quiz", GenerateQuiz(), GenerateQuizInput(user_id=user, query=base_query, kp_id=kp_id)),
        ("lab", GenerateHandsOnLab(), GenerateHandsOnLabInput(user_id=user, query=base_query)),
    ]
    for kind, skill, inp in pairs:
        try:
            out = await skill.run(inp, ctx)
            resources[kind] = out.model_dump()
            await ctx.emit(
                {
                    "event": "artifact",
                    "type": kind,
                    "title": resources[kind].get("content", kind),
                }
            )
        except Exception as exc:  # noqa: BLE001 - allow partial fan-out
            resources[kind] = {"error": str(exc)}
    state["resources"] = resources
    return state


async def n4_quality(state: CourseState) -> CourseState:
    ctx = _ctx(state)
    skill = QualityCheck()
    inp = QualityCheckInput(
        user_id=state.get("user_id", "demo"),
        query=_query(state, "课程文档质量校验"),
        artifact={"resources": state.get("resources", {})},
    )
    out = await skill.run(inp, ctx)
    state["quality"] = out.model_dump()
    state["iteration"] = state.get("iteration", 0) + 1
    return state


async def n5_recommend(state: CourseState) -> CourseState:
    ctx = _ctx(state)
    skill = RecommendResources()
    inp = RecommendResourcesInput(
        user_id=state.get("user_id", "demo"),
        query=_query(state, "向当前学习者推送下一步资源"),
        current_kp_id=(state.get("selected_kp_ids") or [None])[0],
    )
    out = await skill.run(inp, ctx)
    state["recommendations"] = out.model_dump().get("resources", [])
    return state


async def n6_update(state: CourseState) -> CourseState:
    ctx = _ctx(state)
    cap_skill = UpdateCapability()
    cap_inp = UpdateCapabilityInput(
        user_id=state.get("user_id", "demo"),
        query=_query(state, "回流更新画像与能力雷达"),
    )
    await cap_skill.run(cap_inp, ctx)

    persona_skill = UpdatePersona()
    persona_inp = UpdatePersonaInput(
        user_id=state.get("user_id", "demo"),
        query=_query(state, "根据学习事件更新画像"),
    )
    await persona_skill.run(persona_inp, ctx)
    return state


def quality_branch(state: CourseState) -> str:
    quality = state.get("quality", {})
    iteration = state.get("iteration", 0)
    accept = quality.get("accept") if isinstance(quality, dict) else getattr(quality, "accept", False)
    return "recommend" if accept or iteration >= 2 else "regen"


def build_course_learning_graph():
    graph = StateGraph(CourseState)
    graph.add_node("build_persona", n1_build_persona)
    graph.add_node("plan", n2_plan)
    graph.add_node("generate_resources", n3_generate_resources)
    graph.add_node("quality", n4_quality)
    graph.add_node("recommend", n5_recommend)
    graph.add_node("update", n6_update)
    graph.set_entry_point("build_persona")
    graph.add_edge("build_persona", "plan")
    graph.add_edge("plan", "generate_resources")
    graph.add_edge("generate_resources", "quality")
    graph.add_conditional_edges("quality", quality_branch, {"recommend": "recommend", "regen": "generate_resources"})
    graph.add_edge("recommend", "update")
    graph.add_edge("update", END)
    return graph.compile()
