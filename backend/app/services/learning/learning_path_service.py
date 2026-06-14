# Status: planned

"""Per task brief §6.2 — LearningPathService walks ``knowledge_edges`` (kind
``prerequisite`` / ``requires``) and the user capability vector to produce a
personalised ordering. Materialised into ``learning_paths`` + ``learning_tasks``.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class LearningPathPlan:
    path_id: UUID
    task_count: int


class LearningPathService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def generate(
        self,
        *,
        user_id: UUID,
        course_id: UUID,
        time_budget_minutes: int | None = None,
    ) -> LearningPathPlan:
        raise NotImplementedError("planned: P1 — task_orchestrator.GenerateLearningPath")
