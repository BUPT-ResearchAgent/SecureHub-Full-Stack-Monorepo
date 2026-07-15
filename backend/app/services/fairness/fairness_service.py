# Status: real

"""Consent-gated aggregate fairness monitoring and human review workflow."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.fairness.fairness import (
    FairnessAlert,
    FairnessAppeal,
    FairnessConsent,
    FairnessGroupAssignment,
    FairnessMetricCell,
    FairnessMetricRun,
    FairnessPolicy,
    FairnessReview,
)
from app.db.models.identity.user import User
from app.repositories.fairness.fairness_repository import FairnessRepository
from app.repositories.governance.governance import GovernanceRepository
from app.schemas.fairness import (
    FairnessAlertDTO,
    AppealableGradeDTO,
    AppealableGradeListDTO,
    FairnessAppealCreateRequest,
    FairnessAppealDTO,
    FairnessAppealListDTO,
    FairnessAppealResolveRequest,
    FairnessConsentDTO,
    FairnessConsentRequest,
    FairnessConsentWithdrawRequest,
    FairnessDashboardDTO,
    FairnessGroupAssignmentDTO,
    FairnessGroupAssignmentRequest,
    FairnessMetricCellDTO,
    FairnessMetricRunDTO,
    FairnessMetricRunRequest,
    FairnessPolicyCreateRequest,
    FairnessPolicyDTO,
    FairnessReviewDTO,
    FairnessReviewRequest,
)

_ADMIN_ROLE = "administrator"
_CONSENT_SCOPE = "assessment_fairness"
# RFC §8.1 authorizes a non-sensitive teaching cohort or teaching class; no
# protected-attribute key is accepted by this implementation.
_ALLOWED_NON_SENSITIVE_GROUP_KEYS = frozenset({"cohort", "teaching_class"})
_DEFAULT_THRESHOLDS = {"max_mean_score_gap": 10.0, "max_pass_rate_gap": 0.2}


class FairnessDomainError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 403) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class FairnessService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = FairnessRepository(session)
        self.governance_repo = GovernanceRepository(session)

    async def create_policy(
        self, *, actor: User, payload: FairnessPolicyCreateRequest
    ) -> FairnessPolicyDTO:
        await self._require_admin(actor)
        allowed_keys = sorted(set(payload.allowed_group_keys))
        if not allowed_keys or set(allowed_keys) - _ALLOWED_NON_SENSITIVE_GROUP_KEYS:
            raise FairnessDomainError(
                "FAIRNESS_ATTRIBUTE_NOT_ALLOWED",
                "公平政策只允许 RFC 中的非敏感教学分组 cohort 或 teaching_class。",
                422,
            )
        if await self.repo.get_policy_by_code_version(code=payload.code, version_no=payload.version_no):
            raise FairnessDomainError("FAIRNESS_POLICY_CONFLICT", "该公平政策版本已存在。", 409)
        if await self.repo.get_active_policy_by_code(payload.code):
            raise FairnessDomainError(
                "FAIRNESS_POLICY_CONFLICT", "请先退役同代码的现行政策，再激活新版本。", 409
            )
        now = datetime.now(UTC)
        thresholds = {**_DEFAULT_THRESHOLDS, **payload.thresholds}
        policy = await self.repo.create_policy(
            code=payload.code,
            version_no=payload.version_no,
            purpose=payload.purpose.strip(),
            allowed_group_keys=allowed_keys,
            minimum_sample=payload.minimum_sample,
            pass_score=payload.pass_score,
            thresholds=thresholds,
            retention_days=payload.retention_days,
            status="active",
            created_by=actor.id,
            activated_at=now,
            retired_at=None,
        )
        await self.repo.write_audit(
            actor_user_id=actor.id,
            action="fairness_policy.activate",
            object_type="fairness_policy",
            object_id=policy.id,
            reason=policy.purpose,
            result_status="succeeded",
            metadata={
                "version": policy.version_no,
                "allowed_group_keys": allowed_keys,
                "minimum_sample": policy.minimum_sample,
                "retention_days": policy.retention_days,
                "sensitive_attributes": "not_collected",
            },
        )
        return self._policy_dto(policy)

    async def list_policies(self, *, actor: User) -> list[FairnessPolicyDTO]:
        await self._require_admin(actor)
        return [self._policy_dto(item) for item in await self.repo.list_policies()]

    async def grant_consent(
        self, *, actor: User, payload: FairnessConsentRequest
    ) -> FairnessConsentDTO:
        policy = await self._require_active_policy(payload.policy_id)
        now = datetime.now(UTC)
        expires_at = _as_utc(payload.expires_at)
        if expires_at <= now:
            raise FairnessDomainError("FAIRNESS_CONSENT_INVALID", "同意有效期必须晚于当前时间。", 422)
        scope = payload.scope.strip()
        if scope != _CONSENT_SCOPE:
            raise FairnessDomainError("FAIRNESS_CONSENT_SCOPE_INVALID", "不支持该公平评估同意范围。", 422)
        consent = await self.repo.get_consent(user_id=actor.id, policy_id=policy.id, scope=scope)
        if consent is None:
            consent = FairnessConsent(
                user_id=actor.id,
                policy_id=policy.id,
                scope=scope,
                status="granted",
                granted_at=now,
                withdrawn_at=None,
                expires_at=expires_at,
            )
            self.session.add(consent)
        else:
            consent.status = "granted"
            consent.granted_at = now
            consent.withdrawn_at = None
            consent.expires_at = expires_at
        await self.session.flush()
        await self.repo.write_audit(
            actor_user_id=actor.id,
            action="fairness_consent.grant",
            object_type="fairness_consent",
            object_id=consent.id,
            reason="本人明确同意用于聚合公平评估。",
            result_status="succeeded",
            metadata={"policy_id": str(policy.id), "scope": scope, "expires_at": expires_at.isoformat()},
        )
        return self._consent_dto(consent)

    async def withdraw_consent(
        self,
        *,
        actor: User,
        policy_id: UUID,
        payload: FairnessConsentWithdrawRequest,
    ) -> FairnessConsentDTO:
        consent = await self.repo.get_consent(
            user_id=actor.id, policy_id=policy_id, scope=_CONSENT_SCOPE
        )
        if consent is None:
            raise FairnessDomainError("FAIRNESS_CONSENT_REQUIRED", "当前没有可撤回的公平评估同意。", 404)
        now = datetime.now(UTC)
        consent.status = "withdrawn"
        consent.withdrawn_at = now
        await self.session.flush()
        await self.repo.write_audit(
            actor_user_id=actor.id,
            action="fairness_consent.withdraw",
            object_type="fairness_consent",
            object_id=consent.id,
            reason=payload.reason.strip(),
            result_status="succeeded",
            metadata={"policy_id": str(policy_id), "scope": _CONSENT_SCOPE},
        )
        return self._consent_dto(consent)

    async def assign_group(
        self,
        *,
        actor: User,
        policy_id: UUID,
        payload: FairnessGroupAssignmentRequest,
    ) -> FairnessGroupAssignmentDTO:
        await self._require_admin(actor)
        policy = await self._require_active_policy(policy_id)
        now = datetime.now(UTC)
        key = payload.group_key.strip()
        if key not in policy.allowed_group_keys or key not in _ALLOWED_NON_SENSITIVE_GROUP_KEYS:
            raise FairnessDomainError(
                "FAIRNESS_ATTRIBUTE_NOT_ALLOWED", "该分组字段未被政策允许或不属于 RFC 非敏感字段。", 422
            )
        expires_at = _as_utc(payload.expires_at)
        if expires_at <= now:
            raise FairnessDomainError("FAIRNESS_DATA_MISSING", "分组有效期必须晚于当前时间。", 422)
        consent = await self.repo.get_live_consent(
            user_id=payload.user_id, policy_id=policy.id, scope=_CONSENT_SCOPE, now=now
        )
        if consent is None:
            raise FairnessDomainError(
                "FAIRNESS_CONSENT_REQUIRED", "只能为已明确同意且同意尚有效的账号配置公平分组。", 409
            )
        assignment = await self.repo.get_group_assignment(
            user_id=payload.user_id, policy_id=policy.id, group_key=key
        )
        if assignment is None:
            assignment = FairnessGroupAssignment(
                user_id=payload.user_id,
                policy_id=policy.id,
                group_key=key,
                minimal_group_value=payload.minimal_group_value.strip(),
                expires_at=expires_at,
                assigned_by=actor.id,
            )
            self.session.add(assignment)
        else:
            assignment.minimal_group_value = payload.minimal_group_value.strip()
            assignment.expires_at = expires_at
            assignment.assigned_by = actor.id
        await self.session.flush()
        await self.repo.write_audit(
            actor_user_id=actor.id,
            action="fairness_group.assign",
            object_type="fairness_group_assignment",
            object_id=assignment.id,
            reason=payload.reason.strip(),
            result_status="succeeded",
            metadata={"policy_id": str(policy.id), "group_key": key, "user_id": str(payload.user_id)},
        )
        return self._assignment_dto(assignment)

    async def run_metrics(
        self,
        *,
        actor: User,
        policy_id: UUID,
        payload: FairnessMetricRunRequest,
    ) -> FairnessMetricRunDTO:
        await self._require_admin(actor)
        policy = await self._require_active_policy(policy_id)
        now = datetime.now(UTC)
        assessment_ids = sorted({str(value) for value in payload.assessment_ids})
        grade_rows = await self.repo.list_published_grade_rows(
            assessment_ids=[UUID(value) for value in assessment_ids]
        )
        scope = {"assessment_ids": assessment_ids, "published_only": True}
        if not grade_rows:
            return await self._reject_metric_run(
                actor=actor,
                policy=policy,
                scope=scope,
                formula_version=payload.formula_version,
                code="FAIRNESS_DATA_MISSING",
                message="指定范围没有已发布且含最终成绩的评估结果。",
                limitations={"reason": "published_final_grade_required"},
            )

        participant_ids = sorted({row[1].student_id for row in grade_rows}, key=str)
        groups = await self.repo.list_live_group_assignments(
            user_ids=participant_ids, policy_id=policy.id, now=now
        )
        groups_by_user: dict[UUID, FairnessGroupAssignment] = {}
        for assignment in groups:
            if assignment.group_key in policy.allowed_group_keys and assignment.group_key in _ALLOWED_NON_SENSITIVE_GROUP_KEYS:
                groups_by_user.setdefault(assignment.user_id, assignment)
        missing_group_users = [user_id for user_id in participant_ids if user_id not in groups_by_user]
        if missing_group_users:
            return await self._reject_metric_run(
                actor=actor,
                policy=policy,
                scope=scope,
                formula_version=payload.formula_version,
                code="FAIRNESS_DATA_MISSING",
                message="评估范围内存在缺少有效最小分组的已发布成绩，已拒绝计算。",
                limitations={"missing_group_count": len(missing_group_users), "conclusion_hidden": True},
            )
        active_group_keys = {assignment.group_key for assignment in groups_by_user.values()}
        if len(active_group_keys) != 1:
            return await self._reject_metric_run(
                actor=actor,
                policy=policy,
                scope=scope,
                formula_version=payload.formula_version,
                code="FAIRNESS_DATA_MISSING",
                message="一次公平运行必须使用同一个已许可的最小分组字段，已拒绝混合分组。",
                limitations={"active_group_keys": sorted(active_group_keys), "conclusion_hidden": True},
            )
        consents = await self.repo.list_live_consents(
            user_ids=participant_ids, policy_id=policy.id, scope=_CONSENT_SCOPE, now=now
        )
        consent_user_ids = {item.user_id for item in consents}
        missing_consent_users = [user_id for user_id in participant_ids if user_id not in consent_user_ids]
        if missing_consent_users:
            return await self._reject_metric_run(
                actor=actor,
                policy=policy,
                scope=scope,
                formula_version=payload.formula_version,
                code="FAIRNESS_CONSENT_REQUIRED",
                message="评估范围内存在未同意或同意失效的参与者，已拒绝计算。",
                limitations={"missing_consent_count": len(missing_consent_users), "conclusion_hidden": True},
            )

        grouped_scores: dict[tuple[str, str], list[float]] = defaultdict(list)
        fingerprint_rows: list[dict[str, str | float]] = []
        for grade, submission, _, _, _ in grade_rows:
            assignment = groups_by_user[submission.student_id]
            score = float(grade.final_score or 0.0)
            grouped_scores[(assignment.group_key, assignment.minimal_group_value)].append(score)
            fingerprint_rows.append(
                {
                    "grade_id": str(grade.id),
                    "student_id": str(submission.student_id),
                    "group": f"{assignment.group_key}:{assignment.minimal_group_value}",
                    "published_at": _iso_or_empty(grade.published_at),
                    "score": score,
                }
            )
        fingerprint = _fingerprint(
            {
                "policy": f"{policy.code}:{policy.version_no}",
                "formula_version": payload.formula_version,
                "scope": scope,
                "rows": sorted(fingerprint_rows, key=lambda value: str(value["grade_id"])),
            }
        )
        thresholds = {**_DEFAULT_THRESHOLDS, **(policy.thresholds or {}), "pass_score": policy.pass_score}
        base_run = await self.repo.create_metric_run(
            policy_id=policy.id,
            assessment_scope=scope,
            dataset_fingerprint=fingerprint,
            formula_version=payload.formula_version,
            threshold_config=thresholds,
            status="pending",
            rejection_code=None,
            limitations={},
            initiated_by=actor.id,
            started_at=now,
            finished_at=None,
        )
        group_counts = {f"{key}:{value}": len(scores) for (key, value), scores in grouped_scores.items()}
        under_minimum = {name: count for name, count in group_counts.items() if count < policy.minimum_sample}
        if under_minimum:
            base_run.status = "insufficient_sample"
            base_run.rejection_code = "INSUFFICIENT_SAMPLE"
            base_run.limitations = {
                "minimum_sample": policy.minimum_sample,
                "group_counts": group_counts,
                "under_minimum": under_minimum,
                "conclusion_hidden": True,
                "individual_actions_prohibited": True,
            }
            base_run.finished_at = datetime.now(UTC)
            await self.session.flush()
            await self.repo.write_audit(
                actor_user_id=actor.id,
                action="fairness_metric.run",
                object_type="fairness_metric_run",
                object_id=base_run.id,
                reason="样本量不足，未产生群体结论。",
                result_status="insufficient_sample",
                metadata={"policy_id": str(policy.id), "dataset_fingerprint": fingerprint},
            )
            return self._run_dto(base_run, policy, [], [])

        stats = {
            key: _aggregate(scores, pass_score=policy.pass_score)
            for key, scores in sorted(grouped_scores.items())
        }
        reference_key = sorted(stats, key=lambda key: (-int(stats[key]["sample_size"]), key[0], key[1]))[0]
        reference = stats[reference_key]
        cells: list[FairnessMetricCell] = []
        alerts: list[FairnessAlert] = []
        for (group_key, group_value), values in stats.items():
            mean_delta = float(values["mean_score"]) - float(reference["mean_score"])
            pass_delta = float(values["pass_rate"]) - float(reference["pass_rate"])
            limitations = {
                "reference_group": f"{reference_key[0]}:{reference_key[1]}",
                "mean_score_delta": round(mean_delta, 8),
                "pass_rate_delta": round(pass_delta, 8),
                "classification_metrics": "not_applicable_without_ground_truth_labels",
                "causal_interpretation": "not_supported",
                "individual_actions_prohibited": True,
            }
            cell = await self.repo.create_metric_cell(
                run_id=base_run.id,
                group_key=group_key,
                group_value=group_value,
                sample_size=int(values["sample_size"]),
                mean_score=float(values["mean_score"]),
                pass_rate=float(values["pass_rate"]),
                accuracy=None,
                fpr=None,
                fnr=None,
                equal_opportunity_delta=None,
                confidence_interval=values["confidence_interval"],
                limitations=limitations,
            )
            cells.append(cell)
            mean_gap = abs(mean_delta)
            pass_gap = abs(pass_delta)
            if (group_key, group_value) != reference_key and (
                mean_gap > float(thresholds["max_mean_score_gap"])
                or pass_gap > float(thresholds["max_pass_rate_gap"])
            ):
                ratio = max(
                    mean_gap / max(float(thresholds["max_mean_score_gap"]), 0.000001),
                    pass_gap / max(float(thresholds["max_pass_rate_gap"]), 0.000001),
                )
                severity = "high" if ratio >= 2 else "medium" if ratio >= 1.25 else "low"
                alert = await self.repo.create_alert(
                    metric_cell_id=cell.id,
                    alert_kind="aggregate_disparity_threshold_exceeded",
                    severity=severity,
                    explanation={
                        "reference_group": f"{reference_key[0]}:{reference_key[1]}",
                        "mean_score_delta": round(mean_delta, 8),
                        "pass_rate_delta": round(pass_delta, 8),
                        "thresholds": thresholds,
                        "requires_human_review": True,
                        "no_individual_penalty": True,
                    },
                    status="open",
                    opened_at=datetime.now(UTC),
                    resolved_at=None,
                )
                alerts.append(alert)
        base_run.status = "completed"
        base_run.limitations = {
            "minimum_sample": policy.minimum_sample,
            "group_counts": group_counts,
            "classification_metrics": "not_applicable_without_ground_truth_labels",
            "causal_interpretation": "not_supported",
            "individual_actions_prohibited": True,
        }
        base_run.finished_at = datetime.now(UTC)
        await self.session.flush()
        await self.repo.write_audit(
            actor_user_id=actor.id,
            action="fairness_metric.run",
            object_type="fairness_metric_run",
            object_id=base_run.id,
            reason="只读取已发布最终成绩，输出聚合指标与不确定性。",
            result_status="completed",
            metadata={
                "policy_id": str(policy.id),
                "dataset_fingerprint": fingerprint,
                "sample_size": sum(len(scores) for scores in grouped_scores.values()),
                "alert_count": len(alerts),
                "no_individual_action": True,
            },
        )
        return self._run_dto(base_run, policy, cells, alerts)

    async def get_metric_run(self, *, actor: User, run_id: UUID) -> FairnessMetricRunDTO:
        await self._require_admin(actor)
        run = await self.repo.get_metric_run(run_id)
        if run is None:
            raise FairnessDomainError("FAIRNESS_RUN_NOT_FOUND", "公平指标运行不存在。", 404)
        policy = await self.repo.get_policy(run.policy_id)
        if policy is None:
            raise FairnessDomainError("FAIRNESS_DATA_MISSING", "公平政策记录缺失。", 409)
        cells = await self.repo.list_metric_cells(run.id) if run.status == "completed" else []
        alerts = await self.repo.list_alerts_for_run(run.id) if run.status == "completed" else []
        return self._run_dto(run, policy, cells, alerts)

    async def dashboard(self, *, actor: User) -> FairnessDashboardDTO:
        await self._require_admin(actor)
        items: list[FairnessMetricRunDTO] = []
        for run, policy in await self.repo.list_metric_runs():
            cells = await self.repo.list_metric_cells(run.id) if run.status == "completed" else []
            alerts = await self.repo.list_alerts_for_run(run.id) if run.status == "completed" else []
            items.append(self._run_dto(run, policy, cells, alerts))
        return FairnessDashboardDTO(
            items=items,
            calculated_at=datetime.now(UTC),
            policy_note="仅管理员可查看聚合指标；默认仅使用经同意的非敏感教学分组，公平信号不会自动影响个人成绩、权限或处分。",
        )

    async def review_alert(
        self, *, actor: User, alert_id: UUID, payload: FairnessReviewRequest
    ) -> FairnessReviewDTO:
        await self._require_admin(actor)
        alert = await self.repo.get_alert(alert_id)
        if alert is None:
            raise FairnessDomainError("FAIRNESS_ALERT_NOT_FOUND", "公平告警不存在。", 404)
        now = datetime.now(UTC)
        alert.status = payload.status
        alert.resolved_at = now if payload.status in {"resolved", "dismissed"} else None
        review = await self.repo.create_review(
            alert_id=alert.id,
            reviewer_id=actor.id,
            status=payload.status,
            reason=payload.reason.strip(),
            outcome_note=payload.outcome_note.strip() if payload.outcome_note else None,
            reviewed_at=now,
        )
        await self.session.flush()
        await self.repo.write_audit(
            actor_user_id=actor.id,
            action="fairness_alert.review",
            object_type="fairness_alert",
            object_id=alert.id,
            reason=payload.reason.strip(),
            result_status=payload.status,
            metadata={"review_id": str(review.id), "no_individual_penalty": True},
        )
        return self._review_dto(review)

    async def create_appeal(
        self, *, actor: User, payload: FairnessAppealCreateRequest
    ) -> FairnessAppealDTO:
        context = await self.repo.get_grade_appeal_context(payload.grade_decision_id)
        if context is None:
            raise FairnessDomainError("FAIRNESS_DATA_MISSING", "成绩记录不存在。", 404)
        grade, submission = context
        if submission.student_id != actor.id or grade.status != "published":
            raise FairnessDomainError(
                "FAIRNESS_ACTION_FORBIDDEN", "只能针对本人已发布成绩提交公平申诉。", 403
            )
        now = datetime.now(UTC)
        appeal = await self.repo.create_appeal(
            grade_decision_id=grade.id,
            appellant_user_id=actor.id,
            reason=payload.reason.strip(),
            status="submitted",
            reviewer_id=None,
            response_note=None,
            submitted_at=now,
            reviewed_at=None,
        )
        await self.repo.write_audit(
            actor_user_id=actor.id,
            action="fairness_appeal.submit",
            object_type="fairness_appeal",
            object_id=appeal.id,
            reason=appeal.reason,
            result_status="submitted",
            metadata={"grade_decision_id": str(grade.id), "automatic_regrade": False},
        )
        return self._appeal_dto(appeal)

    async def resolve_appeal(
        self, *, actor: User, appeal_id: UUID, payload: FairnessAppealResolveRequest
    ) -> FairnessAppealDTO:
        await self._require_admin(actor)
        appeal = await self.repo.get_appeal(appeal_id)
        if appeal is None:
            raise FairnessDomainError("FAIRNESS_APPEAL_NOT_FOUND", "公平申诉不存在。", 404)
        now = datetime.now(UTC)
        appeal.status = payload.status
        appeal.reviewer_id = actor.id
        appeal.response_note = payload.response_note.strip()
        appeal.reviewed_at = now
        await self.session.flush()
        await self.repo.write_audit(
            actor_user_id=actor.id,
            action="fairness_appeal.review",
            object_type="fairness_appeal",
            object_id=appeal.id,
            reason=appeal.response_note,
            result_status=appeal.status,
            metadata={"grade_decision_id": str(appeal.grade_decision_id), "automatic_regrade": False},
        )
        return self._appeal_dto(appeal)

    async def list_appealable_grades(self, *, actor: User) -> AppealableGradeListDTO:
        rows = await self.repo.list_appealable_grade_contexts(actor.id)
        return AppealableGradeListDTO(
            items=[
                AppealableGradeDTO(
                    grade_decision_id=grade.id,
                    submission_id=submission.id,
                    final_score=float(grade.final_score or 0),
                    published_at=grade.published_at,
                )
                for grade, submission in rows
            ]
        )

    async def list_appeals(self, *, actor: User) -> FairnessAppealListDTO:
        await self._require_admin(actor)
        return FairnessAppealListDTO(items=[self._appeal_dto(row) for row in await self.repo.list_appeals()])

    async def _reject_metric_run(
        self,
        *,
        actor: User,
        policy: FairnessPolicy,
        scope: dict[str, Any],
        formula_version: str,
        code: str,
        message: str,
        limitations: dict[str, Any],
    ) -> FairnessMetricRunDTO:
        now = datetime.now(UTC)
        run = await self.repo.create_metric_run(
            policy_id=policy.id,
            assessment_scope=scope,
            dataset_fingerprint=_fingerprint({"policy": str(policy.id), "scope": scope, "error": code}),
            formula_version=formula_version,
            threshold_config={**_DEFAULT_THRESHOLDS, **(policy.thresholds or {}), "pass_score": policy.pass_score},
            status="rejected",
            rejection_code=code,
            limitations={**limitations, "conclusion_hidden": True, "individual_actions_prohibited": True},
            initiated_by=actor.id,
            started_at=now,
            finished_at=now,
        )
        await self.repo.write_audit(
            actor_user_id=actor.id,
            action="fairness_metric.run",
            object_type="fairness_metric_run",
            object_id=run.id,
            reason=message,
            result_status="rejected",
            metadata={"rejection_code": code, "policy_id": str(policy.id)},
        )
        raise FairnessDomainError(code, message, 409)

    async def _require_active_policy(self, policy_id: UUID) -> FairnessPolicy:
        policy = await self.repo.get_policy(policy_id)
        if policy is None or policy.status != "active":
            raise FairnessDomainError("FAIRNESS_POLICY_NOT_ACTIVE", "公平政策不存在或未处于启用状态。", 404)
        return policy

    async def _require_admin(self, actor: User) -> None:
        if not await self.governance_repo.has_active_role(user_id=actor.id, role_code=_ADMIN_ROLE):
            raise FairnessDomainError("ADMIN_ROLE_REQUIRED", "当前账号不具备公平治理管理员权限。")

    @staticmethod
    def _policy_dto(row: FairnessPolicy) -> FairnessPolicyDTO:
        return FairnessPolicyDTO(
            id=row.id,
            code=row.code,
            version_no=row.version_no,
            purpose=row.purpose,
            allowed_group_keys=list(row.allowed_group_keys or []),
            minimum_sample=row.minimum_sample,
            pass_score=row.pass_score,
            retention_days=row.retention_days,
            thresholds=dict(row.thresholds or {}),
            status=row.status,  # type: ignore[arg-type]
            activated_at=row.activated_at,
        )

    @staticmethod
    def _consent_dto(row: FairnessConsent) -> FairnessConsentDTO:
        return FairnessConsentDTO(
            id=row.id,
            policy_id=row.policy_id,
            user_id=row.user_id,
            scope=row.scope,
            status=row.status,  # type: ignore[arg-type]
            granted_at=row.granted_at,
            withdrawn_at=row.withdrawn_at,
            expires_at=row.expires_at,
        )

    @staticmethod
    def _assignment_dto(row: FairnessGroupAssignment) -> FairnessGroupAssignmentDTO:
        return FairnessGroupAssignmentDTO(
            id=row.id,
            user_id=row.user_id,
            policy_id=row.policy_id,
            group_key=row.group_key,
            minimal_group_value=row.minimal_group_value,
            expires_at=row.expires_at,
        )

    @staticmethod
    def _cell_dto(row: FairnessMetricCell) -> FairnessMetricCellDTO:
        return FairnessMetricCellDTO(
            id=row.id,
            group_key=row.group_key,
            group_value=row.group_value,
            sample_size=row.sample_size,
            mean_score=row.mean_score,
            pass_rate=row.pass_rate,
            accuracy=row.accuracy,
            fpr=row.fpr,
            fnr=row.fnr,
            equal_opportunity_delta=row.equal_opportunity_delta,
            confidence_interval=dict(row.confidence_interval or {}),
            limitations=dict(row.limitations or {}),
        )

    @staticmethod
    def _alert_dto(row: FairnessAlert) -> FairnessAlertDTO:
        return FairnessAlertDTO(
            id=row.id,
            metric_cell_id=row.metric_cell_id,
            alert_kind=row.alert_kind,
            severity=row.severity,  # type: ignore[arg-type]
            explanation=dict(row.explanation or {}),
            status=row.status,  # type: ignore[arg-type]
            opened_at=row.opened_at,
            resolved_at=row.resolved_at,
        )

    @classmethod
    def _run_dto(
        cls,
        run: FairnessMetricRun,
        policy: FairnessPolicy,
        cells: Sequence[FairnessMetricCell],
        alerts: Sequence[FairnessAlert],
    ) -> FairnessMetricRunDTO:
        visible_cells = [cls._cell_dto(cell) for cell in cells] if run.status == "completed" else []
        visible_alerts = [cls._alert_dto(alert) for alert in alerts] if run.status == "completed" else []
        return FairnessMetricRunDTO(
            id=run.id,
            policy_id=policy.id,
            policy_version=f"{policy.code}:v{policy.version_no}",
            assessment_scope=dict(run.assessment_scope or {}),
            dataset_fingerprint=run.dataset_fingerprint,
            formula_version=run.formula_version,
            status=run.status,  # type: ignore[arg-type]
            rejection_code=run.rejection_code,
            limitations=dict(run.limitations or {}),
            sample_size=sum(cell.sample_size for cell in visible_cells),
            started_at=run.started_at,
            finished_at=run.finished_at,
            cells=visible_cells,
            alerts=visible_alerts,
        )

    @staticmethod
    def _review_dto(row: FairnessReview) -> FairnessReviewDTO:
        return FairnessReviewDTO(
            id=row.id,
            alert_id=row.alert_id,
            reviewer_id=row.reviewer_id,
            status=row.status,  # type: ignore[arg-type]
            reason=row.reason,
            outcome_note=row.outcome_note,
            reviewed_at=row.reviewed_at,
        )

    @staticmethod
    def _appeal_dto(row: FairnessAppeal) -> FairnessAppealDTO:
        return FairnessAppealDTO(
            id=row.id,
            grade_decision_id=row.grade_decision_id,
            appellant_user_id=row.appellant_user_id,
            reason=row.reason,
            status=row.status,  # type: ignore[arg-type]
            reviewer_id=row.reviewer_id,
            response_note=row.response_note,
            submitted_at=row.submitted_at,
            reviewed_at=row.reviewed_at,
        )


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _iso_or_empty(value: datetime | None) -> str:
    return _as_utc(value).isoformat() if value is not None else ""


def _fingerprint(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _aggregate(scores: Sequence[float], *, pass_score: float) -> dict[str, Any]:
    n = len(scores)
    mean = sum(scores) / n
    pass_count = sum(1 for value in scores if value >= pass_score)
    variance = sum((value - mean) ** 2 for value in scores) / max(n - 1, 1)
    mean_margin = 1.96 * math.sqrt(variance / n)
    pass_rate = pass_count / n
    wilson_low, wilson_high = _wilson_interval(pass_count, n)
    return {
        "sample_size": n,
        "mean_score": round(mean, 8),
        "pass_rate": round(pass_rate, 8),
        "confidence_interval": {
            "confidence_level": 0.95,
            "mean_score_95": [round(mean - mean_margin, 8), round(mean + mean_margin, 8)],
            "pass_rate_95_wilson": [round(wilson_low, 8), round(wilson_high, 8)],
            "method": "t_approx_mean_and_wilson_binomial",
        },
    }


def _wilson_interval(successes: int, total: int) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    z = 1.96
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)
