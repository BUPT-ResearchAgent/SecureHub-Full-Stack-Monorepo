# Status: real

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.db.models.learning.quiz_attempt import QuizAttempt
from app.db.models.learning.quiz_item import QuizItem
from app.db.models.learning.quiz_quality import QuizItemEvidence, QuizQualityReport
from app.db.models.knowledge.chunk import Chunk
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.repositories.base import UUIDPKRepository


class QuizItemRepository(UUIDPKRepository[QuizItem]):
    model = QuizItem

    async def list_by_kp(
        self, kp_id: UUID, *, limit: int = 50
    ) -> Sequence[QuizItem]:
        stmt = (
            select(QuizItem)
            .where(QuizItem.kp_id == kp_id)
            .order_by(QuizItem.difficulty, QuizItem.created_at)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(
        self,
        *,
        item_id: UUID,
        kp_id: UUID,
        canonical_key: str,
        type: str,
        question: str,
        answer: str,
        explanation: str,
        difficulty: int,
        review_status: str,
        source_status: str,
        content_version: int = 1,
        options: dict[str, Any] | list[Any] | None = None,
        generated_by_skill: UUID | None = None,
    ) -> QuizItem:
        row = QuizItem(
            id=item_id,
            kp_id=kp_id,
            canonical_key=canonical_key,
            content_version=content_version,
            type=type,
            question=question,
            options=options,
            answer=answer,
            explanation=explanation,
            difficulty=difficulty,
            review_status=review_status,
            source_status=source_status,
            generated_by_skill=generated_by_skill,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_for_course(
        self, course_id: UUID
    ) -> Sequence[tuple[QuizItem, KnowledgeNode]]:
        result = await self.session.execute(
            select(QuizItem, KnowledgeNode)
            .join(KnowledgeNode, KnowledgeNode.id == QuizItem.kp_id)
            .where(KnowledgeNode.course_id == course_id)
            .order_by(QuizItem.canonical_key)
        )
        return result.all()

    async def get_for_course_by_canonical_key(
        self, *, course_id: UUID, canonical_key: str
    ) -> tuple[QuizItem, KnowledgeNode] | None:
        result = await self.session.execute(
            select(QuizItem, KnowledgeNode)
            .join(KnowledgeNode, KnowledgeNode.id == QuizItem.kp_id)
            .where(
                KnowledgeNode.course_id == course_id,
                QuizItem.canonical_key == canonical_key,
            )
        )
        return result.one_or_none()


class QuizQualityRepository:
    """Persistent access for evidence bindings and deterministic quality reports."""

    def __init__(self, session: Any) -> None:
        self.session = session

    async def list_evidence_for_items(
        self, item_ids: Sequence[UUID]
    ) -> Sequence[tuple[QuizItemEvidence, Chunk]]:
        if not item_ids:
            return []
        result = await self.session.execute(
            select(QuizItemEvidence, Chunk)
            .join(Chunk, Chunk.id == QuizItemEvidence.chunk_id)
            .where(QuizItemEvidence.quiz_item_id.in_(item_ids))
            .order_by(QuizItemEvidence.quiz_item_id, QuizItemEvidence.chunk_id)
        )
        return result.all()

    async def get_evidence(
        self, *, quiz_item_id: UUID, chunk_id: UUID
    ) -> QuizItemEvidence | None:
        result = await self.session.execute(
            select(QuizItemEvidence).where(
                QuizItemEvidence.quiz_item_id == quiz_item_id,
                QuizItemEvidence.chunk_id == chunk_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_evidence(
        self,
        *,
        evidence_id: UUID,
        quiz_item_id: UUID,
        chunk_id: UUID,
        citation_label: str | None,
    ) -> QuizItemEvidence:
        row = QuizItemEvidence(
            id=evidence_id,
            quiz_item_id=quiz_item_id,
            chunk_id=chunk_id,
            citation_label=citation_label,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_reproducible_report(
        self,
        *,
        quiz_item_id: UUID,
        validator_version: str,
        input_fingerprint: str,
    ) -> QuizQualityReport | None:
        result = await self.session.execute(
            select(QuizQualityReport).where(
                QuizQualityReport.quiz_item_id == quiz_item_id,
                QuizQualityReport.validator_version == validator_version,
                QuizQualityReport.input_fingerprint == input_fingerprint,
            )
        )
        return result.scalar_one_or_none()

    async def list_latest_reports(self, item_ids: Sequence[UUID]) -> dict[UUID, QuizQualityReport]:
        if not item_ids:
            return {}
        result = await self.session.execute(
            select(QuizQualityReport)
            .where(QuizQualityReport.quiz_item_id.in_(item_ids))
            .order_by(QuizQualityReport.quiz_item_id, QuizQualityReport.reviewed_at.desc())
        )
        latest: dict[UUID, QuizQualityReport] = {}
        for row in result.scalars():
            latest.setdefault(row.quiz_item_id, row)
        return latest

    async def create_report(
        self,
        *,
        report_id: UUID,
        quiz_item_id: UUID,
        validator_version: str,
        input_fingerprint: str,
        item_fingerprint: str,
        result: str,
        failure_codes: list[str],
        report: dict[str, Any],
    ) -> QuizQualityReport:
        row = QuizQualityReport(
            id=report_id,
            quiz_item_id=quiz_item_id,
            validator_version=validator_version,
            input_fingerprint=input_fingerprint,
            item_fingerprint=item_fingerprint,
            result=result,
            failure_codes=failure_codes,
            report=report,
            reviewed_by=None,
        )
        self.session.add(row)
        await self.session.flush()
        return row


class QuizAttemptRepository(UUIDPKRepository[QuizAttempt]):
    model = QuizAttempt

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        quiz_item_id: UUID | None = None,
        limit: int = 100,
    ) -> Sequence[QuizAttempt]:
        stmt = select(QuizAttempt).where(QuizAttempt.user_id == user_id)
        if quiz_item_id is not None:
            stmt = stmt.where(QuizAttempt.quiz_item_id == quiz_item_id)
        stmt = stmt.order_by(QuizAttempt.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(
        self,
        *,
        attempt_id: UUID,
        quiz_item_id: UUID,
        user_id: UUID,
        submitted_answer: dict[str, Any],
        is_correct: bool | None = None,
        score: float | None = None,
        feedback: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> QuizAttempt:
        row = QuizAttempt(
            id=attempt_id,
            quiz_item_id=quiz_item_id,
            user_id=user_id,
            submitted_answer=submitted_answer,
            is_correct=is_correct,
            score=score,
            feedback=feedback,
            metadata_=metadata or {},
        )
        self.session.add(row)
        await self.session.flush()
        return row
