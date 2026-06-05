# Status: [planned]

from app.agents.base import AgentCapability, BaseAgent


class JobAnalystAgent(BaseAgent):
    name = "job_analyst"
    role_description = "Analyze job market and skill demand; concrete skills are P2 in this round."
    capability_vector = AgentCapability(job=1.0, planning=0.4)
    tools = ["rag.retrieve", "llm.xfyun"]
    risk_level = "low"
    skills = {}
