# Status: [planned]

"""Data-layer v2 ORM aggregator.

The models are grouped into six sub-packages (``identity`` / ``knowledge`` /
``learning`` / ``agent`` / ``resource`` / ``storage``). This module re-exports
every P0/P1/P2 table at the package root, plus backward-compatible aliases for
v1 names (``KnowledgePoint`` → :class:`KnowledgeNode`,
``KpPrerequisite`` → :class:`KnowledgeEdge`) so older callers keep importing
``from app.db.models import KnowledgePoint`` without churn.
"""

# A. Identity & profile
from app.db.models.identity.user import User
from app.db.models.identity.user_capability import UserCapability
from app.db.models.identity.user_profile import UserProfile

# B. Unified knowledge asset layer
from app.db.models.knowledge.chunk import Chunk
from app.db.models.knowledge.course import Course
from app.db.models.knowledge.document import Document
from app.db.models.knowledge.document_asset import DocumentAsset
from app.db.models.knowledge.knowledge_edge import KnowledgeEdge
from app.db.models.knowledge.knowledge_node import KnowledgeNode

# C. Learning loop
from app.db.models.learning.learning_event import LearningEvent
from app.db.models.learning.learning_path import LearningPath
from app.db.models.learning.learning_task import LearningTask
from app.db.models.learning.quiz_attempt import QuizAttempt
from app.db.models.learning.quiz_item import QuizItem

# D. Multi-agent registry & runs
from app.db.models.agent.agent import Agent
from app.db.models.agent.agent_message import AgentMessage
from app.db.models.agent.agent_run import AgentRun
from app.db.models.agent.agent_skill import AgentSkill

# E. Generated resources & storage
from app.db.models.resource.generated_resource import GeneratedResource
from app.db.models.resource.resource_version import ResourceVersion
from app.db.models.storage.storage_object import StorageObject

# v1 compatibility aliases — keep ``from app.db.models import KnowledgePoint``
# resolving for any unmigrated caller (loaders, repos, tests).
KnowledgePoint = KnowledgeNode
KpPrerequisite = KnowledgeEdge

__all__ = [
    # P0 — identity
    "User",
    "UserProfile",
    "UserCapability",
    # P0 — knowledge
    "Course",
    "Document",
    "DocumentAsset",
    "Chunk",
    "KnowledgeNode",
    "KnowledgeEdge",
    # P0 — learning
    "LearningEvent",
    "QuizItem",
    "QuizAttempt",
    # P0 — agent
    "Agent",
    "AgentSkill",
    "AgentRun",
    # P0 — resource & storage
    "GeneratedResource",
    "StorageObject",
    # P1 / P2 — extensions
    "LearningPath",
    "LearningTask",
    "AgentMessage",
    "ResourceVersion",
    # v1 backward-compatibility aliases
    "KnowledgePoint",
    "KpPrerequisite",
]
