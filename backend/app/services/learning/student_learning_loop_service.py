# Status: real

"""Student-owned path replan and resource feedback orchestration.

This service deliberately composes the existing course, path, resource,
artifact and workflow authorities.  It never computes a result from browser
state, never overwrites a historical path, and never turns an unfinished
resource retry into a successful version.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Iterable
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.education.education_domain import CourseEnrollment
from app.db.models.identity.user import User
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.db.models.learning.learning_event import LearningEvent
from app.db.models.learning.learning_path import LearningPath
from app.db.models.learning.learning_replan import (
    CourseResourceRecommendation,
    LearningPathDecision,
    LearningPathReplanCandidate,
    LearningPathVersion,
)
from app.db.models.learning.learning_task import LearningTask
from app.db.models.learning.quiz_attempt import QuizAttempt
from app.db.models.learning.quiz_item import QuizItem
from app.db.models.resource.generated_resource import GeneratedResource
from app.db.models.resource.resource_feedback import ResourceFeedback
from app.db.models.resource.resource_version import ResourceVersion
from app.db.models.workflow_runtime import WorkflowRun
from app.schemas.student_learning_loop import (
    PathReplanCandidateDTO,
    PathTaskChangeDTO,
    PathVersionDTO,
    ResourceFeedbackDTO,
    ResourceLineageDTO,
    ResourceLineageVersionDTO,
    ResourceRecommendationDTO,
    StudentLearningLoopDTO,
)


_ACCESSIBLE_RESOURCE_STATUSES = ("ready", "active")
_TERMINAL_WORKFLOW_STATUSES = {"succeeded", "failed", "blocked", "cancelled"}
_FEEDBACK_KINDS = {
    "too_difficult": "内容难度偏高",
    "too_shallow": "内容深度不足",
    "missing_example": "缺少防御性示例",
    "want_diagram": "希望增加图解",
    "want_practice": "希望增加实操",
}


class StudentLearningLoopError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 403) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class StudentLearningLoopService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def overview(self, *, actor: User, course_id: UUID) -> StudentLearningLoopDTO:
        await self._require_student_enrollment(actor, course_id)
        await self.reconcile_feedback(actor=actor, course_id=course_id)

        versions = list(
            (
                await self.session.execute(
                    select(LearningPathVersion)
                    .where(
                        LearningPathVersion.user_id == actor.id,
                        LearningPathVersion.course_id == course_id,
                    )
                    .order_by(LearningPathVersion.version_no.desc())
                )
            ).scalars()
        )
        candidates = list(
            (
                await self.session.execute(
                    select(LearningPathReplanCandidate)
                    .where(
                        LearningPathReplanCandidate.student_id == actor.id,
                        LearningPathReplanCandidate.course_id == course_id,
                    )
                    .order_by(LearningPathReplanCandidate.updated_at.desc())
                    .limit(12)
                )
            ).scalars()
        )
        recommendations = await self._recommendations(actor.id, course_id)
        feedback = list(
            (
                await self.session.execute(
                    select(ResourceFeedback)
                    .where(ResourceFeedback.student_id == actor.id, ResourceFeedback.course_id == course_id)
                    .order_by(ResourceFeedback.updated_at.desc())
                    .limit(24)
                )
            ).scalars()
        )
        return StudentLearningLoopDTO(
            course_id=course_id,
            candidates=[await self._candidate_dto(candidate) for candidate in candidates],
            path_versions=[self._path_version_dto(version) for version in versions],
            recommendations=recommendations,
            feedback=[self.feedback_dto(item) for item in feedback],
            resource_lineages=await self._resource_lineages(actor.id, course_id),
        )

    async def create_candidate(
        self,
        *,
        actor: User,
        course_id: UUID,
        trigger_event_id: UUID | None = None,
        assessment_workflow_run_id: UUID | None = None,
    ) -> PathReplanCandidateDTO:
        await self._require_student_enrollment(actor, course_id)
        path = await self._active_path(actor.id, course_id)
        source_version = await self._ensure_version_for_path(path)
        event, workflow = await self._resolve_trigger(
            actor_id=actor.id,
            course_id=course_id,
            trigger_event_id=trigger_event_id,
            assessment_workflow_run_id=assessment_workflow_run_id,
        )
        task_rows = await self._path_tasks(path.id)
        focus_node = await self._focus_node(
            actor_id=actor.id,
            course_id=course_id,
            trigger_event=event,
            tasks=task_rows,
        )
        average_score = await self._node_average_score(actor.id, focus_node.id)
        reason_code, reason_text, expected_minutes, supplemental = self._replan_reason(
            focus_node=focus_node,
            average_score=average_score,
        )
        proposed_tasks = self._proposed_tasks(task_rows, focus_node, supplemental, expected_minutes)
        plan = await self._recommendation_plan(actor.id, course_id, focus_node.id, reason_code)
        fingerprint_source = "|".join(
            (
                str(source_version.id),
                str(event.id) if event is not None else "",
                str(workflow.id) if workflow is not None else "",
                str(focus_node.id),
                reason_code,
                f"{average_score:.4f}" if average_score is not None else "none",
            )
        )
        fingerprint = sha256(fingerprint_source.encode("utf-8")).hexdigest()
        existing = await self.session.scalar(
            select(LearningPathReplanCandidate).where(
                LearningPathReplanCandidate.student_id == actor.id,
                LearningPathReplanCandidate.course_id == course_id,
                LearningPathReplanCandidate.input_fingerprint == fingerprint,
            )
        )
        if existing is not None:
            return await self._candidate_dto(existing)

        candidate = LearningPathReplanCandidate(
            id=uuid4(),
            student_id=actor.id,
            course_id=course_id,
            source_path_version_id=source_version.id,
            trigger_event_id=event.id if event is not None else None,
            trigger_workflow_run_id=workflow.id if workflow is not None else None,
            affected_kp_id=focus_node.id,
            status="pending",
            reason_code=reason_code,
            reason_text=reason_text,
            expected_minutes=expected_minutes,
            proposed_task_snapshot=proposed_tasks,
            recommendation_plan=plan,
            input_fingerprint=fingerprint,
            metadata_={
                "average_score": average_score,
                "trigger_kind": "assessment" if workflow is not None else "learning_event",
                "source_boundary": self._candidate_boundary(event),
            },
        )
        self.session.add(candidate)
        await self.session.flush()
        return await self._candidate_dto(candidate)

    async def decide_candidate(
        self,
        *,
        actor: User,
        course_id: UUID,
        candidate_id: UUID,
        decision: str,
        reason: str | None = None,
    ) -> PathReplanCandidateDTO:
        await self._require_student_enrollment(actor, course_id)
        candidate = await self._candidate_for_actor(candidate_id, actor.id, course_id)
        safe_reason = _clean_optional_text(reason, maximum=400)
        if decision == "defer":
            if candidate.status not in {"pending", "deferred"}:
                raise StudentLearningLoopError(
                    "REPLAN_DECISION_UNAVAILABLE",
                    "当前候选已形成路径结果，不能再次暂缓。",
                    409,
                )
            candidate.status = "deferred"
            self.session.add(
                LearningPathDecision(
                    id=uuid4(),
                    candidate_id=candidate.id,
                    student_id=actor.id,
                    decision="defer",
                    source_path_version_id=candidate.source_path_version_id,
                    reason=safe_reason,
                    metadata_={"candidate_status_before": "pending"},
                )
            )
            await self.session.flush()
            return await self._candidate_dto(candidate)

        if decision == "accept":
            if candidate.status not in {"pending", "deferred"}:
                raise StudentLearningLoopError(
                    "REPLAN_DECISION_UNAVAILABLE",
                    "当前候选已经被处理，不能重复采纳。",
                    409,
                )
            current = await self._active_path_version(actor.id, course_id)
            if current is None or current.id != candidate.source_path_version_id:
                candidate.status = "expired"
                await self.session.flush()
                raise StudentLearningLoopError(
                    "REPLAN_CANDIDATE_STALE",
                    "当前学习路径已发生变化，请重新计算候选后再决定。",
                    409,
                )
            new_version = await self._materialize_path_version(
                actor_id=actor.id,
                course_id=course_id,
                source_version=current,
                task_snapshot=list(candidate.proposed_task_snapshot or []),
                kind="replan",
                summary="学生采纳重规划候选；历史进度保留在上一版本中。",
                diff={
                    "candidate_id": str(candidate.id),
                    "reason_code": candidate.reason_code,
                    "expected_minutes": candidate.expected_minutes,
                    "added_tasks": [
                        task.get("title")
                        for task in list(candidate.proposed_task_snapshot or [])
                        if task.get("action") == "added"
                    ],
                },
                trigger_event_id=candidate.trigger_event_id,
                trigger_workflow_run_id=candidate.trigger_workflow_run_id,
            )
            candidate.status = "accepted"
            candidate.accepted_path_version_id = new_version.id
            self.session.add(
                LearningPathDecision(
                    id=uuid4(),
                    candidate_id=candidate.id,
                    student_id=actor.id,
                    decision="accept",
                    source_path_version_id=current.id,
                    resulting_path_version_id=new_version.id,
                    reason=safe_reason,
                    metadata_={"recommendation_count": 0},
                )
            )
            recommendation_count = await self._sync_candidate_recommendations(
                actor_id=actor.id,
                course_id=course_id,
                candidate=candidate,
                path_version=new_version,
            )
            decision_row = await self.session.scalar(
                select(LearningPathDecision)
                .where(
                    LearningPathDecision.candidate_id == candidate.id,
                    LearningPathDecision.decision == "accept",
                )
                .order_by(LearningPathDecision.created_at.desc())
                .limit(1)
            )
            if decision_row is not None:
                decision_row.metadata_ = {"recommendation_count": recommendation_count}
            await self.session.flush()
            return await self._candidate_dto(candidate)

        if decision == "revert":
            if candidate.status != "accepted" or candidate.accepted_path_version_id is None:
                raise StudentLearningLoopError(
                    "REPLAN_REVERT_UNAVAILABLE",
                    "只有已采纳且仍可追溯的候选路径可以回退。",
                    409,
                )
            current = await self._active_path_version(actor.id, course_id)
            if current is None or current.id != candidate.accepted_path_version_id:
                raise StudentLearningLoopError(
                    "REPLAN_REVERT_STALE",
                    "当前路径已经继续演进，不能覆盖为旧版本；请先查看版本记录。",
                    409,
                )
            source = await self.session.get(LearningPathVersion, candidate.source_path_version_id)
            if source is None or source.user_id != actor.id or source.course_id != course_id:
                raise StudentLearningLoopError("REPLAN_SOURCE_UNAVAILABLE", "原路径版本不可用。", 409)
            reverted = await self._materialize_path_version(
                actor_id=actor.id,
                course_id=course_id,
                source_version=current,
                task_snapshot=list(source.task_snapshot or []),
                kind="revert",
                summary=f"学生显式回退到 v{source.version_no}；之前的路径和完成记录仍可查看。",
                diff={
                    "reverted_candidate_id": str(candidate.id),
                    "restored_version_no": source.version_no,
                },
                trigger_event_id=candidate.trigger_event_id,
                trigger_workflow_run_id=candidate.trigger_workflow_run_id,
            )
            candidate.status = "reverted"
            self.session.add(
                LearningPathDecision(
                    id=uuid4(),
                    candidate_id=candidate.id,
                    student_id=actor.id,
                    decision="revert",
                    source_path_version_id=current.id,
                    resulting_path_version_id=reverted.id,
                    reason=safe_reason,
                    metadata_={"restored_version_no": source.version_no},
                )
            )
            await self.session.flush()
            return await self._candidate_dto(candidate)

        raise StudentLearningLoopError("REPLAN_DECISION_INVALID", "不支持的路径决定。", 422)

    async def decide_recommendation(
        self,
        *,
        actor: User,
        course_id: UUID,
        recommendation_id: UUID,
        decision: str,
        reason: str | None = None,
    ) -> ResourceRecommendationDTO:
        await self._require_student_enrollment(actor, course_id)
        recommendation = await self.session.scalar(
            select(CourseResourceRecommendation).where(
                CourseResourceRecommendation.id == recommendation_id,
                CourseResourceRecommendation.student_id == actor.id,
                CourseResourceRecommendation.course_id == course_id,
            )
        )
        if recommendation is None:
            raise StudentLearningLoopError("RECOMMENDATION_NOT_FOUND", "推荐记录不存在或不属于当前账户。", 404)
        status_map = {
            "accept": "accepted",
            "defer": "deferred",
            "reject": "rejected",
            "complete": "completed",
        }
        if decision not in status_map:
            raise StudentLearningLoopError("RECOMMENDATION_DECISION_INVALID", "不支持的推荐决定。", 422)
        if recommendation.status in {"superseded", "feedback_received"}:
            raise StudentLearningLoopError("RECOMMENDATION_DECISION_UNAVAILABLE", "该推荐已被后续路径或反馈替换。", 409)
        recommendation.status = status_map[decision]
        recommendation.decision_reason = _clean_optional_text(reason, maximum=400)
        recommendation.decided_at = _now()
        await self.session.flush()
        return await self._recommendation_dto(recommendation)

    async def create_feedback(
        self,
        *,
        actor: User,
        course_id: UUID,
        resource_id: UUID,
        feedback_kinds: list[str],
        comment: str | None,
        recommendation_id: UUID | None,
    ) -> ResourceFeedback:
        await self._require_student_enrollment(actor, course_id)
        safe_kinds = _normalise_feedback_kinds(feedback_kinds)
        safe_comment = _clean_feedback_comment(comment)
        resource = await self._accessible_resource(actor.id, course_id, resource_id)
        recommendation: CourseResourceRecommendation | None = None
        if recommendation_id is not None:
            recommendation = await self.session.scalar(
                select(CourseResourceRecommendation).where(
                    CourseResourceRecommendation.id == recommendation_id,
                    CourseResourceRecommendation.student_id == actor.id,
                    CourseResourceRecommendation.course_id == course_id,
                    CourseResourceRecommendation.resource_id == resource.id,
                )
            )
            if recommendation is None:
                raise StudentLearningLoopError(
                    "RECOMMENDATION_NOT_AVAILABLE",
                    "所选推荐不存在、已失效或不属于当前资源。",
                    404,
                )
        feedback = ResourceFeedback(
            id=uuid4(),
            resource_id=resource.id,
            student_id=actor.id,
            course_id=course_id,
            kp_id=resource.kp_id,
            recommendation_id=recommendation.id if recommendation is not None else None,
            feedback_kinds=safe_kinds,
            comment=safe_comment,
            status="submitted",
            outcome={},
            metadata_={
                "source_kind": _resource_source_kind(resource),
                "source_boundary": _resource_boundary(resource),
                "lineage_root_id": str(resource.lineage_root_id or resource.id),
            },
        )
        self.session.add(feedback)
        if recommendation is not None and recommendation.status not in {"superseded", "completed"}:
            recommendation.status = "feedback_received"
            recommendation.decided_at = _now()
        await self.session.flush()
        return feedback

    async def attach_retry_run(
        self,
        *,
        actor: User,
        course_id: UUID,
        feedback_id: UUID,
        workflow_run_id: UUID,
    ) -> ResourceFeedback:
        feedback = await self._feedback_for_actor(feedback_id, actor.id, course_id)
        feedback.retry_workflow_run_id = workflow_run_id
        feedback.status = "retry_requested"
        feedback.outcome = {
            "state": "queued",
            "message": "已创建真实资源重生成请求；旧版本会继续保留，直到新的 Artifact 通过质量检查并持久化。",
        }
        await self.session.flush()
        return feedback

    async def mark_feedback_unavailable(
        self,
        *,
        actor: User,
        course_id: UUID,
        feedback_id: UUID,
        code: str,
        message: str,
    ) -> ResourceFeedback:
        feedback = await self._feedback_for_actor(feedback_id, actor.id, course_id)
        feedback.status = "provider_unavailable"
        feedback.outcome = {
            "state": "not_started",
            "code": str(code)[:96],
            "message": str(message)[:400],
            "old_version_retained": True,
        }
        await self.session.flush()
        return feedback

    async def mark_feedback_failed(
        self,
        *,
        actor: User,
        course_id: UUID,
        feedback_id: UUID,
        code: str,
        message: str,
    ) -> ResourceFeedback:
        """Persist a real start failure without relabelling it as a provider outage."""

        feedback = await self._feedback_for_actor(feedback_id, actor.id, course_id)
        feedback.status = "failed"
        feedback.outcome = {
            "state": "not_started",
            "code": str(code)[:96],
            "message": str(message)[:400],
            "old_version_retained": True,
        }
        await self.session.flush()
        return feedback

    async def reconcile_feedback(self, *, actor: User, course_id: UUID) -> None:
        """Project terminal retry facts without treating a queued root as success."""

        pending = list(
            (
                await self.session.execute(
                    select(ResourceFeedback).where(
                        ResourceFeedback.student_id == actor.id,
                        ResourceFeedback.course_id == course_id,
                        ResourceFeedback.status == "retry_requested",
                        ResourceFeedback.retry_workflow_run_id.is_not(None),
                    )
                )
            ).scalars()
        )
        for feedback in pending:
            run = await self.session.get(WorkflowRun, feedback.retry_workflow_run_id)
            if run is None or run.user_id != actor.id or run.status not in _TERMINAL_WORKFLOW_STATUSES:
                continue
            if run.status == "succeeded":
                result = await self.session.scalar(
                    select(GeneratedResource)
                    .where(
                        GeneratedResource.workflow_run_id == run.id,
                        GeneratedResource.parent_resource_id == feedback.resource_id,
                        GeneratedResource.user_id == actor.id,
                        GeneratedResource.course_id == course_id,
                        GeneratedResource.status.in_(_ACCESSIBLE_RESOURCE_STATUSES),
                    )
                    .order_by(GeneratedResource.version.desc(), GeneratedResource.updated_at.desc())
                    .limit(1)
                )
                original = await self.session.get(GeneratedResource, feedback.resource_id)
                if result is not None and original is not None and (
                    result.lineage_root_id or result.id
                ) == (original.lineage_root_id or original.id):
                    feedback.status = "regenerated"
                    feedback.resulting_resource_id = result.id
                    feedback.outcome = {
                        "state": "completed",
                        "message": "新的资源版本已通过真实工作流持久化；可比较内容与质量变化。",
                        "old_version_retained": True,
                    }
                    await self._create_feedback_follow_up(feedback, original, result)
                    continue
                feedback.status = "failed"
                feedback.outcome = {
                    "state": "output_missing",
                    "message": "工作流结束但未找到可验证的新 Artifact；旧版本保持可用。",
                    "old_version_retained": True,
                }
                continue

            error = dict(run.error or {})
            code = str(error.get("code") or run.status.upper())[:96]
            feedback.status = "provider_unavailable" if code in {
                "PROVIDER_UNAVAILABLE", "PROVIDER_UNKNOWN_OUTCOME", "INSUFFICIENT_EVIDENCE"
            } else "failed"
            feedback.outcome = {
                "state": run.status,
                "code": code,
                "message": str(error.get("message") or "资源重生成未完成；旧版本仍可继续使用。")[:400],
                "old_version_retained": True,
            }
        await self.session.flush()

    async def _require_student_enrollment(self, actor: User, course_id: UUID) -> CourseEnrollment:
        # Endpoint handlers commit their own mutation before returning.  Refresh
        # the authenticated entity so a later in-session operation never reads
        # an expired role field through synchronous lazy loading.
        await self.session.refresh(actor)
        if actor.role != "student":
            raise StudentLearningLoopError(
                "STUDENT_ROLE_REQUIRED",
                "当前学习路径与资源反馈仅面向已登录的学生账户。",
            )
        enrollment = await self.session.scalar(
            select(CourseEnrollment)
            .where(
                CourseEnrollment.course_id == course_id,
                CourseEnrollment.student_id == actor.id,
                CourseEnrollment.status.in_(("enrolled", "completed")),
            )
            .limit(1)
        )
        if enrollment is None:
            raise StudentLearningLoopError(
                "COURSE_ENROLLMENT_REQUIRED",
                "当前账户没有此课程的有效选课记录，不能操作路径或资源反馈。",
            )
        return enrollment

    async def _active_path(self, user_id: UUID, course_id: UUID) -> LearningPath:
        path = await self.session.scalar(
            select(LearningPath)
            .where(
                LearningPath.user_id == user_id,
                LearningPath.course_id == course_id,
                LearningPath.status == "active",
            )
            .order_by(LearningPath.updated_at.desc())
            .limit(1)
        )
        if path is None:
            raise StudentLearningLoopError(
                "LEARNING_PATH_REQUIRED",
                "当前没有可重规划的已持久化学习路径；请先完成课程路径生成或检查选课数据。",
                409,
            )
        return path

    async def _active_path_version(self, user_id: UUID, course_id: UUID) -> LearningPathVersion | None:
        return await self.session.scalar(
            select(LearningPathVersion)
            .where(
                LearningPathVersion.user_id == user_id,
                LearningPathVersion.course_id == course_id,
                LearningPathVersion.state == "active",
            )
            .order_by(LearningPathVersion.version_no.desc())
            .limit(1)
        )

    async def _ensure_version_for_path(self, path: LearningPath) -> LearningPathVersion:
        existing = await self.session.scalar(
            select(LearningPathVersion)
            .where(LearningPathVersion.path_id == path.id)
            .order_by(LearningPathVersion.version_no.desc())
            .limit(1)
        )
        if existing is not None:
            return existing
        current = await self._active_path_version(path.user_id, path.course_id)
        if current is not None and current.path_id != path.id:
            current.state = "historical"
        version = LearningPathVersion(
            id=uuid4(),
            path_id=path.id,
            user_id=path.user_id,
            course_id=path.course_id,
            version_no=await self._next_version_no(path.user_id, path.course_id),
            state="active",
            kind="baseline",
            title=path.title,
            summary="当前已持久化学习路径的基线版本。",
            diff={"added_tasks": [], "removed_tasks": []},
            task_snapshot=await self._task_snapshot(path.id),
            metadata_={"path_metadata": dict(path.metadata_ or {})},
        )
        self.session.add(version)
        await self.session.flush()
        return version

    async def _resolve_trigger(
        self,
        *,
        actor_id: UUID,
        course_id: UUID,
        trigger_event_id: UUID | None,
        assessment_workflow_run_id: UUID | None,
    ) -> tuple[LearningEvent | None, WorkflowRun | None]:
        if trigger_event_id is not None:
            event = await self.session.scalar(
                select(LearningEvent).where(
                    LearningEvent.id == trigger_event_id,
                    LearningEvent.user_id == actor_id,
                )
            )
            if event is None or not await self._event_in_course(event, course_id):
                raise StudentLearningLoopError(
                    "REPLAN_TRIGGER_NOT_FOUND",
                    "所选学习事件不存在或不属于当前课程。",
                    404,
                )
            return event, None
        if assessment_workflow_run_id is not None:
            workflow = await self.session.scalar(
                select(WorkflowRun).where(
                    WorkflowRun.id == assessment_workflow_run_id,
                    WorkflowRun.user_id == actor_id,
                    WorkflowRun.workflow_name == "assessment_update_v2",
                    WorkflowRun.status == "succeeded",
                )
            )
            payload = dict(workflow.input_payload or {}) if workflow is not None else {}
            if workflow is None or _uuid_or_none(payload.get("course_id")) != course_id:
                raise StudentLearningLoopError(
                    "ASSESSMENT_TRIGGER_NOT_FOUND",
                    "所选阶段评估不存在、未完成或不属于当前课程。",
                    404,
                )
            return None, workflow
        event = await self.session.scalar(
            select(LearningEvent)
            .where(LearningEvent.user_id == actor_id)
            .order_by(LearningEvent.occurred_at.desc())
            .limit(24)
        )
        if event is not None and await self._event_in_course(event, course_id):
            return event, None
        return None, None

    async def _event_in_course(self, event: LearningEvent, course_id: UUID) -> bool:
        if event.kp_id is not None:
            node = await self.session.get(KnowledgeNode, event.kp_id)
            if node is not None and node.course_id == course_id:
                return True
        if event.resource_id is not None:
            resource = await self.session.get(GeneratedResource, event.resource_id)
            if resource is not None and resource.course_id == course_id:
                return True
        return _uuid_or_none(dict(event.result or {}).get("course_id")) == course_id

    async def _path_tasks(self, path_id: UUID) -> list[tuple[LearningTask, KnowledgeNode | None]]:
        return list(
            (
                await self.session.execute(
                    select(LearningTask, KnowledgeNode)
                    .outerjoin(KnowledgeNode, KnowledgeNode.id == LearningTask.kp_id)
                    .where(LearningTask.path_id == path_id)
                    .order_by(LearningTask.order_index)
                )
            ).all()
        )

    async def _task_snapshot(self, path_id: UUID) -> list[dict[str, Any]]:
        return [self._snapshot_task(task, node, action="retained") for task, node in await self._path_tasks(path_id)]

    async def _focus_node(
        self,
        *,
        actor_id: UUID,
        course_id: UUID,
        trigger_event: LearningEvent | None,
        tasks: list[tuple[LearningTask, KnowledgeNode | None]],
    ) -> KnowledgeNode:
        if trigger_event is not None and trigger_event.kp_id is not None:
            node = await self.session.get(KnowledgeNode, trigger_event.kp_id)
            if node is not None and node.course_id == course_id:
                return node
        for task, node in tasks:
            if node is not None and task.status in {"active", "todo", "in_progress"}:
                return node
        node = await self.session.scalar(
            select(KnowledgeNode)
            .join(QuizItem, QuizItem.kp_id == KnowledgeNode.id)
            .join(QuizAttempt, QuizAttempt.quiz_item_id == QuizItem.id)
            .where(QuizAttempt.user_id == actor_id, KnowledgeNode.course_id == course_id)
            .order_by(QuizAttempt.created_at.desc())
            .limit(1)
        )
        if node is None:
            raise StudentLearningLoopError(
                "REPLAN_KNOWLEDGE_POINT_REQUIRED",
                "当前路径缺少可关联的课程知识点，无法生成可解释的重规划候选。",
                409,
            )
        return node

    async def _node_average_score(self, user_id: UUID, kp_id: UUID) -> float | None:
        values = list(
            (
                await self.session.execute(
                    select(QuizAttempt.score)
                    .join(QuizItem, QuizItem.id == QuizAttempt.quiz_item_id)
                    .where(
                        QuizAttempt.user_id == user_id,
                        QuizItem.kp_id == kp_id,
                        QuizAttempt.score.is_not(None),
                    )
                    .order_by(QuizAttempt.created_at.desc())
                    .limit(6)
                )
            ).scalars()
        )
        numeric = [float(value) for value in values if value is not None]
        return round(sum(numeric) / len(numeric), 3) if numeric else None

    @staticmethod
    def _replan_reason(
        *, focus_node: KnowledgeNode, average_score: float | None
    ) -> tuple[str, str, int, str]:
        if average_score is not None and average_score < 0.65:
            return (
                "needs_reinforcement",
                f"{focus_node.name} 的近期已评分作答均分为 {round(average_score * 100)}%，先补一项防御性复盘，再继续原有后续任务。",
                35,
                f"{focus_node.name} 防御性补强复盘",
            )
        if average_score is not None and average_score >= 0.85:
            return (
                "ready_for_consolidation",
                f"{focus_node.name} 的近期已评分作答均分为 {round(average_score * 100)}%，建议用一项迁移性复盘巩固，而不是重复覆盖已完成进度。",
                25,
                f"{focus_node.name} 迁移性防御复盘",
            )
        return (
            "consolidate_current_progress",
            f"当前学习事件指向 {focus_node.name}；现有样本不足以给出激进跳过结论，建议加入一项短复盘并保留原有顺序。",
            20,
            f"{focus_node.name} 关键概念复盘",
        )

    def _proposed_tasks(
        self,
        tasks: list[tuple[LearningTask, KnowledgeNode | None]],
        focus_node: KnowledgeNode,
        supplemental_title: str,
        expected_minutes: int,
    ) -> list[dict[str, Any]]:
        proposed: list[dict[str, Any]] = []
        inserted = False
        for task, node in tasks:
            if not inserted and node is not None and node.id == focus_node.id and task.status != "done":
                proposed.append(
                    {
                        "action": "added",
                        "title": supplemental_title,
                        "kp_id": str(focus_node.id),
                        "knowledge_point": focus_node.name,
                        "status": "todo",
                        "task_type": "replan_review",
                        "expected_minutes": expected_minutes,
                        "metadata": {"reason": "student_replan"},
                    }
                )
                inserted = True
            proposed.append(self._snapshot_task(task, node, action="retained"))
        if not inserted:
            proposed.append(
                {
                    "action": "added",
                    "title": supplemental_title,
                    "kp_id": str(focus_node.id),
                    "knowledge_point": focus_node.name,
                    "status": "todo",
                    "task_type": "replan_review",
                    "expected_minutes": expected_minutes,
                    "metadata": {"reason": "student_replan"},
                }
            )
        for index, item in enumerate(proposed, start=1):
            item["order_index"] = index
        return proposed

    @staticmethod
    def _snapshot_task(
        task: LearningTask,
        node: KnowledgeNode | None,
        *,
        action: str,
    ) -> dict[str, Any]:
        metadata = dict(task.metadata_ or {})
        return {
            "action": action,
            "title": task.title,
            "kp_id": str(task.kp_id) if task.kp_id else None,
            "knowledge_point": node.name if node is not None else None,
            "status": _task_status(task.status),
            "task_type": task.task_type,
            "expected_minutes": _bounded_int(metadata.get("expected_minutes"), default=0),
            "metadata": metadata,
        }

    async def _recommendation_plan(
        self,
        user_id: UUID,
        course_id: UUID,
        kp_id: UUID,
        reason_code: str,
    ) -> list[dict[str, Any]]:
        rows = list(
            (
                await self.session.execute(
                    select(GeneratedResource)
                    .where(
                        GeneratedResource.course_id == course_id,
                        GeneratedResource.kp_id == kp_id,
                        GeneratedResource.status.in_(_ACCESSIBLE_RESOURCE_STATUSES),
                        or_(GeneratedResource.user_id.is_(None), GeneratedResource.user_id == user_id),
                    )
                    .order_by(GeneratedResource.version.desc(), GeneratedResource.updated_at.desc())
                )
            ).scalars()
        )
        seen_lineages: set[UUID] = set()
        plan: list[dict[str, Any]] = []
        for resource in rows:
            lineage = resource.lineage_root_id or resource.id
            if lineage in seen_lineages:
                continue
            seen_lineages.add(lineage)
            plan.append(
                {
                    "resource_id": str(resource.id),
                    "kp_id": str(kp_id),
                    "rationale": self._recommendation_reason(resource, reason_code),
                }
            )
            if len(plan) >= 2:
                break
        return plan

    @staticmethod
    def _recommendation_reason(resource: GeneratedResource, reason_code: str) -> str:
        label = {
            "needs_reinforcement": "补强当前薄弱环节",
            "ready_for_consolidation": "巩固已掌握概念并迁移到新的防御判断",
            "consolidate_current_progress": "在原路径基础上完成短复盘",
        }[reason_code]
        return f"{label}：优先推送与当前知识点关联的{resource.resource_type}资源《{resource.title}》。"

    async def _candidate_for_actor(
        self, candidate_id: UUID, student_id: UUID, course_id: UUID
    ) -> LearningPathReplanCandidate:
        candidate = await self.session.scalar(
            select(LearningPathReplanCandidate).where(
                LearningPathReplanCandidate.id == candidate_id,
                LearningPathReplanCandidate.student_id == student_id,
                LearningPathReplanCandidate.course_id == course_id,
            )
        )
        if candidate is None:
            raise StudentLearningLoopError("REPLAN_CANDIDATE_NOT_FOUND", "重规划候选不存在或不属于当前账户。", 404)
        return candidate

    async def _materialize_path_version(
        self,
        *,
        actor_id: UUID,
        course_id: UUID,
        source_version: LearningPathVersion,
        task_snapshot: list[dict[str, Any]],
        kind: str,
        summary: str,
        diff: dict[str, Any],
        trigger_event_id: UUID | None,
        trigger_workflow_run_id: UUID | None,
    ) -> LearningPathVersion:
        source_path = await self.session.get(LearningPath, source_version.path_id)
        if source_path is None:
            raise StudentLearningLoopError("PATH_VERSION_SOURCE_UNAVAILABLE", "路径版本的原始路径不存在。", 409)
        active_paths = list(
            (
                await self.session.execute(
                    select(LearningPath).where(
                        LearningPath.user_id == actor_id,
                        LearningPath.course_id == course_id,
                        LearningPath.status == "active",
                    )
                )
            ).scalars()
        )
        for active_path in active_paths:
            active_path.status = "superseded"
        active_versions = list(
            (
                await self.session.execute(
                    select(LearningPathVersion).where(
                        LearningPathVersion.user_id == actor_id,
                        LearningPathVersion.course_id == course_id,
                        LearningPathVersion.state == "active",
                    )
                )
            ).scalars()
        )
        for active_version in active_versions:
            active_version.state = "historical"

        path = LearningPath(
            id=uuid4(),
            user_id=actor_id,
            course_id=course_id,
            title=source_path.title,
            objective=source_path.objective,
            status="active",
            metadata_={
                **dict(source_path.metadata_ or {}),
                "derived_from_path_version_id": str(source_version.id),
                "path_change_kind": kind,
            },
        )
        self.session.add(path)
        await self.session.flush()
        normalized_snapshot = self._normalise_snapshot(task_snapshot)
        for item in normalized_snapshot:
            self.session.add(
                LearningTask(
                    id=uuid4(),
                    path_id=path.id,
                    kp_id=_uuid_or_none(item.get("kp_id")),
                    title=str(item["title"]),
                    task_type=str(item.get("task_type") or "course_learning"),
                    order_index=int(item["order_index"]),
                    status=str(item.get("status") or "todo"),
                    metadata_={
                        **dict(item.get("metadata") or {}),
                        "expected_minutes": _bounded_int(item.get("expected_minutes"), default=0),
                        "replan_action": str(item.get("action") or "retained"),
                    },
                )
            )
        version = LearningPathVersion(
            id=uuid4(),
            path_id=path.id,
            user_id=actor_id,
            course_id=course_id,
            parent_version_id=source_version.id,
            trigger_event_id=trigger_event_id,
            trigger_workflow_run_id=trigger_workflow_run_id,
            version_no=await self._next_version_no(actor_id, course_id),
            state="active",
            kind=kind,
            title=path.title,
            summary=summary,
            diff=diff,
            task_snapshot=normalized_snapshot,
            metadata_={"source_version_no": source_version.version_no},
        )
        self.session.add(version)
        await self.session.flush()
        return version

    @staticmethod
    def _normalise_snapshot(snapshot: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(snapshot, start=1):
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            normalized.append(
                {
                    "action": "added" if item.get("action") == "added" else "retained",
                    "title": title[:240],
                    "kp_id": str(item.get("kp_id")) if _uuid_or_none(item.get("kp_id")) else None,
                    "knowledge_point": str(item.get("knowledge_point") or "")[:255] or None,
                    "status": _task_status(str(item.get("status") or "todo")),
                    "task_type": str(item.get("task_type") or "course_learning")[:64],
                    "order_index": index,
                    "expected_minutes": _bounded_int(item.get("expected_minutes"), default=0),
                    "metadata": dict(item.get("metadata") or {}),
                }
            )
        if not normalized:
            raise StudentLearningLoopError("PATH_SNAPSHOT_INVALID", "候选路径没有可持久化的学习任务。", 409)
        return normalized

    async def _next_version_no(self, user_id: UUID, course_id: UUID) -> int:
        maximum = await self.session.scalar(
            select(func.max(LearningPathVersion.version_no)).where(
                LearningPathVersion.user_id == user_id,
                LearningPathVersion.course_id == course_id,
            )
        )
        return int(maximum or 0) + 1

    async def _sync_candidate_recommendations(
        self,
        *,
        actor_id: UUID,
        course_id: UUID,
        candidate: LearningPathReplanCandidate,
        path_version: LearningPathVersion,
    ) -> int:
        created = 0
        for item in list(candidate.recommendation_plan or []):
            resource_id = _uuid_or_none(item.get("resource_id"))
            if resource_id is None:
                continue
            resource = await self._accessible_resource(actor_id, course_id, resource_id)
            duplicate = await self.session.scalar(
                select(CourseResourceRecommendation).where(
                    CourseResourceRecommendation.student_id == actor_id,
                    CourseResourceRecommendation.source_candidate_id == candidate.id,
                    CourseResourceRecommendation.resource_id == resource.id,
                )
            )
            if duplicate is not None:
                continue
            self.session.add(
                CourseResourceRecommendation(
                    id=uuid4(),
                    student_id=actor_id,
                    course_id=course_id,
                    resource_id=resource.id,
                    kp_id=resource.kp_id,
                    path_version_id=path_version.id,
                    source_candidate_id=candidate.id,
                    status="scheduled",
                    rationale=str(item.get("rationale") or "基于已采纳路径同步的课程资源。"),
                    match_context={
                        "candidate_id": str(candidate.id),
                        "reason_code": candidate.reason_code,
                        "lineage_root_id": str(resource.lineage_root_id or resource.id),
                    },
                )
            )
            created += 1
        await self.session.flush()
        return created

    async def _accessible_resource(
        self, student_id: UUID, course_id: UUID, resource_id: UUID
    ) -> GeneratedResource:
        resource = await self.session.scalar(
            select(GeneratedResource).where(
                GeneratedResource.id == resource_id,
                GeneratedResource.course_id == course_id,
                GeneratedResource.status.in_(_ACCESSIBLE_RESOURCE_STATUSES),
                or_(GeneratedResource.user_id.is_(None), GeneratedResource.user_id == student_id),
            )
        )
        if resource is None:
            raise StudentLearningLoopError(
                "RESOURCE_NOT_ACCESSIBLE",
                "资源不存在、不可用或不属于当前课程学习范围。",
                404,
            )
        return resource

    async def _feedback_for_actor(
        self, feedback_id: UUID, student_id: UUID, course_id: UUID
    ) -> ResourceFeedback:
        feedback = await self.session.scalar(
            select(ResourceFeedback).where(
                ResourceFeedback.id == feedback_id,
                ResourceFeedback.student_id == student_id,
                ResourceFeedback.course_id == course_id,
            )
        )
        if feedback is None:
            raise StudentLearningLoopError("RESOURCE_FEEDBACK_NOT_FOUND", "资源反馈不存在或不属于当前账户。", 404)
        return feedback

    async def _create_feedback_follow_up(
        self,
        feedback: ResourceFeedback,
        original: GeneratedResource,
        result: GeneratedResource,
    ) -> None:
        if feedback.recommendation_id is not None:
            recommendation = await self.session.get(CourseResourceRecommendation, feedback.recommendation_id)
            if recommendation is not None:
                recommendation.status = "superseded"
                recommendation.decided_at = _now()
        if feedback.follow_up_recommendation_id is not None:
            return
        active_version = await self._active_path_version(feedback.student_id, feedback.course_id)
        follow_up = CourseResourceRecommendation(
            id=uuid4(),
            student_id=feedback.student_id,
            course_id=feedback.course_id,
            resource_id=result.id,
            kp_id=result.kp_id,
            path_version_id=active_version.id if active_version is not None else None,
            status="scheduled",
            rationale="根据你的结构化资源反馈生成了可验证的新版本；原版本仍可比较和回看。",
            match_context={
                "feedback_id": str(feedback.id),
                "previous_resource_id": str(original.id),
                "lineage_root_id": str(result.lineage_root_id or result.id),
            },
        )
        self.session.add(follow_up)
        await self.session.flush()
        feedback.follow_up_recommendation_id = follow_up.id

    async def _recommendations(self, student_id: UUID, course_id: UUID) -> list[ResourceRecommendationDTO]:
        rows = list(
            (
                await self.session.execute(
                    select(CourseResourceRecommendation, GeneratedResource, KnowledgeNode)
                    .join(GeneratedResource, GeneratedResource.id == CourseResourceRecommendation.resource_id)
                    .outerjoin(KnowledgeNode, KnowledgeNode.id == CourseResourceRecommendation.kp_id)
                    .where(
                        CourseResourceRecommendation.student_id == student_id,
                        CourseResourceRecommendation.course_id == course_id,
                        or_(GeneratedResource.user_id.is_(None), GeneratedResource.user_id == student_id),
                    )
                    .order_by(CourseResourceRecommendation.scheduled_at.desc())
                    .limit(24)
                )
            ).all()
        )
        return [
            self._recommendation_dto_from_row(recommendation, resource, node)
            for recommendation, resource, node in rows
        ]

    async def _recommendation_dto(self, recommendation: CourseResourceRecommendation) -> ResourceRecommendationDTO:
        resource = await self.session.get(GeneratedResource, recommendation.resource_id)
        node = await self.session.get(KnowledgeNode, recommendation.kp_id) if recommendation.kp_id else None
        if resource is None:
            raise StudentLearningLoopError("RECOMMENDATION_RESOURCE_UNAVAILABLE", "推荐资源已不可读取。", 409)
        return self._recommendation_dto_from_row(recommendation, resource, node)

    @staticmethod
    def _recommendation_dto_from_row(
        recommendation: CourseResourceRecommendation,
        resource: GeneratedResource,
        node: KnowledgeNode | None,
    ) -> ResourceRecommendationDTO:
        return ResourceRecommendationDTO(
            id=recommendation.id,
            resource_id=resource.id,
            title=resource.title,
            resource_type=resource.resource_type,
            knowledge_point=node.name if node is not None else None,
            status=recommendation.status,  # type: ignore[arg-type]
            scheduled_at=recommendation.scheduled_at,
            rationale=recommendation.rationale,
            source_boundary=_resource_boundary(resource),
            created_at=recommendation.created_at,
        )

    async def _resource_lineages(self, student_id: UUID, course_id: UUID) -> list[ResourceLineageDTO]:
        rows = list(
            (
                await self.session.execute(
                    select(GeneratedResource, KnowledgeNode)
                    .outerjoin(KnowledgeNode, KnowledgeNode.id == GeneratedResource.kp_id)
                    .where(
                        GeneratedResource.course_id == course_id,
                        GeneratedResource.status.in_(_ACCESSIBLE_RESOURCE_STATUSES),
                        or_(GeneratedResource.user_id.is_(None), GeneratedResource.user_id == student_id),
                    )
                    .order_by(GeneratedResource.created_at.desc())
                )
            ).all()
        )
        grouped: dict[UUID, list[tuple[GeneratedResource, KnowledgeNode | None]]] = defaultdict(list)
        for resource, node in rows:
            grouped[resource.lineage_root_id or resource.id].append((resource, node))
        resource_ids = [resource.id for resource, _ in rows]
        version_rows = list(
            (
                await self.session.execute(
                    select(ResourceVersion).where(ResourceVersion.resource_id.in_(resource_ids))
                )
            ).scalars()
        ) if resource_ids else []
        change_by_resource = {row.resource_id: row for row in version_rows}
        workflow_ids = {resource.workflow_run_id for resource, _ in rows if resource.workflow_run_id is not None}
        workflow_rows = list(
            (
                await self.session.execute(select(WorkflowRun).where(WorkflowRun.id.in_(workflow_ids)))
            ).scalars()
        ) if workflow_ids else []
        run_status = {row.id: row.status for row in workflow_rows}
        lineages: list[ResourceLineageDTO] = []
        for root_id, versions in grouped.items():
            versions.sort(key=lambda pair: (pair[0].version, pair[0].created_at))
            previous: GeneratedResource | None = None
            version_dtos: list[ResourceLineageVersionDTO] = []
            for resource, _node in versions:
                change = change_by_resource.get(resource.id)
                version_dtos.append(
                    ResourceLineageVersionDTO(
                        resource_id=resource.id,
                        version=max(1, int(resource.version)),
                        parent_resource_id=resource.parent_resource_id,
                        title=resource.title,
                        status=resource.status,
                        quality_score=resource.quality_score,
                        quality_delta=_quality_delta(previous, resource),
                        changed_fields=_changed_fields(previous.content if previous else {}, resource.content),
                        change_summary=change.change_summary if change is not None else None,
                        evidence_count=len(resource.evidence_chunk_ids or []),
                        run_state=run_status.get(resource.workflow_run_id, "not_live_run"),
                        source_kind=_resource_source_kind(resource),  # type: ignore[arg-type]
                        source_boundary=_resource_boundary(resource),
                        created_at=resource.created_at,
                    )
                )
                previous = resource
            current, current_node = versions[-1]
            metadata = dict(current.metadata_ or {})
            lineages.append(
                ResourceLineageDTO(
                    lineage_root_id=root_id,
                    logical_key=str(metadata.get("logical_key") or f"{current.resource_type}:{root_id}"),
                    resource_type=current.resource_type,
                    title=current.title,
                    knowledge_point=current_node.name if current_node is not None else None,
                    current_resource_id=current.id,
                    versions=list(reversed(version_dtos)),
                )
            )
        return sorted(lineages, key=lambda item: (item.resource_type, item.title))

    async def _candidate_dto(self, candidate: LearningPathReplanCandidate) -> PathReplanCandidateDTO:
        # ``updated_at`` is maintained by a database-side on-update expression.
        # Refresh after a decision flush so async DTO serialization never tries
        # to lazily load an expired timestamp outside SQLAlchemy's greenlet.
        await self.session.refresh(candidate)
        source = await self.session.get(LearningPathVersion, candidate.source_path_version_id)
        accepted = (
            await self.session.get(LearningPathVersion, candidate.accepted_path_version_id)
            if candidate.accepted_path_version_id is not None
            else None
        )
        node = await self.session.get(KnowledgeNode, candidate.affected_kp_id) if candidate.affected_kp_id else None
        event = await self.session.get(LearningEvent, candidate.trigger_event_id) if candidate.trigger_event_id else None
        workflow = await self.session.get(WorkflowRun, candidate.trigger_workflow_run_id) if candidate.trigger_workflow_run_id else None
        changed = [
            PathTaskChangeDTO(
                action="added" if item.get("action") == "added" else "retained",
                title=str(item.get("title") or "未命名任务"),
                knowledge_point=str(item.get("knowledge_point") or "") or None,
                status=_task_status(str(item.get("status") or "todo")),  # type: ignore[arg-type]
                expected_minutes=_bounded_int(item.get("expected_minutes"), default=0),
            )
            for item in list(candidate.proposed_task_snapshot or [])
        ]
        trigger_label = (
            "已完成阶段评估" if workflow is not None else
            f"学习事件：{event.event_type}" if event is not None else
            "当前已持久化学习状态"
        )
        trigger_at = workflow.finished_at if workflow is not None else event.occurred_at if event is not None else None
        return PathReplanCandidateDTO(
            id=candidate.id,
            status=candidate.status,  # type: ignore[arg-type]
            source_version_no=source.version_no if source is not None else 1,
            accepted_version_no=accepted.version_no if accepted is not None else None,
            trigger_label=trigger_label,
            trigger_at=trigger_at,
            reason_code=candidate.reason_code,
            reason_text=candidate.reason_text,
            affected_knowledge_point=node.name if node is not None else None,
            expected_minutes=candidate.expected_minutes,
            changed_tasks=changed,
            source_boundary=str(
                dict(candidate.metadata_ or {}).get("source_boundary")
                or "候选由当前账户的持久化学习记录计算；不会伪称为实时模型结论。"
            ),
            created_at=candidate.created_at,
            updated_at=candidate.updated_at,
        )

    @staticmethod
    def _path_version_dto(version: LearningPathVersion) -> PathVersionDTO:
        return PathVersionDTO(
            id=version.id,
            version_no=version.version_no,
            kind=version.kind,  # type: ignore[arg-type]
            state=version.state,  # type: ignore[arg-type]
            title=version.title,
            summary=version.summary,
            diff=dict(version.diff or {}),
            created_at=version.created_at,
        )

    @staticmethod
    def feedback_dto(feedback: ResourceFeedback) -> ResourceFeedbackDTO:
        return ResourceFeedbackDTO(
            id=feedback.id,
            resource_id=feedback.resource_id,
            status=feedback.status,  # type: ignore[arg-type]
            feedback_kinds=list(feedback.feedback_kinds or []),  # type: ignore[arg-type]
            comment=feedback.comment,
            retry_workflow_run_id=feedback.retry_workflow_run_id,
            resulting_resource_id=feedback.resulting_resource_id,
            outcome=dict(feedback.outcome or {}),
            created_at=feedback.created_at,
            updated_at=feedback.updated_at,
        )

    @staticmethod
    def _candidate_boundary(event: LearningEvent | None) -> str:
        if event is not None and dict(event.result or {}).get("seed_profile"):
            return "受控 WEBSEC-101 课程场景中的真实持久化学习事件；不是实时模型生成结果。"
        return "候选由当前账户的已持久化学习事件、作答和路径状态计算；采纳前不会改写课程或历史进度。"


def _task_status(value: str) -> str:
    if value == "done":
        return "done"
    if value in {"active", "in_progress"}:
        return "active"
    if value in {"blocked", "locked"}:
        return "blocked"
    return "todo"


def _uuid_or_none(value: Any) -> UUID | None:
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def _bounded_int(value: Any, *, default: int) -> int:
    try:
        return max(0, min(600, int(value)))
    except (TypeError, ValueError):
        return default


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_optional_text(value: str | None, *, maximum: int) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())[:maximum]
    return cleaned or None


def _normalise_feedback_kinds(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        normalised = str(value).strip()
        if normalised not in _FEEDBACK_KINDS:
            raise StudentLearningLoopError("RESOURCE_FEEDBACK_KIND_INVALID", "反馈类型不受支持。", 422)
        if normalised not in result:
            result.append(normalised)
    if not result:
        raise StudentLearningLoopError("RESOURCE_FEEDBACK_REQUIRED", "请至少选择一项资源反馈。", 422)
    return result


def _clean_feedback_comment(value: str | None) -> str | None:
    cleaned = _clean_optional_text(value, maximum=500)
    if cleaned is None:
        return None
    lower = cleaned.lower()
    forbidden = ("ignore previous instructions", "system prompt", "忽略之前指令", "忽略以上指令")
    if any(marker in lower for marker in forbidden):
        raise StudentLearningLoopError(
            "RESOURCE_FEEDBACK_UNSAFE",
            "反馈包含无法作为课程资源改写要求处理的指令，请改为描述学习困难或希望补充的内容。",
            422,
        )
    return cleaned


def _resource_source_kind(resource: GeneratedResource) -> str:
    metadata = dict(resource.metadata_ or {})
    content = dict(resource.content or {})
    value = str(metadata.get("source_kind") or content.get("source_type") or "").strip()
    if value == "external-preview":
        return "external-preview"
    if value in {"curated-demo", "curated_lecture", "preprocessed_seed"}:
        return "curated-demo"
    return "real"


def _resource_boundary(resource: GeneratedResource) -> str:
    source_kind = _resource_source_kind(resource)
    content = dict(resource.content or {})
    if source_kind == "external-preview":
        return "外部公开资料目录；平台只保留合规跳转与学习导引，不托管或伪称生成该内容。"
    if source_kind == "curated-demo":
        return "受控课程整理内容，已写入真实课程资源记录；不是实时模型生成。"
    return str(content.get("source_boundary") or "真实持久化资源；详情保留来源、Evidence 与运行状态。")


def _quality_delta(previous: GeneratedResource | None, current: GeneratedResource) -> float | None:
    if previous is None or previous.quality_score is None or current.quality_score is None:
        return None
    return round(float(current.quality_score) - float(previous.quality_score), 3)


def _changed_fields(before: dict[str, Any] | None, after: dict[str, Any] | None) -> list[str]:
    previous = dict(before or {})
    current = dict(after or {})
    keys = sorted(set(previous) | set(current))
    return [key for key in keys if previous.get(key) != current.get(key)][:12]


__all__ = ["StudentLearningLoopError", "StudentLearningLoopService"]
