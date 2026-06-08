# Status: real

"""Repository layer package.

v2 repositories are grouped into six sub-packages
(``identity`` / ``knowledge`` / ``learning`` / ``agent`` / ``resource`` /
``storage``) per task brief §5. Each class is exported here so callers can
``from app.repositories import DocumentRepository`` without remembering the
sub-package layout.

The legacy ``research_repository.ResearchRepository`` (挑战杯 mock data
backing the existing ``/api/v1/research/*`` endpoints) is left in place
untouched — see CLAUDE.md §10 boundaries.
"""

from app.repositories.agent.agent_runs import AgentRunRepository
from app.repositories.agent.agent_skills import AgentSkillRepository
from app.repositories.agent.agents import AgentRepository
from app.repositories.identity.capabilities import UserCapabilityRepository
from app.repositories.identity.profiles import UserProfileRepository
from app.repositories.identity.users import UserRepository
from app.repositories.knowledge.chunks import ChunkRepository
from app.repositories.knowledge.courses import CourseRepository
from app.repositories.knowledge.document_assets import DocumentAssetRepository
from app.repositories.knowledge.documents import DocumentRepository
from app.repositories.knowledge.knowledge_graph import KnowledgeGraphRepository
from app.repositories.learning.learning_events import LearningEventRepository
from app.repositories.learning.learning_paths import LearningPathRepository
from app.repositories.learning.quizzes import QuizAttemptRepository, QuizItemRepository
from app.repositories.resource.generated_resources import GeneratedResourceRepository
from app.repositories.storage.storage_objects import StorageObjectRepository

__all__ = [
    # identity
    "UserRepository",
    "UserProfileRepository",
    "UserCapabilityRepository",
    # knowledge
    "DocumentRepository",
    "DocumentAssetRepository",
    "ChunkRepository",
    "CourseRepository",
    "KnowledgeGraphRepository",
    # learning
    "LearningEventRepository",
    "LearningPathRepository",
    "QuizItemRepository",
    "QuizAttemptRepository",
    # agent
    "AgentRepository",
    "AgentSkillRepository",
    "AgentRunRepository",
    # resource
    "GeneratedResourceRepository",
    # storage
    "StorageObjectRepository",
]
