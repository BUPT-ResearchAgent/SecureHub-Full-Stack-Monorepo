# Status: real

from app.agents.base import AgentCapability, BaseAgent
from app.agents.career_planner.skills import (
    build_learning_persona,
    generate_growth_plan,
    recommend_resources,
    route_tutor_question,
    update_persona,
)


class CareerPlannerAgent(BaseAgent):
    name = "career_planner"
    role_description = "Build and update learning persona, route tutor questions, recommend personalized resources, and produce growth plans."
    capability_vector = AgentCapability(planning=1.0, task=0.5, eval=0.5)
    tools = ["rag.retrieve", "llm.xfyun"]
    risk_level = "high"
    skills = {
        "BuildLearningPersona": build_learning_persona.BuildLearningPersona,
        "UpdatePersona": update_persona.UpdatePersona,
        "RecommendResources": recommend_resources.RecommendResources,
        "RouteTutorQuestion": route_tutor_question.RouteTutorQuestion,
        "GenerateGrowthPlan": generate_growth_plan.GenerateGrowthPlan,
    }
