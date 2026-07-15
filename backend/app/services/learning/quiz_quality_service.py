# Status: real

"""Deterministic quality gate and read models for the only ready WebSec bank.

This service deliberately contains no provider call and does not claim that a
rule-based review is a human review.  It validates durable quiz rows against
the existing WEBSEC-101 knowledge graph and chunks, writes reproducible
reports, and exposes only curated, passed items to course consumers.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from hashlib import sha256
import json
import re
from typing import Any, Iterable
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.education.education_domain import GovernanceAuditEvent
from app.db.models.identity.user import User
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.db.models.learning.quiz_item import QuizItem
from app.db.models.learning.quiz_quality import QuizItemEvidence, QuizQualityReport
from app.db.seeds._constants import COURSE_WEBSEC_CODE, COURSE_WEBSEC_ID
from app.repositories.education.education_domain import EducationRepository
from app.repositories.learning.quizzes import QuizItemRepository, QuizQualityRepository
from app.schemas.quiz_quality import (
    PublishedQuizListDTO,
    QuizBankItemDTO,
    QuizBankListDTO,
    QuizEvidenceDTO,
    QuizQualityFailureSampleDTO,
    QuizQualityItemResultDTO,
    QuizQualityRunDTO,
    QuizQualityStateDTO,
)


VALIDATOR_VERSION = "websec-quiz-quality-v1"
QUALITY_RULES: dict[str, Any] = {
    "validator_version": VALIDATOR_VERSION,
    "near_duplicate_similarity": 0.92,
    "minimum_question_types": 3,
    "maximum_single_type_share": 0.8,
    "required_evidence": "one existing chunk that cites the item knowledge node",
    "publishable_review_status": "curated",
}
_COURSE_TEACHER_ROLES = {"course_teacher", "hybrid"}
_PUBLISHABLE_REVIEW_STATUS = "curated"


class QuizQualityError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class _ItemContext:
    item: QuizItem
    node: KnowledgeNode
    evidences: tuple[tuple[QuizItemEvidence, dict[str, Any]], ...]


class QuizQualityService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.items = QuizItemRepository(session)
        self.quality = QuizQualityRepository(session)
        self.education = EducationRepository(session)

    async def list_teacher_bank(self, *, actor: User) -> QuizBankListDTO:
        await self._require_teacher_scope(actor)
        contexts = await self._load_contexts(COURSE_WEBSEC_ID)
        latest = await self.quality.list_latest_reports([ctx.item.id for ctx in contexts])
        coverage = await self._coverage(COURSE_WEBSEC_ID, contexts)
        return QuizBankListDTO(
            course_id=COURSE_WEBSEC_ID,
            course_code=COURSE_WEBSEC_CODE,
            items=[self._item_dto(ctx, latest.get(ctx.item.id)) for ctx in contexts],
            coverage=coverage,
        )

    async def validate_for_teacher(self, *, actor: User) -> QuizQualityRunDTO:
        await self._require_teacher_scope(actor)
        outcome = await self.validate_course(course_id=COURSE_WEBSEC_ID)
        self.session.add(
            GovernanceAuditEvent(
                id=uuid4(),
                actor_user_id=actor.id,
                action="quiz_quality.validate",
                object_type="course_quiz_bank",
                object_id=COURSE_WEBSEC_ID,
                reason="教师触发 WEBSEC-101 题库确定性质量校验",
                result_status=outcome.result,
                request_id=None,
                metadata_={
                    "validator_version": outcome.validator_version,
                    "input_fingerprint": outcome.input_fingerprint,
                    "failure_sample_count": len(outcome.failure_samples),
                },
            )
        )
        await self.session.flush()
        return outcome

    async def validate_course(self, *, course_id: UUID) -> QuizQualityRunDTO:
        self._require_websec_course(course_id)
        contexts = await self._load_contexts(course_id)
        if not contexts:
            raise QuizQualityError("COURSE_NOT_READY", "Web 安全题库尚未完成初始化。")

        all_nodes = await self._list_course_nodes(course_id)
        input_fingerprint = self._input_fingerprint(course_id=course_id, contexts=contexts)
        failures = self._collect_failures(contexts=contexts, all_nodes=all_nodes)
        coverage = self._coverage_from_nodes(contexts=contexts, all_nodes=all_nodes)
        type_distribution = dict(Counter(ctx.item.type for ctx in contexts))
        item_results: list[QuizQualityItemResultDTO] = []
        failure_samples: list[QuizQualityFailureSampleDTO] = []

        for ctx in contexts:
            codes = sorted(failures[ctx.item.id])
            item_fingerprint = self._item_fingerprint(ctx)
            result = "failed" if codes else "passed"
            existing = await self.quality.get_reproducible_report(
                quiz_item_id=ctx.item.id,
                validator_version=VALIDATOR_VERSION,
                input_fingerprint=input_fingerprint,
            )
            if existing is None:
                existing = await self.quality.create_report(
                    report_id=uuid4(),
                    quiz_item_id=ctx.item.id,
                    validator_version=VALIDATOR_VERSION,
                    input_fingerprint=input_fingerprint,
                    item_fingerprint=item_fingerprint,
                    result=result,
                    failure_codes=codes,
                    report={
                        "rules": QUALITY_RULES,
                        "course_id": str(course_id),
                        "canonical_key": ctx.item.canonical_key,
                        "knowledge_node_id": str(ctx.node.id),
                        "evidence_chunk_ids": [str(evidence.chunk_id) for evidence, _ in ctx.evidences],
                        "coverage": coverage,
                        "type_distribution": type_distribution,
                    },
                )
            state = self._quality_state(existing)
            item_results.append(
                QuizQualityItemResultDTO(
                    quiz_item_id=ctx.item.id,
                    canonical_key=ctx.item.canonical_key,
                    **state.model_dump(),
                )
            )
            if codes:
                failure_samples.append(
                    QuizQualityFailureSampleDTO(
                        quiz_item_id=ctx.item.id,
                        canonical_key=ctx.item.canonical_key,
                        failure_codes=codes,
                    )
                )

        return QuizQualityRunDTO(
            course_id=course_id,
            course_code=COURSE_WEBSEC_CODE,
            validator_version=VALIDATOR_VERSION,
            input_fingerprint=input_fingerprint,
            result="failed" if failure_samples else "passed",
            rules=QUALITY_RULES,
            coverage=coverage,
            type_distribution=type_distribution,
            items=item_results,
            failure_samples=failure_samples[:20],
        )

    async def list_publishable_items(
        self, *, course_id: UUID, canonical_key: str | None = None
    ) -> PublishedQuizListDTO:
        self._require_websec_course(course_id)
        contexts = await self._load_contexts(course_id)
        latest = await self.quality.list_latest_reports([ctx.item.id for ctx in contexts])
        selected = [
            ctx
            for ctx in contexts
            if ctx.item.review_status == _PUBLISHABLE_REVIEW_STATUS
            and (report := latest.get(ctx.item.id)) is not None
            and report.result == "passed"
            and report.validator_version == VALIDATOR_VERSION
        ]
        if canonical_key is not None:
            requested = next(
                (ctx for ctx in contexts if ctx.item.canonical_key == canonical_key), None
            )
            if requested is None:
                raise QuizQualityError("QUESTION_NOT_FOUND", "题目不存在。", 404)
            if requested not in selected:
                raise QuizQualityError(
                    "QUESTION_STATUS_NOT_PUBLISHABLE",
                    "题目尚未通过质量校验或未处于可发布 curated 状态。",
                )
            selected = [requested]
        return PublishedQuizListDTO(
            course_id=course_id,
            course_code=COURSE_WEBSEC_CODE,
            items=[self._item_dto(ctx, latest.get(ctx.item.id)) for ctx in selected],
        )

    async def _load_contexts(self, course_id: UUID) -> list[_ItemContext]:
        rows = await self.items.list_for_course(course_id)
        item_ids = [item.id for item, _ in rows]
        evidence_rows = await self.quality.list_evidence_for_items(item_ids)
        evidences_by_item: dict[UUID, list[tuple[QuizItemEvidence, dict[str, Any]]]] = defaultdict(list)
        for evidence, chunk in evidence_rows:
            metadata = chunk.metadata_ if isinstance(chunk.metadata_, dict) else {}
            evidences_by_item[evidence.quiz_item_id].append((evidence, metadata))
        return [
            _ItemContext(
                item=item,
                node=node,
                evidences=tuple(evidences_by_item.get(item.id, [])),
            )
            for item, node in rows
        ]

    async def _list_course_nodes(self, course_id: UUID) -> list[KnowledgeNode]:
        result = await self.session.execute(
            select(KnowledgeNode)
            .where(KnowledgeNode.course_id == course_id)
            .order_by(KnowledgeNode.id)
        )
        return list(result.scalars())

    async def _coverage(self, course_id: UUID, contexts: list[_ItemContext]) -> dict[str, Any]:
        return self._coverage_from_nodes(contexts=contexts, all_nodes=await self._list_course_nodes(course_id))

    @staticmethod
    def _coverage_from_nodes(
        *, contexts: Iterable[_ItemContext], all_nodes: Iterable[KnowledgeNode]
    ) -> dict[str, Any]:
        contexts_list = list(contexts)
        node_ids = {node.id for node in all_nodes}
        covered = {ctx.node.id for ctx in contexts_list}
        missing = sorted(str(node_id) for node_id in node_ids - covered)
        return {
            "required_knowledge_point_count": len(node_ids),
            "covered_knowledge_point_count": len(covered & node_ids),
            "missing_knowledge_node_ids": missing,
            "all_knowledge_points_covered": not missing,
        }

    def _collect_failures(
        self, *, contexts: list[_ItemContext], all_nodes: list[KnowledgeNode]
    ) -> dict[UUID, set[str]]:
        failures: dict[UUID, set[str]] = defaultdict(set)
        normalized_questions: dict[str, list[_ItemContext]] = defaultdict(list)
        for ctx in contexts:
            normalized_questions[self._normalize(ctx.item.question)].append(ctx)
            self._validate_item(ctx, failures[ctx.item.id])

        for duplicates in normalized_questions.values():
            if len(duplicates) > 1:
                for ctx in duplicates:
                    failures[ctx.item.id].add("QUESTION_DUPLICATE")
        for index, current in enumerate(contexts):
            current_text = self._normalize(current.item.question)
            for candidate in contexts[index + 1 :]:
                similarity = SequenceMatcher(
                    None, current_text, self._normalize(candidate.item.question)
                ).ratio()
                if similarity >= float(QUALITY_RULES["near_duplicate_similarity"]):
                    failures[current.item.id].add("QUESTION_NEAR_DUPLICATE")
                    failures[candidate.item.id].add("QUESTION_NEAR_DUPLICATE")

        coverage = self._coverage_from_nodes(contexts=contexts, all_nodes=all_nodes)
        if not coverage["all_knowledge_points_covered"]:
            for ctx in contexts:
                failures[ctx.item.id].add("KNOWLEDGE_POINT_UNCOVERED")
        type_counts = Counter(ctx.item.type for ctx in contexts)
        type_count = len(type_counts)
        max_share = max(type_counts.values(), default=0) / max(len(contexts), 1)
        if (
            type_count < int(QUALITY_RULES["minimum_question_types"])
            or max_share > float(QUALITY_RULES["maximum_single_type_share"])
        ):
            for ctx in contexts:
                failures[ctx.item.id].add("QUESTION_TYPE_DISTRIBUTION_INVALID")
        return failures

    def _validate_item(self, ctx: _ItemContext, failures: set[str]) -> None:
        item = ctx.item
        options = self._options(item.options)
        if not item.canonical_key.strip():
            failures.add("QUESTION_CANONICAL_KEY_MISSING")
        if not item.explanation.strip():
            failures.add("QUESTION_EXPLANATION_MISSING")
        if not ctx.evidences:
            failures.add("QUESTION_EVIDENCE_MISSING")
        else:
            matching_evidence = any(
                str(ctx.node.id) in metadata.get("kp_ids", [])
                for _, metadata in ctx.evidences
            )
            if not matching_evidence:
                failures.add("QUESTION_EVIDENCE_KP_MISMATCH")
        if item.type in {"single_choice", "multi_choice"}:
            if len(options) < 2:
                failures.add("QUESTION_OPTIONS_INSUFFICIENT")
            normalized_options = [self._normalize(option) for option in options]
            if len(set(normalized_options)) != len(normalized_options):
                failures.add("QUESTION_AMBIGUOUS_OPTIONS")
            answers = (
                [item.answer.strip()]
                if item.type == "single_choice"
                else [part.strip() for part in item.answer.split(";") if part.strip()]
            )
            if not answers or any(self._normalize(answer) not in normalized_options for answer in answers):
                failures.add("QUESTION_ANSWER_OPTION_CONFLICT")
            if item.type == "multi_choice" and len(answers) < 2:
                failures.add("QUESTION_MULTI_ANSWER_AMBIGUOUS")
        elif not item.answer.strip():
            failures.add("QUESTION_ANSWER_MISSING")

    @staticmethod
    def _options(value: object) -> list[str]:
        return [entry.strip() for entry in value if isinstance(entry, str) and entry.strip()] if isinstance(value, list) else []

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"\s+", "", value).lower()

    def _input_fingerprint(self, *, course_id: UUID, contexts: list[_ItemContext]) -> str:
        payload = {
            "course_id": str(course_id),
            "rules": QUALITY_RULES,
            "items": [self._fingerprint_payload(ctx) for ctx in contexts],
        }
        return self._fingerprint(payload)

    def _item_fingerprint(self, ctx: _ItemContext) -> str:
        return self._fingerprint(self._fingerprint_payload(ctx))

    def _fingerprint_payload(self, ctx: _ItemContext) -> dict[str, Any]:
        return {
            "canonical_key": ctx.item.canonical_key,
            "content_version": ctx.item.content_version,
            "knowledge_node_id": str(ctx.node.id),
            "type": ctx.item.type,
            "question": ctx.item.question,
            "options": self._options(ctx.item.options),
            "answer": ctx.item.answer,
            "explanation": ctx.item.explanation,
            "difficulty": ctx.item.difficulty,
            "review_status": ctx.item.review_status,
            "source_status": ctx.item.source_status,
            "evidence_chunk_ids": [str(evidence.chunk_id) for evidence, _ in ctx.evidences],
        }

    @staticmethod
    def _fingerprint(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _quality_state(report: QuizQualityReport | None) -> QuizQualityStateDTO:
        if report is None:
            return QuizQualityStateDTO(
                validator_version=VALIDATOR_VERSION,
                input_fingerprint="",
                result="pending",
                failure_codes=[],
                reviewed_at=None,
            )
        return QuizQualityStateDTO(
            validator_version=report.validator_version,
            input_fingerprint=report.input_fingerprint,
            result=report.result,  # type: ignore[arg-type]
            failure_codes=list(report.failure_codes or []),
            reviewed_at=report.reviewed_at,
        )

    def _item_dto(self, ctx: _ItemContext, report: QuizQualityReport | None) -> QuizBankItemDTO:
        return QuizBankItemDTO(
            id=ctx.item.id,
            canonical_key=ctx.item.canonical_key,
            content_version=ctx.item.content_version,
            knowledge_node_id=ctx.node.id,
            knowledge_node_name=ctx.node.name,
            type=ctx.item.type,  # type: ignore[arg-type]
            question=ctx.item.question,
            options=self._options(ctx.item.options),
            answer=ctx.item.answer,
            explanation=ctx.item.explanation,
            difficulty=ctx.item.difficulty,
            review_status=ctx.item.review_status,  # type: ignore[arg-type]
            source_status=ctx.item.source_status,  # type: ignore[arg-type]
            evidence=[
                QuizEvidenceDTO(chunk_id=evidence.chunk_id, citation_label=evidence.citation_label)
                for evidence, _ in ctx.evidences
            ],
            quality=self._quality_state(report),
        )

    async def _require_teacher_scope(self, actor: User) -> None:
        if actor.role not in _COURSE_TEACHER_ROLES:
            raise QuizQualityError(
                "TEACHER_ROLE_REQUIRED", "当前账号不具备 Web 安全题库管理权限。", 403
            )
        assignment = await self.education.get_course_teacher_assignment(
            course_id=COURSE_WEBSEC_ID, teacher_id=actor.id
        )
        if assignment is None:
            raise QuizQualityError("COURSE_SCOPE_DENIED", "当前教师未获 WEBSEC-101 课程授权。", 403)

    @staticmethod
    def _require_websec_course(course_id: UUID) -> None:
        if course_id != COURSE_WEBSEC_ID:
            raise QuizQualityError("COURSE_SCOPE_DENIED", "该题库只服务 WEBSEC-101。", 403)


__all__ = ["QUALITY_RULES", "VALIDATOR_VERSION", "QuizQualityError", "QuizQualityService"]
