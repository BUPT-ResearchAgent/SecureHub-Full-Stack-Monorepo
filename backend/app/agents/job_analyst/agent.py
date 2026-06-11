# Status: real

from app.agents.base import AgentCapability, BaseAgent
from app.agents.job_analyst.skills import analyze_job_market, skill_gap_analysis


class JobAnalystAgent(BaseAgent):
    name = "job_analyst"
    role_description = "Analyze job market trends and skill gaps versus learner profile."
    capability_vector = AgentCapability(job=1.0, planning=0.4)
    tools = ["rag.retrieve", "llm.xfyun"]
    risk_level = "low"
    skills = {
        "AnalyzeJobMarket": analyze_job_market.AnalyzeJobMarket,
        "SkillGapAnalysis": skill_gap_analysis.SkillGapAnalysis,
    }
