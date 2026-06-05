# Status: [planned]

from app.agents.base import AgentCapability, BaseAgent
from app.agents.outcome_evaluator.skills import evaluate_submission, quality_check, run_assessment, update_capability


class OutcomeEvaluatorAgent(BaseAgent):
    name = "outcome_evaluator"
    role_description = "Evaluate submissions, update capabilities, and enforce quality gates."
    capability_vector = AgentCapability(eval=1.0, planning=0.4, doc=0.4)
    tools = ["rag.retrieve", "llm.xfyun"]
    risk_level = "high"
    skills = {
        "EvaluateSubmission": evaluate_submission.EvaluateSubmission,
        "RunAssessment": run_assessment.RunAssessment,
        "QualityCheck": quality_check.QualityCheck,
        "UpdateCapability": update_capability.UpdateCapability,
    }
