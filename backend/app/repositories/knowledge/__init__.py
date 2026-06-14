# Status: real

from app.repositories.knowledge.chunks import ChunkRepository
from app.repositories.knowledge.courses import CourseRepository
from app.repositories.knowledge.document_assets import DocumentAssetRepository
from app.repositories.knowledge.documents import DocumentRepository
from app.repositories.knowledge.knowledge_graph import KnowledgeGraphRepository

__all__ = [
    "ChunkRepository",
    "CourseRepository",
    "DocumentAssetRepository",
    "DocumentRepository",
    "KnowledgeGraphRepository",
]
