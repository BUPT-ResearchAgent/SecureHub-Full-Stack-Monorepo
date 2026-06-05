# Status: [planned]

from uuid import UUID

from pydantic import BaseModel


class KnowledgePointDraft(BaseModel):
    name: str
    description: str
    level: int
    prereq_names: list[str]


async def extract_knowledge_points(course_id: UUID, source_document_ids: list[UUID]) -> list[KnowledgePointDraft]:
    raise NotImplementedError("TODO: extract knowledge points and prerequisite edges")
