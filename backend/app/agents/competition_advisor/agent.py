# Status: [planned]

from app.agents.base import AgentCapability, BaseAgent
from app.agents.competition_advisor.skills import generate_competition_plan, generate_quiz, recommend_competition


class CompetitionAdvisorAgent(BaseAgent):
    name = "competition_advisor"
    role_description = "Recommend competitions and generate evidence-linked practice quizzes."
    capability_vector = AgentCapability(competition=1.0, task=0.4, eval=0.4)
    tools = ["rag.retrieve", "llm.xfyun"]
    risk_level = "medium"
    skills = {
        "RecommendCompetition": recommend_competition.RecommendCompetition,
        "GenerateQuiz": generate_quiz.GenerateQuiz,
        "GenerateCompetitionPlan": generate_competition_plan.GenerateCompetitionPlan,
    }
