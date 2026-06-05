# Status: [planned]

from app.agents.base import AgentCapability, BaseAgent
from app.agents.policy_interpreter.skills import compliance_check, interpret_policy


class PolicyInterpreterAgent(BaseAgent):
    name = "policy_interpreter"
    role_description = "Interpret policy text and provide compliance guidance with evidence."
    capability_vector = AgentCapability(policy=1.0, topic=0.4, doc=0.3, eval=0.5)
    tools = ["rag.retrieve", "llm.xfyun"]
    risk_level = "medium"
    skills = {
        "InterpretPolicy": interpret_policy.InterpretPolicy,
        "ComplianceCheck": compliance_check.ComplianceCheck,
    }
