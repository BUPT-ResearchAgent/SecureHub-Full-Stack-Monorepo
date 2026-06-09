# Status: planned

"""Service layer package.

v2 services are grouped per task brief §6 into five sub-packages
(``knowledge`` / ``learning`` / ``agent`` / ``resource`` / ``storage``). Each
class signature is fixed; implementation bodies raise ``NotImplementedError``
until the matching P0 / P1 milestone lands.

The legacy ``research_service.ResearchService`` (挑战杯 mock backing
``/api/v1/research/*``) is left untouched — see CLAUDE.md §10.
"""

from app.services.agent.agent_registry_service import AgentRegistryService
from app.services.agent.agent_run_service import AgentRunService
from app.services.agent.skill_registry_service import SkillRegistryService
from app.services.knowledge.chunking_service import ChunkingService
from app.services.knowledge.embedding_service import EmbeddingService
from app.services.knowledge.evidence_service import EvidenceService
from app.services.knowledge.ingestion_service import IngestionService
from app.services.knowledge.retrieval_service import RetrievalService
from app.services.learning.assessment_service import AssessmentService
from app.services.learning.capability_service import CapabilityService
from app.services.learning.learning_path_service import LearningPathService
from app.services.learning.profile_service import ProfileService
from app.services.resource.artifact_storage_service import ArtifactStorageService
from app.services.resource.resource_generation_service import ResourceGenerationService
from app.services.storage.storage_service import StorageService

__all__ = [
    # knowledge
    "IngestionService",
    "ChunkingService",
    "EmbeddingService",
    "RetrievalService",
    "EvidenceService",
    # learning
    "ProfileService",
    "CapabilityService",
    "LearningPathService",
    "AssessmentService",
    # agent
    "AgentRegistryService",
    "AgentRunService",
    "SkillRegistryService",
    # resource
    "ResourceGenerationService",
    "ArtifactStorageService",
    # storage
    "StorageService",
]
