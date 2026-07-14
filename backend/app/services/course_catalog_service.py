# Status: real

"""Data-backed catalog, knowledge graph, path, and progress projections.

Ready-course progress is intentionally persisted inside the course product's
existing ``user_capabilities`` dimension.  Preview products return an honest
empty projection and never write learner progress, evidence, or artifacts.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.identity.user_capability import UserCapability
from app.db.models.knowledge.course import Course
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.db.seeds._constants import (
    COURSE_PRODUCTS,
    COURSE_PRODUCT_BY_CODE,
    CourseProductDefinition,
    LEGACY_SMOKE_COURSE_WEBSEC_ID,
)
from app.repositories.course_learning import CourseLearningRepository
from app.repositories.identity.capabilities import UserCapabilityRepository
from app.schemas.course_product import (
    CourseCatalogItemDTO,
    CourseChapterDTO,
    CourseDetailDTO,
    CourseGraphDTO,
    CourseGraphEdgeDTO,
    CourseKnowledgePointDTO,
    CoursePathDTO,
    CoursePathNodeDTO,
    CourseProgressDTO,
)

_PROGRESS_KEY = "course_progress"
_PROGRESS_SCHEMA_VERSION = 1


class CourseProductNotFoundError(LookupError):
    pass


class CourseProgressValidationError(ValueError):
    pass


class CourseContentNotReadyError(RuntimeError):
    """A real-content action was requested for a catalogue-only preview."""


class CourseCatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = CourseLearningRepository(session)
        self.capabilities = UserCapabilityRepository(session)

    async def list_catalog(self, *, user_id: UUID) -> list[CourseCatalogItemDTO]:
        # The product manifest fixes user-visible ordering.  The legacy smoke
        # course remains compatible with historical resources but never
        # appears as a fifth catalogue item.
        courses_by_code = {course.code: course for course in await self.repository.list_courses()}
        ordered: list[Course] = []
        for product in COURSE_PRODUCTS:
            course = courses_by_code.get(product.code)
            if course is None or course.id != product.id:
                raise CourseProductNotFoundError(f"course product {product.code} is not seeded")
            ordered.append(course)
        return [await self._catalog_item(course, user_id=user_id) for course in ordered]

    async def get_detail(self, *, course_id: UUID, user_id: UUID) -> CourseDetailDTO:
        course = await self._require_course(course_id)
        product = self._product_for(course)
        if product.content_status == "preview":
            return self._preview_detail(course, product)
        nodes = list(await self.repository.list_nodes(course.id))
        resource_counts = await self.repository.resource_counts(
            course_ids=_resource_course_ids(course, product), user_id=user_id
        )
        documents = await self.repository.list_evidence_documents(course.domain)
        evidence_by_slug, platforms = _evidence_by_slug(documents)
        progress = await self.get_progress(course_id=course.id, user_id=user_id, nodes=nodes)
        coverage = _chapter_coverage(nodes, evidence_by_slug, product)
        catalog_item = self._catalog_from_parts(
            course,
            product=product,
            nodes=nodes,
            resource_counts=resource_counts,
            evidence_by_slug=evidence_by_slug,
            progress=progress,
            coverage=coverage,
        )
        knowledge_points = [
            _node_dto(node, resource_count=resource_counts.get(node.id, 0), evidence_count=len(evidence_by_slug.get(_slug(node), set())))
            for node in nodes
        ]
        return CourseDetailDTO(
            **catalog_item.model_dump(),
            chapters=coverage,
            knowledge_points=knowledge_points,
            source_platforms=platforms,
            source_manifest=product.source_manifest,
        )

    async def get_graph(self, *, course_id: UUID, user_id: UUID) -> CourseGraphDTO:
        course = await self._require_course(course_id)
        product = self._product_for(course)
        if product.content_status == "preview":
            return CourseGraphDTO(course_id=course.id, nodes=[], edges=[])
        nodes = list(await self.repository.list_nodes(course.id))
        resources = await self.repository.resource_counts(
            course_ids=_resource_course_ids(course, product), user_id=user_id
        )
        documents = await self.repository.list_evidence_documents(course.domain)
        evidence_by_slug, _ = _evidence_by_slug(documents)
        edges = await self.repository.list_edges([node.id for node in nodes])
        return CourseGraphDTO(
            course_id=course.id,
            nodes=[
                _node_dto(node, resource_count=resources.get(node.id, 0), evidence_count=len(evidence_by_slug.get(_slug(node), set())))
                for node in nodes
            ],
            edges=[
                CourseGraphEdgeDTO(
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                    edge_type="prerequisite",
                    weight=edge.weight,
                )
                for edge in edges
            ],
        )

    async def get_path(self, *, course_id: UUID, user_id: UUID) -> CoursePathDTO:
        course = await self._require_course(course_id)
        product = self._product_for(course)
        if product.content_status == "preview":
            return CoursePathDTO(
                course_id=course.id,
                capability_dimension=product.capability,
                capability_score=0.0,
                strategy="foundation_first",
                explanation=product.unavailable_reason or "课程内容正在建设中。",
                nodes=[],
            )
        nodes = list(await self.repository.list_nodes(course.id))
        edges = list(await self.repository.list_edges([node.id for node in nodes]))
        progress = await self.get_progress(course_id=course.id, user_id=user_id, nodes=nodes, edges=edges)
        capability = await self.capabilities.get(user_id, product.capability)
        score = capability.score if capability is not None else 0.0
        accelerated = score >= 0.7
        ordered = _topological_order(nodes, edges, accelerated=accelerated)
        prerequisites = _prerequisites(edges)
        completed = set(progress.completed_knowledge_point_ids)
        active_id = progress.next_knowledge_point_id
        node_dtos: list[CoursePathNodeDTO] = []
        for node in ordered:
            node_prerequisites = prerequisites.get(node.id, [])
            if node.id in completed:
                status = "done"
            elif node.id == active_id:
                status = "in_progress"
            elif all(prerequisite in completed for prerequisite in node_prerequisites):
                status = "ready"
            else:
                status = "locked"
            node_dtos.append(
                CoursePathNodeDTO(
                    knowledge_point_id=node.id,
                    title=node.name,
                    status=status,
                    prerequisites=node_prerequisites,
                    rationale=_path_rationale(node, score=score, accelerated=accelerated),
                )
            )
        strategy = "accelerated_prerequisite_route" if accelerated else "foundation_first"
        explanation = (
            f"依据 user_capabilities.{product.capability}={score:.2f}，优先选择解锁更多后续主题的已满足先修节点。"
            if accelerated
            else f"依据 user_capabilities.{product.capability}={score:.2f}，先按课程图谱稳固基础概念。"
        )
        return CoursePathDTO(
            course_id=course.id,
            capability_dimension=product.capability,
            capability_score=score,
            strategy=strategy,
            explanation=explanation,
            nodes=node_dtos,
        )

    async def get_progress(
        self,
        *,
        course_id: UUID,
        user_id: UUID,
        nodes: list[KnowledgeNode] | None = None,
        edges: list[Any] | None = None,
    ) -> CourseProgressDTO:
        course = await self._require_course(course_id)
        product = self._product_for(course)
        if product.content_status == "preview":
            return CourseProgressDTO(
                course_id=course.id,
                course_code=course.code,
                completed_knowledge_point_ids=[],
                progress_percent=0.0,
                next_recommendation=product.unavailable_reason or "课程内容正在建设中。",
            )
        nodes = nodes if nodes is not None else list(await self.repository.list_nodes(course.id))
        edges = edges if edges is not None else list(await self.repository.list_edges([node.id for node in nodes]))
        capability = await self.capabilities.get(user_id, product.capability)
        payload = _progress_payload(capability, course.code)
        known_ids = {node.id for node in nodes}
        completed = [UUID(value) for value in payload.get("completed_kp_ids", []) if _is_known_uuid(value, known_ids)]
        next_node = _next_node(nodes, edges, set(completed))
        return CourseProgressDTO(
            course_id=course.id,
            course_code=course.code,
            completed_knowledge_point_ids=completed,
            progress_percent=round((len(completed) / len(nodes) * 100) if nodes else 0.0, 1),
            current_knowledge_point_id=completed[-1] if completed else None,
            next_knowledge_point_id=next_node.id if next_node is not None else None,
            next_recommendation=(f"下一步：{next_node.name}" if next_node is not None else "课程核心知识点已完成，可进入综合复盘。"),
            updated_at=_parse_datetime(payload.get("updated_at")),
        )

    async def record_completion(
        self,
        *,
        course_id: UUID,
        user_id: UUID,
        knowledge_point_id: UUID,
        activity_type: str,
        activity_id: str,
        workflow_run_id: UUID | None = None,
    ) -> CourseProgressDTO:
        course = await self._require_course(course_id)
        product = self._product_for(course)
        if product.content_status == "preview":
            raise CourseContentNotReadyError(product.unavailable_reason or "课程内容正在建设中。")
        nodes = list(await self.repository.list_nodes(course.id))
        if knowledge_point_id not in {node.id for node in nodes}:
            raise CourseProgressValidationError("knowledge point does not belong to this course")
        capability = await self.capabilities.get(user_id, product.capability)
        if capability is None:
            capability = await self.capabilities.upsert_score(
                user_id=user_id,
                dimension=product.capability,
                score=0.0,
                confidence=0.0,
                evidence_count=0,
                metadata={},
            )
        metadata = dict(capability.metadata_ or {})
        all_progress = dict(metadata.get(_PROGRESS_KEY) or {})
        payload = dict(all_progress.get(course.code) or {})
        completed = [value for value in payload.get("completed_kp_ids", []) if isinstance(value, str)]
        serialized_kp_id = str(knowledge_point_id)
        if serialized_kp_id not in completed:
            completed.append(serialized_kp_id)
        activities = [item for item in payload.get("activities", []) if isinstance(item, dict)]
        seen = {str(item.get("activity_id")) for item in activities}
        if activity_id not in seen:
            activities.append(
                {
                    "activity_id": activity_id,
                    "activity_type": activity_type,
                    "knowledge_point_id": serialized_kp_id,
                    "workflow_run_id": str(workflow_run_id) if workflow_run_id else None,
                    "completed_at": datetime.now(UTC).isoformat(),
                }
            )
        payload.update(
            {
                "schema_version": _PROGRESS_SCHEMA_VERSION,
                "completed_kp_ids": completed,
                "activities": activities[-100:],
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
        all_progress[course.code] = payload
        metadata[_PROGRESS_KEY] = all_progress
        await self.capabilities.upsert_score(
            user_id=user_id,
            dimension=product.capability,
            score=capability.score,
            confidence=capability.confidence,
            evidence_count=capability.evidence_count,
            metadata=metadata,
        )
        return await self.get_progress(course_id=course.id, user_id=user_id, nodes=nodes)

    async def _catalog_item(self, course: Course, *, user_id: UUID) -> CourseCatalogItemDTO:
        product = self._product_for(course)
        if product.content_status == "preview":
            return self._catalog_from_parts(
                course,
                product=product,
                nodes=[],
                resource_counts={},
                evidence_by_slug={},
                progress=await self.get_progress(course_id=course.id, user_id=user_id),
                coverage=[],
            )
        nodes = list(await self.repository.list_nodes(course.id))
        resources = await self.repository.resource_counts(
            course_ids=_resource_course_ids(course, product), user_id=user_id
        )
        documents = await self.repository.list_evidence_documents(course.domain)
        evidence_by_slug, _ = _evidence_by_slug(documents)
        progress = await self.get_progress(course_id=course.id, user_id=user_id, nodes=nodes)
        return self._catalog_from_parts(
            course,
            product=product,
            nodes=nodes,
            resource_counts=resources,
            evidence_by_slug=evidence_by_slug,
            progress=progress,
            coverage=_chapter_coverage(nodes, evidence_by_slug, product),
        )

    async def _require_course(self, course_id: UUID) -> Course:
        course = await self.repository.get_course(course_id)
        if course is None or course.code not in COURSE_PRODUCT_BY_CODE:
            raise CourseProductNotFoundError(f"course {course_id} does not exist")
        product = COURSE_PRODUCT_BY_CODE[course.code]
        if course.id != product.id:
            raise CourseProductNotFoundError(f"course {course_id} does not match its product definition")
        return course

    @staticmethod
    def _product_for(course: Course) -> CourseProductDefinition:
        try:
            return COURSE_PRODUCT_BY_CODE[course.code]
        except KeyError as exc:  # _require_course should make this unreachable.
            raise CourseProductNotFoundError(f"course {course.id} does not have a product definition") from exc

    @staticmethod
    def _catalog_from_parts(
        course: Course,
        *,
        product: CourseProductDefinition,
        nodes: list[KnowledgeNode],
        resource_counts: dict[UUID, int],
        evidence_by_slug: dict[str, set[UUID]],
        progress: CourseProgressDTO,
        coverage: list[CourseChapterDTO],
    ) -> CourseCatalogItemDTO:
        current = next((node for node in nodes if node.id == progress.current_knowledge_point_id), None)
        core_coverage = sum(chapter.coverage_percent for chapter in coverage) / len(coverage) if coverage else 0.0
        return CourseCatalogItemDTO(
            id=course.id,
            code=course.code,
            title=course.title,
            domain=course.domain,
            description=course.description,
            content_status=product.content_status,
            unavailable_reason=product.unavailable_reason,
            chapter_count=len(coverage),
            knowledge_point_count=len(nodes),
            resource_count=sum(resource_counts.values()),
            progress_percent=progress.progress_percent,
            current_knowledge_point_id=current.id if current is not None else progress.next_knowledge_point_id,
            current_knowledge_point=current.name if current is not None else progress.next_recommendation,
            next_recommendation=progress.next_recommendation,
            core_coverage_percent=round(core_coverage, 1),
        )

    def _preview_detail(self, course: Course, product: CourseProductDefinition) -> CourseDetailDTO:
        progress = CourseProgressDTO(
            course_id=course.id,
            course_code=course.code,
            completed_knowledge_point_ids=[],
            progress_percent=0.0,
            next_recommendation=product.unavailable_reason or "课程内容正在建设中。",
        )
        catalog_item = self._catalog_from_parts(
            course,
            product=product,
            nodes=[],
            resource_counts={},
            evidence_by_slug={},
            progress=progress,
            coverage=[],
        )
        return CourseDetailDTO(
            **catalog_item.model_dump(),
            chapters=[],
            knowledge_points=[],
            source_platforms=[],
            source_manifest=None,
        )


def _node_dto(node: KnowledgeNode, *, resource_count: int, evidence_count: int) -> CourseKnowledgePointDTO:
    metadata = dict(node.metadata_ or {})
    return CourseKnowledgePointDTO(
        id=node.id,
        slug=_slug(node),
        name=node.name,
        description=node.description,
        level=node.level,
        chapter_code=str(metadata.get("chapter_code") or "unclassified"),
        chapter_title=str(metadata.get("chapter_title") or "未分类"),
        resource_count=resource_count,
        evidence_count=evidence_count,
    )


def _resource_course_ids(course: Course, product: CourseProductDefinition) -> tuple[UUID, ...]:
    if product.id == COURSE_PRODUCTS[0].id:
        return (course.id, LEGACY_SMOKE_COURSE_WEBSEC_ID)
    return (course.id,)


def _slug(node: KnowledgeNode) -> str:
    value = dict(node.metadata_ or {}).get("slug")
    return str(value) if value else str(node.id)


def _evidence_by_slug(documents: list[Any] | Any) -> tuple[dict[str, set[UUID]], list[str]]:
    evidence: dict[str, set[UUID]] = defaultdict(set)
    platforms: set[str] = set()
    for document in documents:
        metadata = dict(document.metadata_ or {})
        slug = metadata.get("kp_slug")
        source_url = metadata.get("source_url") or document.url
        rights_note = metadata.get("rights_note")
        license_value = metadata.get("license")
        if not isinstance(slug, str) or not source_url or not rights_note or not license_value:
            continue
        evidence[slug].add(document.id)
        platform = metadata.get("platform")
        if isinstance(platform, str) and platform:
            platforms.add(platform)
    return evidence, sorted(platforms)


def _chapter_coverage(
    nodes: list[KnowledgeNode],
    evidence_by_slug: dict[str, set[UUID]],
    product: CourseProductDefinition,
) -> list[CourseChapterDTO]:
    by_slug = {_slug(node): node for node in nodes}
    chapters: list[CourseChapterDTO] = []
    for code, title, slugs in product.chapters:
        chapter_nodes = [by_slug[slug] for slug in slugs if slug in by_slug]
        covered = [node.id for node in chapter_nodes if evidence_by_slug.get(_slug(node))]
        percentage = round((len(covered) / len(chapter_nodes) * 100) if chapter_nodes else 0.0, 1)
        chapters.append(
            CourseChapterDTO(
                code=code,
                title=title,
                knowledge_point_ids=[node.id for node in chapter_nodes],
                covered_knowledge_point_ids=covered,
                coverage_percent=percentage,
            )
        )
    return chapters


def _prerequisites(edges: list[Any] | Any) -> dict[UUID, list[UUID]]:
    result: dict[UUID, list[UUID]] = defaultdict(list)
    for edge in edges:
        result[edge.target_id].append(edge.source_id)
    return {key: sorted(value, key=str) for key, value in result.items()}


def _topological_order(nodes: list[KnowledgeNode], edges: list[Any] | Any, *, accelerated: bool) -> list[KnowledgeNode]:
    by_id = {node.id: node for node in nodes}
    incoming: dict[UUID, set[UUID]] = {node.id: set() for node in nodes}
    outgoing: dict[UUID, set[UUID]] = {node.id: set() for node in nodes}
    for edge in edges:
        incoming[edge.target_id].add(edge.source_id)
        outgoing[edge.source_id].add(edge.target_id)

    def key(node_id: UUID) -> tuple[Any, ...]:
        node = by_id[node_id]
        if accelerated:
            return (-len(outgoing[node_id]), node.level or 0, node.name)
        return (node.level or 999, node.name)

    ready = sorted((node_id for node_id, parents in incoming.items() if not parents), key=key)
    ordered: list[KnowledgeNode] = []
    while ready:
        node_id = ready.pop(0)
        ordered.append(by_id[node_id])
        for target_id in sorted(outgoing[node_id], key=str):
            incoming[target_id].discard(node_id)
            if not incoming[target_id]:
                ready.append(target_id)
        ready.sort(key=key)
    if len(ordered) != len(nodes):
        raise CourseProgressValidationError("course prerequisite graph must be acyclic")
    return ordered


def _next_node(nodes: list[KnowledgeNode], edges: list[Any] | Any, completed: set[UUID]) -> KnowledgeNode | None:
    prerequisites = _prerequisites(edges)
    for node in _topological_order(nodes, edges, accelerated=False):
        if node.id not in completed and all(parent in completed for parent in prerequisites.get(node.id, [])):
            return node
    return None


def _progress_payload(capability: UserCapability | None, course_code: str) -> dict[str, Any]:
    if capability is None:
        return {}
    metadata = dict(capability.metadata_ or {})
    progress = metadata.get(_PROGRESS_KEY)
    if not isinstance(progress, dict):
        return {}
    payload = progress.get(course_code)
    return dict(payload) if isinstance(payload, dict) else {}


def _is_known_uuid(value: Any, known_ids: set[UUID]) -> bool:
    try:
        return UUID(str(value)) in known_ids
    except (TypeError, ValueError):
        return False


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _path_rationale(node: KnowledgeNode, *, score: float, accelerated: bool) -> str:
    if accelerated:
        return f"能力评分 {score:.2f}，该节点在满足先修后优先解锁高价值后续主题。"
    return f"能力评分 {score:.2f}，按基础层级逐步建立 {node.name} 的前置理解。"
