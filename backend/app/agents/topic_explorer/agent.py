# Status: [planned]

from app.agents.base import AgentCapability, BaseAgent
from app.agents.topic_explorer.skills import generate_hands_on_lab, generate_research_topic, recommend_readings


class TopicExplorerAgent(BaseAgent):
    name = "topic_explorer"
    role_description = "Explore research topics, reading paths, and hands-on labs."
    capability_vector = AgentCapability(topic=1.0, doc=0.5, competition=0.3)
    tools = ["rag.retrieve", "llm.xfyun"]
    risk_level = "medium"
    skills = {
        "GenerateResearchTopic": generate_research_topic.GenerateResearchTopic,
        "GenerateHandsOnLab": generate_hands_on_lab.GenerateHandsOnLab,
        "RecommendReadings": recommend_readings.RecommendReadings,
    }
