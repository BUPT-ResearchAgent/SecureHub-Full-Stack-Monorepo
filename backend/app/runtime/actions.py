# Status: real

"""Deterministic Workflow Actions owned by RuntimeEngine, not by models."""

from __future__ import annotations

import json
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
        raise ValueError(f"unknown deterministic workflow action: {action_name}")

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
        from app.db.models.learning.learning_path import LearningPath

        user_id = self._required_uuid(root_input.get("user_id"))
        output = dict((state.get("generate_path") or {}).get("output") or {})
        path = LearningPath(
            user_id=user_id,
            course_id=self._course_id(root_input.get("course_id")),
            title=str(output.get("title") or "Personalised learning path"),
            objective=str(root_input.get("query") or ""),
            status="active",
            metadata_={"nodes": output.get("nodes", []), "edges": output.get("edges", []), "milestones": output.get("milestones", [])},
        )
        self.session.add(path)
        await self.session.flush()
        return {
            "learning_path_id": str(path.id),
            "course_id": str(path.course_id),
            "path": output.get("nodes", []),
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
    def _as_float(value: Any) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None


__all__ = ["WorkflowActionService"]
