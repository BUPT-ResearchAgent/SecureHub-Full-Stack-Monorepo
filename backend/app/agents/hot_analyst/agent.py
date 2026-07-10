# Status: real

from app.agents.base import AgentCapability, BaseAgent
from app.agents.hot_analyst.skills import analyze_hot_event, recommend_readings


class HotAnalystAgent(BaseAgent):
    name = "hot_analyst"
    role_description = "Analyze security events and recommend safe educational readings."
    capability_vector = AgentCapability(hot=1.0, topic=0.5, eval=0.4)
    tools = ["rag.retrieve", "llm.xfyun"]
    risk_level = "high"
    skills = {
        "AnalyzeHotEvent": analyze_hot_event.AnalyzeHotEvent,
        "RecommendReadings": recommend_readings.RecommendReadings,
    }
