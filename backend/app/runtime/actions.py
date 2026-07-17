# Status: real

"""Deterministic Workflow Actions owned by RuntimeEngine, not by models."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seeds._constants import COURSE_WEBSEC_ID
from app.runtime.artifacts.saga import ArtifactSaga
from app.runtime.harness.context import ExecutionContext
from app.services.storage import StorageService


class WorkflowActionService:
    def __init__(self, session: AsyncSession, *, storage_service: StorageService | None = None) -> None:
        self.session = session
        self.storage_service = storage_service or StorageService(session)

    async def __call__(
        self,
        action_name: str,
        root_input: dict[str, Any],
        state: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        if action_name == "PersistGeneratedResource":
            return await self.persist_generated_resource(root_input, state, context)
        if action_name == "PersistResourceFanout":
            return await self.persist_resource_fanout(root_input, state, context)
        if action_name == "PersistProfile":
            return await self.persist_profile(root_input, state, context)
        if action_name == "PersistLearningPath":
            return await self.persist_learning_path(root_input, state, context)
        if action_name == "PersistCapability":
            return await self.persist_capability(root_input, state, context)
        if action_name == "PersistAssessmentFeedback":
            return await self.persist_assessment_feedback(root_input, state, context)
        if action_name == "ProjectTutorAnswer":
            return await self.project_tutor_answer(root_input, state, context)
        if action_name == "ProjectFundRecommendation":
            return await self.project_fund_recommendation(root_input, state, context)
        raise ValueError(f"unknown deterministic workflow action: {action_name}")

    async def project_fund_recommendation(
        self,
        root_input: dict[str, Any],
        state: dict[str, Any],
        _context: ExecutionContext,
    ) -> dict[str, Any]:
        """Project only a QualityCheck-accepted, evidence-linked fund result."""
        from app.schemas.fund_recommendation import FundRecommendationResult

        quality = dict((state.get("quality_check") or {}).get("output") or {})
        if quality.get("accept") is not True:
            raise ValueError("fund recommendation terminal action requires QualityCheck acceptance")

        recommendation_state = dict(state.get("recommend_funds") or {})
        recommendation = dict(recommendation_state.get("output") or {})
        evidence_snapshot_ids = [
            str(value)
            for value in recommendation_state.get("evidence_snapshot_ids") or []
            if self._optional_uuid(value) is not None
        ]
        if len(evidence_snapshot_ids) < 3:
            raise ValueError("accepted fund recommendation is missing the evidence floor")

        snapshot = dict(root_input.get("profile_snapshot") or {})
        allowed_dimensions = {
            str(key)
            for key in dict(snapshot.get("dimensions") or {})
            if isinstance(key, str) and key.strip()
        }
        allowed_dimensions.update(
            str(item.get("dimension"))
            for item in snapshot.get("capabilities") or []
            if isinstance(item, dict) and isinstance(item.get("dimension"), str) and item["dimension"].strip()
        )
        raw_recommendations = list(recommendation.get("fund_recommendations") or [])
        if not raw_recommendations:
            raise ValueError("accepted fund recommendation is missing recommendations")
        projected: list[dict[str, Any]] = []
        for item in raw_recommendations[:3]:
            if not isinstance(item, dict):
                raise ValueError("fund recommendation item is not an object")
            matches = self._canonical_profile_dimensions(
                item.get("matched_profile_dimensions"),
                allowed_dimensions,
            )
            if not matches:
                raise ValueError("fund recommendation cites profile dimensions outside the durable snapshot")
            projected.append({**item, "matched_profile_dimensions": matches, "evidence_snapshot_ids": evidence_snapshot_ids})

        landscape = dict((state.get("analyse_fund_landscape") or {}).get("output") or {})
        result = FundRecommendationResult.model_validate(
            {
                "recommendations": projected,
                "landscape_summary": str(landscape.get("trend") or recommendation.get("content") or ""),
                "profile_dimensions_used": sorted(
                    {dimension for item in projected for dimension in item["matched_profile_dimensions"]}
                ),
                "evidence_snapshot_ids": evidence_snapshot_ids,
            }
        )
        return result.model_dump(mode="json")

    @staticmethod
    def _canonical_profile_dimensions(value: Any, allowed_dimensions: set[str]) -> list[str]:
        """Map harmless display suffixes back to the durable profile keys.

        Fund prompts ask for a persisted dimension name, but providers commonly
        append a score or value (for example ``web_security (1.0)``).  The
        terminal projection retains only the exact durable key and still
        rejects a label that cannot be unambiguously traced to that snapshot.
        """
        matches: list[str] = []
        # These are display aliases of existing profile keys, not a second
        # profile taxonomy. Some Chinese provider responses translate the
        # bounded keys despite the output contract requesting the key itself.
        aliases: dict[str, tuple[str, ...]] = {
            "Web安全": ("web_security",),
            "网络安全": ("network_security",),
            "系统安全": ("system_security",),
            "网络与系统安全": ("network_security", "system_security"),
            "AI安全": ("ai_security",),
            "工程实践": ("engineering_practice",),
            "学术写作": ("academic_writing",),
            "兴趣锚点": ("interest_anchors",),
            "职业目标": ("career_goal",),
            "认知风格": ("cognitive_style",),
            "知识基础": ("knowledge_basis",),
            "学习节奏": ("learning_pace",),
            "易错点": ("easy_mistakes",),
        }
        for raw_value in value if isinstance(value, list) else []:
            if not isinstance(raw_value, str):
                continue
            label = raw_value.strip()
            canonical = next(
                (
                    dimension
                    for dimension in sorted(allowed_dimensions, key=len, reverse=True)
                    if label == dimension
                    or (
                        label.startswith(dimension)
                        and len(label) > len(dimension)
                        and label[len(dimension)] in {" ", "(", "（", ":", "："}
                    )
                ),
                None,
            )
            resolved = (canonical,) if canonical is not None else next(
                (
                    dimensions
                    for alias, dimensions in aliases.items()
                    if label == alias
                    or (
                        label.startswith(alias)
                        and len(label) > len(alias)
                        and label[len(alias)] in {" ", "(", "（", ":", "："}
                    )
                ),
                (),
            )
            for dimension in resolved:
                if dimension in allowed_dimensions and dimension not in matches:
                    matches.append(dimension)
        return matches

    async def project_tutor_answer(
        self,
        _root_input: dict[str, Any],
        state: dict[str, Any],
        _context: ExecutionContext,
    ) -> dict[str, Any]:
        """Expose only the accepted learner answer as a tutor workflow terminal value."""
        answer = dict((state.get("answer") or {}).get("output") or {})
        content = answer.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("accepted tutor answer is missing learner-facing content")
        resources = answer.get("resources")
        return {
            "content": content.strip(),
            "resources": resources if isinstance(resources, list) else [],
            "quality_score": self._as_float(answer.get("quality_score")),
        }

    async def persist_generated_resource(
        self,
        root_input: dict[str, Any],
        state: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        resource_type = str(root_input.get("resource_type") or "doc")
        recovered = await self._recover_existing_resource(resource_type, context)
        if recovered is not None:
            return recovered

        producer = state.get("producer") or {}
        output = dict(producer.get("output") or {})
        quality = dict((state.get("quality_check") or {}).get("output") or {})
        title = str(output.get("title") or f"{resource_type}: {root_input.get('query', 'SecureHub resource')}")[:240]
        encoded = json.dumps(output, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        resource_content = {"schema_version": "v1", "output": output}
        evidence_ids = self._uuid_list(output.get("evidence_chunk_ids") or [])
        options = dict(root_input.get("options") or {})
        saga = ArtifactSaga(self.session, self.storage_service)
        staged = await saga.stage(
            workflow_run_id=context.workflow_run_id,
            step_attempt_id=context.step_attempt_id,
            agent_run_id=producer.get("agent_run_id"),
            resource_type=resource_type,
            title=title,
            content=encoded,
            resource_content=resource_content,
            user_id=root_input.get("user_id"),
            course_id=self._course_id(root_input.get("course_id")),
            kp_id=self._optional_uuid(root_input.get("kp_id")),
            evidence_chunk_ids=evidence_ids,
            quality_score=self._as_float(quality.get("quality_score") or output.get("quality_score")),
            mime_type="application/json",
            metadata={
                "quality_defects": quality.get("defects", []),
                "evidence_snapshot_ids": list(producer.get("evidence_snapshot_ids") or []),
            },
            parent_resource_id=options.get("parent_resource_id"),
            lease_epoch=context.lease_epoch,
        )
        # Stage metadata + hidden outbox event must survive before activation.
        await self.session.commit()
        active = await saga.activate(staged.storage_object_id, lease_epoch=context.lease_epoch)
        await self.session.commit()
        from app.db.models.resource.generated_resource import GeneratedResource

        resource = await self.session.get(GeneratedResource, active.resource_id)
        assert resource is not None
        return self._resource_result(resource)

    async def _recover_existing_resource(
        self,
        resource_type: str,
        context: ExecutionContext,
    ) -> dict[str, Any] | None:
        """Finish or reuse a staged artifact after a process loss.

        An action step can die after ArtifactSaga durably activates one branch
        but before its step output is persisted. The existing resource is the
        authority for that `(root, resource_type)` effect; a resumed action
        receives a new step attempt, so it must not create a second artifact
        merely to reconstruct output.
        """
        from sqlalchemy import select

        from app.db.models.resource.generated_resource import GeneratedResource
        from app.db.models.storage.storage_object import StorageObject

        rows = list(
            (
                await self.session.execute(
                    select(GeneratedResource)
                    .where(
                        GeneratedResource.workflow_run_id == context.workflow_run_id,
                        GeneratedResource.resource_type == resource_type,
                        GeneratedResource.status.in_(("staging", "active")),
                    )
                    .order_by(GeneratedResource.created_at.desc())
                )
            ).scalars().all()
        )
        for resource in rows:
            if resource.status == "staging":
                storage = await self.session.scalar(
                    select(StorageObject)
                    .where(
                        StorageObject.status == "staging",
                        StorageObject.metadata_["resource_id"].as_string() == str(resource.id),
                    )
                    .limit(1)
                )
                if storage is not None:
                    saga = ArtifactSaga(self.session, self.storage_service)
                    await saga.activate(storage.id, lease_epoch=context.lease_epoch)
                    await self.session.commit()
                    await self.session.refresh(resource)
            if resource.status == "active":
                return self._resource_result(resource)
        return None

    @staticmethod
    def _resource_result(resource: Any) -> dict[str, Any]:
        metadata = dict(resource.metadata_ or {})
        return {
            "resource_id": str(resource.id),
            "resource_type": resource.resource_type,
            "object_key": resource.object_key,
            "storage_status": resource.status,
            "quality_score": resource.quality_score,
            "evidence_snapshot_ids": [str(value) for value in metadata.get("evidence_snapshot_ids") or []],
            "version": int(resource.version),
            "parent_resource_id": str(resource.parent_resource_id) if resource.parent_resource_id else None,
            "lineage_root_id": str(resource.lineage_root_id or resource.id),
        }

    async def persist_resource_fanout(
        self,
        root_input: dict[str, Any],
        state: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Persist each quality-approved branch as a distinct typed ArtifactRef."""
        # v1 contains four branches; v2 adds mindmap and video.  Persist only
        # producer nodes present in the recorded state so old v1 roots retain
        # their exact four-artifact behaviour.
        resource_types = {
            "resource_doc": "doc",
            "resource_ppt": "ppt",
            "resource_mindmap": "mindmap",
            "resource_quiz": "quiz",
            "resource_lab": "lab",
            "resource_video": "video",
            "resource_readings": "readings",
        }
        resources: list[dict[str, Any]] = []
        quality = state.get("quality_check") or {}
        for node_id, resource_type in resource_types.items():
            producer = state.get(node_id)
            if not isinstance(producer, dict):
                continue
            result = await self.persist_generated_resource(
                {**root_input, "resource_type": resource_type},
                {"producer": producer, "quality_check": quality},
                context,
            )
            result["producer_node_id"] = node_id
            resources.append(result)
        if not resources:
            raise ValueError("parallel resource workflow has no producer output to persist")
        return {
            "resources": resources,
            "resource_ids": [item["resource_id"] for item in resources],
            "quality_score": self._as_float(((quality.get("output") or {}) if isinstance(quality, dict) else {}).get("quality_score")),
        }

    async def persist_profile(
        self,
        root_input: dict[str, Any],
        state: dict[str, Any],
        _context: ExecutionContext,
    ) -> dict[str, Any]:
        from app.db.models.identity.user_profile import UserProfile

        user_id = self._required_uuid(root_input.get("user_id"))
        producer = state.get("build_persona") or state.get("update_persona") or {}
        output = dict(producer.get("output") or {})
        dimensions = output.get("dimensions") if isinstance(output.get("dimensions"), dict) else {}
        row = await self.session.get(UserProfile, user_id)
        if row is None:
            row = UserProfile(user_id=user_id, dimensions=dict(dimensions))
            self.session.add(row)
        else:
            row.dimensions = {**dict(row.dimensions or {}), **dict(dimensions)}
        await self.session.flush()
        persisted: dict[str, Any] = {
            "user_id": str(user_id),
            "dimensions": dict(row.dimensions or {}),
            "quality_score": self._as_float(output.get("quality_score")),
        }
        # Keep the learner-facing reply in the durable terminal output.  The
        # profile row remains the source of truth for dimensions, while a
        # reconnecting UI can recover the associated follow-up question.
        for key in ("content", "next_question"):
            value = output.get(key)
            if isinstance(value, str) and value.strip():
                persisted[key] = value.strip()
        # Assessment workflows end by persisting the persona. Preserve the
        # independently persisted assessment/capability result in that final
        # action output so the synchronous compatibility adapter has one
        # durable, queryable terminal response rather than model-only state.
        assessment = dict((state.get("run_assessment") or {}).get("output") or {})
        capability = dict((state.get("persist_capability") or {}).get("output") or {})
        if assessment:
            updated_capabilities = list(capability.get("updated_capabilities") or [])
            assessment["updated_capabilities"] = updated_capabilities
            persisted["assessment"] = assessment
            for key in ("score", "overall_score", "feedback", "next_recommendation"):
                if key in assessment:
                    persisted[key] = assessment[key]
            persisted["updated_capabilities"] = updated_capabilities
        return persisted

    async def persist_learning_path(
        self,
        root_input: dict[str, Any],
        state: dict[str, Any],
        _context: ExecutionContext,
    ) -> dict[str, Any]:
        from sqlalchemy import select

        from app.db.models.knowledge.knowledge_node import KnowledgeNode
        from app.db.models.learning.learning_path import LearningPath
        from app.db.models.learning.learning_task import LearningTask

        user_id = self._required_uuid(root_input.get("user_id"))
        course_id = self._course_id(root_input.get("course_id"))
        output = dict((state.get("generate_path") or {}).get("output") or {})
        task_specs = self._normalise_generated_path_tasks(output.get("nodes"))

        # A model may use an opaque identifier in a path node.  Only retain a
        # typed knowledge-node relation when it belongs to this course; the
        # original identifier remains traceable in task metadata either way.
        requested_kp_ids = {item["kp_id"] for item in task_specs if item["kp_id"] is not None}
        if requested_kp_ids:
            durable_kp_ids = set(
                (
                    await self.session.execute(
                        select(KnowledgeNode.id).where(
                            KnowledgeNode.id.in_(requested_kp_ids),
                            KnowledgeNode.course_id == course_id,
                        )
                    )
                ).scalars()
            )
            for item in task_specs:
                if item["kp_id"] not in durable_kp_ids:
                    item["kp_id"] = None

        # Validate and materialise the new path before retiring the existing
        # projection.  This keeps a malformed model result from replacing the
        # learner's last usable active path.
        active_paths = list(
            (
                await self.session.execute(
                    select(LearningPath).where(
                        LearningPath.user_id == user_id,
                        LearningPath.course_id == course_id,
                        LearningPath.status == "active",
                    )
                )
            ).scalars()
        )
        path = LearningPath(
            user_id=user_id,
            course_id=course_id,
            title=str(output.get("title") or "Personalised learning path"),
            objective=str(root_input.get("query") or ""),
            status="active",
            metadata_={
                "nodes": output.get("nodes", []),
                "edges": output.get("edges", []),
                "milestones": output.get("milestones", []),
            },
        )
        self.session.add(path)
        await self.session.flush()
        for item in task_specs:
            self.session.add(
                LearningTask(
                    path_id=path.id,
                    kp_id=item["kp_id"],
                    title=item["title"],
                    task_type=item["task_type"],
                    order_index=item["order_index"],
                    status=item["status"],
                    metadata_=item["metadata"],
                )
            )
        await self.session.flush()
        for active_path in active_paths:
            active_path.status = "superseded"
        await self.session.flush()
        return {
            "learning_path_id": str(path.id),
            "course_id": str(path.course_id),
            "path": output.get("nodes", []),
            "task_count": len(task_specs),
            "quality_score": self._as_float(output.get("quality_score")),
        }

    async def persist_capability(
        self,
        root_input: dict[str, Any],
        state: dict[str, Any],
        _context: ExecutionContext,
    ) -> dict[str, Any]:
        from sqlalchemy import select

        from app.db.models.identity.user_capability import UserCapability

        user_id = self._required_uuid(root_input.get("user_id"))
        output = dict((state.get("update_capability") or {}).get("output") or {})
        delta = output.get("delta") or output.get("capability_delta") or {}
        if not isinstance(delta, dict):
            delta = {}
        persisted: list[dict[str, Any]] = []
        for dimension, value in delta.items():
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            row = await self.session.scalar(
                select(UserCapability).where(UserCapability.user_id == user_id, UserCapability.dimension == str(dimension))
            )
            if row is None:
                row = UserCapability(user_id=user_id, dimension=str(dimension), score=max(0.0, min(1.0, 0.5 + numeric)), confidence=0.7, evidence_count=0)
                self.session.add(row)
            else:
                row.score = max(0.0, min(1.0, float(row.score) + numeric))
                row.confidence = max(float(row.confidence), 0.7)
            persisted.append({"dimension": str(dimension), "score": row.score, "confidence": row.confidence})
        await self.session.flush()
        return {"user_id": str(user_id), "updated_capabilities": persisted}

    async def persist_assessment_feedback(
        self,
        root_input: dict[str, Any],
        state: dict[str, Any],
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Atomically apply an accepted assessment's capability and persona effects.

        The savepoint is intentional: RuntimeEngine commits every action step
        after it settles the durable step attempt. A nested transaction keeps
        a validation or profile failure from leaking the capability mutation
        into that failure commit.
        """
        from sqlalchemy import select

        from app.db.models.identity.user_capability import UserCapability
        from app.db.models.identity.user_profile import UserProfile

        user_id = self._required_uuid(root_input.get("user_id"))
        assessment = dict((state.get("run_assessment") or {}).get("output") or {})
        capability = dict((state.get("update_capability") or {}).get("output") or {})
        persona = dict((state.get("update_persona") or {}).get("output") or {})
        score_contract = self._assessment_score_contract(root_input)
        model_score = self._unit_score(assessment.get("score"))
        objective_floor_score = (
            score_contract["objective_floor_score"]
            if score_contract is not None
            else None
        )
        score_reconciled = (
            model_score is not None
            and objective_floor_score is not None
            and model_score < objective_floor_score
        )
        if score_reconciled:
            # The objective floor is derived from the real frozen version and
            # durable submission before a model sees any prompt projection.
            # Do not persist a lower model score merely because a bounded
            # answer transport was mistaken for an incomplete response.
            assessment = dict(assessment)
            assessment["score"] = objective_floor_score
            assessment["feedback"] = (
                "已按当前已发布冻结题目与持久化提交核验客观部分："
                f"{score_contract['objective_earned_points']:g}/"
                f"{score_contract['objective_total_points']:g} 分；"
                f"完整试卷当前可核验得分下限为 {objective_floor_score:.0%}。"
                "主观题仍以本次 Evidence 关联的评估反馈为准。"
            )
            assessment["next_recommendation"] = (
                "继续查看本次评估关联的课程 Evidence 与主观题反馈；"
                "后续路径将以已核验的客观题结果重新排序。"
            )
        proposed_delta = capability.get("capability_delta") or capability.get("delta") or assessment.get("capability_delta")
        if score_reconciled:
            # A negative model delta cannot be allowed to contradict a
            # server-verified lower-bound score. The durable capability write
            # below therefore reconciles Web security to that bound and
            # records the source in the audit rather than inventing a demo
            # delta in the browser.
            proposed_delta = {"web_security": 0.0}
        if not isinstance(proposed_delta, dict) or not proposed_delta:
            raise ValueError("accepted assessment did not produce a capability delta")
        persona_patch = persona.get("dimensions") or persona.get("updated_dimensions") or {}
        if not isinstance(persona_patch, dict):
            raise ValueError("persona update did not produce a dimensions patch")
        allowed_capability_dimensions = {
            str(value).strip()
            for value in root_input.get("capability_dimensions", [])
            if isinstance(value, str) and value.strip()
        }
        allowed_persona_dimension_keys = {
            str(value).strip()
            for value in root_input.get("persona_dimension_keys", [])
            if isinstance(value, str) and value.strip()
        }
        evidence_snapshot_ids = [
            str(value)
            for value in ((state.get("run_assessment") or {}).get("evidence_snapshot_ids") or [])
            if self._optional_uuid(value) is not None
        ]
        if not evidence_snapshot_ids:
            raise ValueError("accepted assessment is missing evidence snapshots")

        async with self.session.begin_nested():
            changes: list[dict[str, Any]] = []
            for dimension, delta, source_dimensions in self._normalise_assessment_capability_deltas(
                proposed_delta,
                allowed_capability_dimensions=allowed_capability_dimensions,
                domain=str(root_input.get("domain") or ""),
            ):
                row = await self.session.scalar(
                    select(UserCapability).where(
                        UserCapability.user_id == user_id,
                        UserCapability.dimension == str(dimension),
                    )
                )
                # A model cannot create an unassessed capability baseline.
                # The product seed/profile flow owns first-row creation.
                if row is None:
                    continue
                before_score = float(row.score)
                applied_delta = delta
                applied_sources = source_dimensions
                if score_reconciled and dimension == "web_security":
                    # The floor covers the entire assessment denominator, so
                    # moving an older lower capability up to it is
                    # conservative. A higher existing capability remains
                    # unchanged pending a non-conflicting full evaluation.
                    applied_delta = max(0.0, objective_floor_score - before_score)
                    applied_sources = ["server_verified_objective_floor"]
                row.score = max(0.0, min(1.0, before_score + applied_delta))
                row.evidence_count = int(row.evidence_count) + len(evidence_snapshot_ids)
                changes.append(
                    {
                        "dimension": str(dimension),
                        "before_score": before_score,
                        "after_score": float(row.score),
                        "delta": float(row.score) - before_score,
                        "confidence": float(row.confidence),
                        "evidence_count": int(row.evidence_count),
                        "source_dimensions": applied_sources,
                    }
                )
            if not changes:
                raise ValueError("accepted assessment did not target an existing capability")

            profile = await self.session.get(UserProfile, user_id)
            before_dimensions = dict(profile.dimensions or {}) if profile is not None else {}
            persona_projection = "model"
            if allowed_persona_dimension_keys:
                # The assessment agent may describe a learner gap, but it
                # cannot replace a profile field. V2 writes only a bounded,
                # append-only review item derived from the accepted feedback.
                persona_patch = self._assessment_persona_fallback(
                    before_dimensions,
                    assessment=assessment,
                    allowed_keys=allowed_persona_dimension_keys,
                )
                persona_projection = "assessment_feedback" if persona_patch else "none"
            unexpected_persona_keys = set(map(str, persona_patch)) - allowed_persona_dimension_keys
            if allowed_persona_dimension_keys and unexpected_persona_keys:
                raise ValueError("persona update included a non-profile dimension")
            after_dimensions = {**before_dimensions, **persona_patch}
            if profile is None:
                profile = UserProfile(user_id=user_id, dimensions=after_dimensions)
                self.session.add(profile)
            else:
                profile.dimensions = after_dimensions
            changed_dimensions = [
                {"dimension": str(key), "before": before_dimensions.get(key), "after": value}
                for key, value in persona_patch.items()
                if before_dimensions.get(key) != value
            ]
            if allowed_persona_dimension_keys and not changed_dimensions:
                raise ValueError("accepted assessment did not produce a persona change")
            await self.session.flush()

        scoring_audit = (
            {
                **score_contract,
                "model_score": model_score,
                "effective_score": self._unit_score(assessment.get("score")),
                "reconciled": score_reconciled,
                "model_feedback": str(
                    dict((state.get("run_assessment") or {}).get("output") or {}).get("feedback")
                    or ""
                )[:1_200],
            }
            if score_contract is not None
            else None
        )
        assessment_payload = {
            key: assessment[key]
            for key in ("score", "overall_score", "feedback", "capability_delta", "weak_kp_ids", "next_recommendation")
            if key in assessment
        }
        if scoring_audit is not None:
            assessment_payload["scoring"] = scoring_audit
        assessment_payload["updated_capabilities"] = [
            {
                "dimension": item["dimension"],
                "score": item["after_score"],
                "confidence": item["confidence"],
                "evidence_count": item["evidence_count"],
            }
            for item in changes
        ]
        context_payload = root_input.get("context") if isinstance(root_input.get("context"), dict) else {}
        reasons = [
            {
                "dimension": item["dimension"],
                "delta": item["delta"],
                "effect": self._path_effect(item),
            }
            for item in changes
        ]
        recommendation = assessment.get("next_recommendation")
        return {
            "user_id": str(user_id),
            "assessment": assessment_payload,
            "updated_capabilities": assessment_payload["updated_capabilities"],
            "assessment_audit": {
                "schema_version": 1,
                "root_run_id": str(context.workflow_run_id),
                "occurred_at": datetime.now(UTC).isoformat(),
                "quiz": {
                    "artifact_id": root_input.get("quiz_artifact_id"),
                    "knowledge_point_id": context_payload.get("kp_id"),
                    "answered_count": len(root_input.get("answers") or []),
                    "submitted_answers": self._assessment_answers_for_audit(root_input.get("answers")),
                },
                "scoring": scoring_audit,
                "evidence_snapshot_ids": evidence_snapshot_ids,
                "capability_changes": changes,
                "persona": {
                    "before_dimensions": before_dimensions,
                    "after_dimensions": after_dimensions,
                    "changed_dimensions": changed_dimensions,
                    "projection": persona_projection,
                },
                "recommendation": {
                    "previous": None,
                    "next": recommendation if isinstance(recommendation, str) and recommendation.strip() else None,
                    "reasons": reasons,
                },
            },
        }

    @staticmethod
    def _assessment_score_contract(root_input: dict[str, Any]) -> dict[str, float | str] | None:
        """Read only a server-verified objective scoring floor from root input.

        The regular API replaces browser answers with this projection only
        after it has matched a published frozen submission. The final action
        still verifies the canonical context and arithmetic so an arbitrary
        generic workflow payload cannot use this path to claim a score.
        """

        context = root_input.get("context")
        if (
            not isinstance(context, dict)
            or context.get("assessment_source") != "server_verified_published_submission"
        ):
            return None
        answers = root_input.get("answers")
        if not isinstance(answers, list):
            return None
        summary: dict[str, Any] | None = None
        for answer in answers:
            if isinstance(answer, dict) and isinstance(answer.get("assessment_summary"), dict):
                summary = dict(answer["assessment_summary"])
                break
        if summary is None or summary.get("source") != "server_verified_published_submission":
            return None
        scoring = summary.get("scoring")
        if (
            not isinstance(scoring, dict)
            or scoring.get("source") != "server_verified_frozen_objective_items"
        ):
            return None
        try:
            earned = float(scoring["objective_earned_points"])
            objective_total = float(scoring["objective_total_points"])
            total = float(scoring["total_assessment_points"])
            floor = float(scoring["objective_floor_score"])
        except (KeyError, TypeError, ValueError):
            return None
        if (
            earned < 0.0
            or objective_total < 0.0
            or total <= 0.0
            or earned > objective_total
            or objective_total > total
            or floor < 0.0
            or floor > 1.0
            or abs(floor - earned / total) > 0.000_001
        ):
            return None
        return {
            "source": "server_verified_frozen_objective_items",
            "objective_earned_points": earned,
            "objective_total_points": objective_total,
            "total_assessment_points": total,
            "objective_floor_score": floor,
        }

    @staticmethod
    def _unit_score(value: Any) -> float | None:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return None
        return score if 0.0 <= score <= 1.0 else None

    @staticmethod
    def _normalise_assessment_capability_deltas(
        proposed_delta: dict[str, Any],
        *,
        allowed_capability_dimensions: set[str],
        domain: str,
    ) -> list[tuple[str, float, list[str]]]:
        """Map assessment sub-concepts to an existing durable capability only.

        ``RunAssessment`` evaluates concrete learning concepts, while the
        current course profile intentionally exposes the coarser
        ``web_security`` capability. The mapping is explicit, course-domain
        bounded and included in the audit's ``source_dimensions`` field.
        """
        aggregated: dict[str, float] = {}
        sources: dict[str, list[str]] = {}
        for raw_dimension, raw_delta in proposed_delta.items():
            try:
                delta = float(raw_delta)
            except (TypeError, ValueError):
                continue
            dimension = str(raw_dimension).strip()
            if not dimension:
                continue
            if domain == "course_websec" and "web_security" in allowed_capability_dimensions:
                # Course assessment evaluates sub-concepts, while its durable
                # feedback contract owns only the Web security capability.
                # Do not let an otherwise valid profile dimension turn this
                # root into a cross-domain mutation.
                target = "web_security"
            elif not allowed_capability_dimensions or dimension in allowed_capability_dimensions:
                target = dimension
            else:
                continue
            aggregated[target] = aggregated.get(target, 0.0) + delta
            sources.setdefault(target, []).append(dimension)
        return [
            (dimension, delta, sources[dimension])
            for dimension, delta in sorted(aggregated.items())
        ]

    @staticmethod
    def _assessment_persona_fallback(
        before_dimensions: dict[str, Any],
        *,
        assessment: dict[str, Any],
        allowed_keys: set[str],
    ) -> dict[str, Any]:
        """Project an accepted learner-facing gap onto an existing persona key."""
        feedback = assessment.get("feedback")
        if not isinstance(feedback, str) or not feedback.strip():
            return {}
        for key in ("weak_points", "easy_mistakes"):
            if key not in allowed_keys:
                continue
            existing = before_dimensions.get(key)
            values = [str(value) for value in existing] if isinstance(existing, list) else []
            entry = f"评估待复盘：{feedback.strip()[:180]}"
            return {key: list(dict.fromkeys([*values, entry]))}
        return {}

    @staticmethod
    def _assessment_answers_for_audit(value: Any) -> list[dict[str, Any]]:
        """Retain only bounded learner-visible answers in the terminal audit."""
        if not isinstance(value, list):
            return []
        answers: list[dict[str, Any]] = []
        for raw in value[:20]:
            if not isinstance(raw, dict):
                continue
            quiz_item_id = raw.get("quiz_item_id")
            if not isinstance(quiz_item_id, str) or not quiz_item_id.strip():
                continue
            answer = raw.get("answer")
            if isinstance(answer, str):
                projected_answer: str | list[str] = answer.strip()[:800]
            elif isinstance(answer, list):
                projected_answer = [
                    item.strip()[:400]
                    for item in answer[:8]
                    if isinstance(item, str) and item.strip()
                ]
            else:
                continue
            prompt = raw.get("question")
            answers.append(
                {
                    "quiz_item_id": quiz_item_id.strip()[:160],
                    "prompt": prompt.strip()[:800] if isinstance(prompt, str) and prompt.strip() else None,
                    "answer": projected_answer,
                }
            )
        return answers

    @staticmethod
    def _path_effect(change: dict[str, Any]) -> str:
        if change["dimension"] != "web_security":
            return "下一次推荐会使用这项已持久化能力变化。"
        before_score = float(change["before_score"])
        after_score = float(change["after_score"])
        if before_score < 0.7 <= after_score:
            return "已达到加速先修路径阈值，下一次课程路径会优先解锁后续主题。"
        if before_score >= 0.7 > after_score:
            return "低于加速先修路径阈值，下一次课程路径会先巩固基础主题。"
        return "下一次课程路径会按更新后的 Web 安全能力重新排序。"

    @classmethod
    def _normalise_generated_path_tasks(cls, nodes: Any) -> list[dict[str, Any]]:
        """Turn accepted generated nodes into the durable task projection.

        The model's path schema deliberately allows extension fields.  The
        deterministic terminal action therefore keeps only the task fields the
        database owns, preserves opaque node identifiers as metadata, and
        rejects an empty projection before it can become active.
        """
        if not isinstance(nodes, list):
            raise ValueError("generated learning path requires a node list")

        tasks: list[dict[str, Any]] = []
        allowed_statuses = {"todo", "active", "in_progress", "done", "blocked", "locked"}
        for index, raw_node in enumerate(nodes, start=1):
            if not isinstance(raw_node, dict):
                raise ValueError("generated learning path contains a non-object node")
            title = str(raw_node.get("title") or raw_node.get("label") or raw_node.get("name") or "").strip()
            if not title:
                raise ValueError(f"generated learning path node {index} has no task title")
            raw_node_id = (
                raw_node.get("kp_id")
                or raw_node.get("knowledge_node_id")
                or raw_node.get("node_id")
                or raw_node.get("id")
            )
            raw_status = str(raw_node.get("status") or "todo").strip().lower()
            task_metadata = dict(raw_node.get("metadata") or {}) if isinstance(raw_node.get("metadata"), dict) else {}
            if raw_node_id is not None and str(raw_node_id).strip():
                task_metadata["source_node_id"] = str(raw_node_id).strip()[:255]
            description = raw_node.get("description")
            if isinstance(description, str) and description.strip():
                task_metadata["source_description"] = description.strip()[:1_200]
            expected_minutes = cls._bounded_int(
                next(
                    (
                        raw_node[key]
                        for key in ("expected_minutes", "estimated_minutes", "est_minutes")
                        if raw_node.get(key) is not None
                    ),
                    0,
                ),
                default=0,
            )
            task_metadata["expected_minutes"] = expected_minutes
            task_type = str(raw_node.get("task_type") or raw_node.get("type") or "course_learning").strip()[:64]
            tasks.append(
                {
                    "kp_id": cls._optional_uuid(raw_node_id),
                    "title": title[:240],
                    "task_type": task_type or "course_learning",
                    "order_index": index,
                    "status": raw_status if raw_status in allowed_statuses else "todo",
                    "metadata": task_metadata,
                }
            )
        if not tasks:
            raise ValueError("generated learning path has no materialisable learning tasks")
        return tasks

    @staticmethod
    def _required_uuid(value: Any) -> UUID:
        parsed = WorkflowActionService._optional_uuid(value)
        if parsed is None:
            raise ValueError("workflow action requires a UUID user id")
        return parsed

    @staticmethod
    def _optional_uuid(value: Any) -> UUID | None:
        if value is None:
            return None
        try:
            return UUID(str(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _course_id(value: Any) -> UUID:
        return WorkflowActionService._optional_uuid(value) or COURSE_WEBSEC_ID

    @staticmethod
    def _uuid_list(values: list[Any]) -> list[UUID]:
        return [parsed for item in values if (parsed := WorkflowActionService._optional_uuid(item)) is not None]

    @staticmethod
    def _bounded_int(value: Any, *, default: int) -> int:
        try:
            return max(0, min(600, int(value)))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _as_float(value: Any) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None


__all__ = ["WorkflowActionService"]
