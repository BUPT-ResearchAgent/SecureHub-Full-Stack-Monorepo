# Status: [planned]

from app.agents.base import AgentCapability, BaseAgent
from app.agents.task_orchestrator.skills import decompose_wbs, generate_learning_path


class TaskOrchestratorAgent(BaseAgent):
    name = "task_orchestrator"
    role_description = "Generate learning paths and executable task decomposition."
    capability_vector = AgentCapability(task=1.0, planning=0.7)
    tools = ["rag.retrieve", "llm.xfyun"]
    risk_level = "low"
    skills = {
        "GenerateLearningPath": generate_learning_path.GenerateLearningPath,
        "DecomposeWBS": decompose_wbs.DecomposeWBS,
    }
