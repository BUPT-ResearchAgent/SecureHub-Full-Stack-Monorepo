# Status: [planned]

from app.agents.base import AgentCapability, BaseAgent
from app.agents.career_planner.skills import build_learning_persona, recommend_resources, update_persona


class CareerPlannerAgent(BaseAgent):
    name = "career_planner"
    role_description = "Build and update learning persona, then recommend personalized resources."
    capability_vector = AgentCapability(planning=1.0, task=0.5, eval=0.5)
    tools = ["rag.retrieve", "llm.xfyun"]
    risk_level = "high"
    skills = {
        "BuildLearningPersona": build_learning_persona.BuildLearningPersona,
        "UpdatePersona": update_persona.UpdatePersona,
        "RecommendResources": recommend_resources.RecommendResources,
    }
