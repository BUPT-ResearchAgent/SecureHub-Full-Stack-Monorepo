# Status: [planned]

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph


class CourseState(TypedDict, total=False):
    user_id: str
    course_id: str
    selected_kp_ids: list[str]
    persona: dict[str, Any]
    path: dict[str, Any]
    resources: dict[str, Any]
    quality: dict[str, Any]
    recommendations: list[dict[str, Any]]
    iteration: int


async def n1_build_persona(state: CourseState) -> CourseState:
    raise NotImplementedError("TODO: call career_planner.BuildLearningPersona and emit progress 10")


async def n2_plan(state: CourseState) -> CourseState:
    raise NotImplementedError("TODO: call task_orchestrator.GenerateLearningPath and emit progress 20")


async def n3_generate_resources(state: CourseState) -> CourseState:
    raise NotImplementedError("TODO: fan out doc/ppt/mindmap/quiz/lab/video generation")


async def n4_quality(state: CourseState) -> CourseState:
    raise NotImplementedError("TODO: call outcome_evaluator.QualityCheck and emit progress 90")


async def n5_recommend(state: CourseState) -> CourseState:
    raise NotImplementedError("TODO: call career_planner.RecommendResources")


async def n6_update(state: CourseState) -> CourseState:
    raise NotImplementedError("TODO: call outcome_evaluator.UpdateCapability and career_planner.UpdatePersona")


def quality_branch(state: CourseState) -> str:
    quality = state.get("quality", {})
    iteration = state.get("iteration", 0)
    return "recommend" if quality.get("accept") or iteration >= 2 else "regen"


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
