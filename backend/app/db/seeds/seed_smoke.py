# Status: real

"""Idempotent smoke seed for the Day 0 SQL injection demo."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.db.models.agent.agent import Agent
from app.db.models.agent.agent_skill import AgentSkill
from app.db.models.identity.user import User
from app.db.models.identity.user_capability import UserCapability
from app.db.models.identity.user_profile import UserProfile
from app.db.models.knowledge.chunk import Chunk
from app.db.models.knowledge.course import Course
from app.db.models.knowledge.document import Document
from app.db.models.knowledge.knowledge_edge import KnowledgeEdge
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.db.seeds._constants import DEMO_USER_PASSWORD
from app.db.seeds.seed_demo_user import run as seed_demo_user

USER_DEMO_ID = UUID("00000000-0000-0000-0000-000000000001")
COURSE_ID = UUID("00000000-0000-0000-0000-000000000101")
DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000601")
COURSE_CODE = "course_websec_intro"
COURSE_DOMAIN = "course_websec"
COURSE_TITLE = "Web 安全基础"
DOCUMENT_URL = "https://owasp.org/www-community/attacks/SQL_Injection"

NODE_IDS = {
    "SQL 注入基础": UUID("00000000-0000-0000-0000-000000000201"),
    "XSS 基础": UUID("00000000-0000-0000-0000-000000000202"),
    "CSRF 基础": UUID("00000000-0000-0000-0000-000000000203"),
}

AGENTS: list[tuple[str, str, str, str]] = [
    ("policy_interpreter", "Policy and compliance interpretation agent.", "medium", "InterpretPolicy"),
    ("hot_analyst", "Security event and reading recommendation agent.", "high", "RecommendReadings"),
    ("job_analyst", "Job market and skill gap analysis agent.", "low", "AnalyzeJobSkillGap"),
    ("competition_advisor", "Competition and quiz generation agent.", "medium", "GenerateQuiz"),
    ("career_planner", "Learning persona and resource recommendation agent.", "high", "BuildLearningPersona"),
    ("topic_explorer", "Research topic and hands-on lab agent.", "medium", "GenerateHandsOnLab"),
    ("doc_archivist", "Course document, PPT, mindmap, and video agent.", "low", "GenerateCourseDoc"),
    ("task_orchestrator", "Learning path and task planning agent.", "low", "GenerateLearningPath"),
    ("outcome_evaluator", "Assessment, capability update, and quality gate agent.", "high", "QualityCheck"),
]

CAPABILITIES: list[tuple[str, float, float]] = [
    ("web_security", 0.35, 0.60),
    ("crypto", 0.20, 0.45),
    ("reverse", 0.18, 0.40),
    ("forensics", 0.25, 0.50),
    ("mobile", 0.15, 0.35),
    ("cloud_sec", 0.22, 0.42),
]

CHUNK_TEXTS = [
    "SQL injection happens when untrusted input is mixed into a database query. The attacker can change query structure instead of only providing data.",
    "A vulnerable login or search form may reveal data, bypass authentication, or modify records. Parameterized queries keep user input separate from SQL syntax.",
    "The OWASP guidance treats SQL injection as a long-standing web risk. Input validation helps, but prepared statements are the primary defense.",
    "Attackers often test quotation marks, boolean conditions, and comments to learn how an application builds SQL. Error messages can expose table or column clues.",
    "Union-based injection tries to combine attacker-selected rows with the original query. The attacker usually needs to learn the number and type of selected columns first.",
    "Blind injection appears when the page hides database errors. Attackers infer truth from response differences or timing behavior.",
    "Least-privilege database accounts reduce blast radius. An application account should not own schema changes when it only needs read or limited write access.",
    "Escaping alone is fragile because database dialects and encodings differ. Safe query APIs and reviewed data-access helpers are easier to audit.",
    "Detection should combine code review, dependency scanning, and dynamic tests. Security tests need representative inputs for login, search, and filter endpoints.",
    "For teaching, SQL injection is useful because students can see how a small string changes a backend query. The lesson should end with parameterized fixes.",
]


@dataclass
class TableStats:
    inserted: int = 0
    skipped: int = 0


def stable_id(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"securehub:smoke:{name}")


async def _dialect_name(session: AsyncSession) -> str:
    connection = await session.connection()
    return connection.dialect.name


def _print_stats(table: str, stats: TableStats) -> None:
    print(f"[seed_smoke] inserted {stats.inserted} / skipped {stats.skipped} rows for {table}")


async def _seed_user(session: AsyncSession) -> None:
    stats = TableStats()
    existing = await session.get(User, USER_DEMO_ID)
    if existing is None:
        session.add(
            User(
                id=USER_DEMO_ID,
                email="demo_student_zhang@securehub.local",
                display_name="demo_student_zhang",
                hashed_password=hash_password(DEMO_USER_PASSWORD),
                is_active=True,
            )
        )
        stats.inserted += 1
    else:
        if not existing.hashed_password:
            existing.hashed_password = hash_password(DEMO_USER_PASSWORD)
            existing.is_active = True
            await session.flush()
        stats.skipped += 1
    _print_stats("users", stats)


async def _seed_course(session: AsyncSession) -> Course:
    stats = TableStats()
    existing = (
        await session.execute(select(Course).where(Course.code == COURSE_CODE))
    ).scalar_one_or_none()
    if existing is not None:
        stats.skipped += 1
        _print_stats("courses", stats)
        return existing

    course = Course(
        id=COURSE_ID,
        code=COURSE_CODE,
        title=COURSE_TITLE,
        domain=COURSE_DOMAIN,
        description="SQL 注入、XSS、CSRF 等 Web 安全入门课程。",
    )
    session.add(course)
    stats.inserted += 1
    _print_stats("courses", stats)
    return course


async def _seed_nodes(session: AsyncSession, course_id: UUID) -> dict[str, UUID]:
    stats = TableStats()
    resolved: dict[str, UUID] = {}
    for name, node_id in NODE_IDS.items():
        existing = (
            await session.execute(
                select(KnowledgeNode).where(
                    KnowledgeNode.domain == COURSE_DOMAIN,
                    KnowledgeNode.name == name,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            stats.skipped += 1
            resolved[name] = existing.id
            continue
        node = KnowledgeNode(
            id=node_id,
            domain=COURSE_DOMAIN,
            course_id=course_id,
            name=name,
            description=f"{name} demo concept node.",
            node_type="concept",
            level=1,
            metadata_={"seed": "smoke"},
        )
        session.add(node)
        stats.inserted += 1
        resolved[name] = node_id
    _print_stats("knowledge_nodes", stats)
    return resolved


async def _seed_edges(session: AsyncSession, node_ids: dict[str, UUID]) -> None:
    stats = TableStats()
    edges = [
        ("SQL 注入基础", "XSS 基础", "related_to"),
        ("SQL 注入基础", "CSRF 基础", "related_to"),
        ("XSS 基础", "CSRF 基础", "related_to"),
    ]
    for source, target, edge_type in edges:
        existing = await session.get(
            KnowledgeEdge,
            {
                "source_id": node_ids[source],
                "target_id": node_ids[target],
                "edge_type": edge_type,
            },
        )
        if existing is not None:
            stats.skipped += 1
            continue
        session.add(
            KnowledgeEdge(
                source_id=node_ids[source],
                target_id=node_ids[target],
                edge_type=edge_type,
                weight=1.0,
                metadata_={"seed": "smoke"},
            )
        )
        stats.inserted += 1
    _print_stats("knowledge_edges", stats)


async def _seed_document(session: AsyncSession) -> Document:
    stats = TableStats()
    existing = (
        await session.execute(
            select(Document).where(
                Document.domain == COURSE_DOMAIN,
                Document.url == DOCUMENT_URL,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        stats.skipped += 1
        _print_stats("documents", stats)
        return existing

    document = Document(
        id=DOCUMENT_ID,
        domain=COURSE_DOMAIN,
        source_type="manual",
        title="OWASP SQL Injection 摘要",
        url=DOCUMENT_URL,
        content_hash=None,
        raw_text=None,
        metadata_={
            "platform": "owasp",
            "author": "OWASP",
            "rights_note": "CC BY-SA 4.0",
        },
        trust_score=0.9,
        status="ready",
        fetched_at=datetime.now(UTC),
    )
    session.add(document)
    stats.inserted += 1
    _print_stats("documents", stats)
    return document


async def _seed_chunks(session: AsyncSession, document_id: UUID, sql_node_id: UUID) -> None:
    stats = TableStats()
    for index, chunk_text in enumerate(CHUNK_TEXTS):
        existing = (
            await session.execute(
                select(Chunk).where(
                    Chunk.document_id == document_id,
                    Chunk.chunk_index == index,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            stats.skipped += 1
            continue
        metadata: dict[str, Any] = {
            "platform": "owasp",
            "author": "OWASP",
            "rights_note": "CC BY-SA 4.0",
            "asset_type": "web_article",
        }
        if index < 3:
            metadata["kp_ids"] = [str(sql_node_id)]
        session.add(
            Chunk(
                id=stable_id(f"chunk:{index}"),
                document_id=document_id,
                domain=COURSE_DOMAIN,
                chunk_text=chunk_text,
                chunk_index=index,
                token_count=len(chunk_text.split()),
                embedding=None,
                embedding_status="pending",
                metadata_=metadata,
            )
        )
        stats.inserted += 1
    _print_stats("chunks", stats)


def _vector_literal(dim: int = 64) -> str:
    return "[" + ",".join(["0"] * dim) + "]"


async def _seed_agent_row(
    session: AsyncSession,
    dialect: str,
    name: str,
    description: str,
    risk: str,
) -> tuple[UUID, bool]:
    existing = (
        await session.execute(select(Agent).where(Agent.name == name))
    ).scalar_one_or_none()
    if existing is not None:
        return existing.id, False

    agent_id = stable_id(f"agent:{name}")
    payload: dict[str, Any] = {
        "id": str(agent_id),
        "name": name,
        "rd": description,
        "cv": _vector_literal(),
        "rl": risk,
        "en": True,
    }
    if dialect == "postgresql":
        payload["tools"] = ["rag.retrieve", "llm.xfyun"]
        await session.execute(
            text(
                "INSERT INTO agents (id, name, role_description, capability_vector, "
                "tools, input_schema, output_schema, risk_level, enabled) "
                "VALUES (:id, :name, :rd, CAST(:cv AS vector), :tools, "
                "CAST('{}' AS jsonb), CAST('{}' AS jsonb), :rl, :en)"
            ),
            payload,
        )
    else:
        payload["tools"] = json.dumps(["rag.retrieve", "llm.xfyun"])
        await session.execute(
            text(
                "INSERT INTO agents (id, name, role_description, capability_vector, "
                "tools, input_schema, output_schema, risk_level, enabled) "
                "VALUES (:id, :name, :rd, :cv, :tools, '{}', '{}', :rl, :en)"
            ),
            payload,
        )
    return agent_id, True


async def _seed_skill_row(
    session: AsyncSession,
    dialect: str,
    agent_id: UUID,
    agent_name: str,
    skill_name: str,
) -> bool:
    existing = await session.execute(
        text(
            "SELECT id FROM agent_skills "
            "WHERE agent_id = :aid AND skill_name = :sn AND version = :v"
        ),
        {"aid": str(agent_id), "sn": skill_name, "v": 1},
    )
    if existing.first() is not None:
        return False

    skill_id = stable_id(f"skill:{agent_name}:{skill_name}:1")
    payload: dict[str, Any] = {
        "id": str(skill_id),
        "aid": str(agent_id),
        "sn": skill_name,
        "pt": "[seeded placeholder]",
        "v": 1,
        "en": True,
    }
    if dialect == "postgresql":
        payload["ad"] = [COURSE_DOMAIN]
        payload["rt"] = ["rag.retrieve", "llm.xfyun"]
        await session.execute(
            text(
                "INSERT INTO agent_skills (id, agent_id, skill_name, prompt_template, "
                "applicable_domains, required_tools, output_schema, version, enabled) "
                "VALUES (:id, :aid, :sn, :pt, :ad, :rt, CAST('{}' AS jsonb), :v, :en)"
            ),
            payload,
        )
    else:
        payload["ad"] = json.dumps([COURSE_DOMAIN])
        payload["rt"] = json.dumps(["rag.retrieve", "llm.xfyun"])
        await session.execute(
            text(
                "INSERT INTO agent_skills (id, agent_id, skill_name, prompt_template, "
                "applicable_domains, required_tools, output_schema, version, enabled) "
                "VALUES (:id, :aid, :sn, :pt, :ad, :rt, '{}', :v, :en)"
            ),
            payload,
        )
    return True


async def _seed_agents_and_skills(session: AsyncSession) -> None:
    dialect = await _dialect_name(session)
    agent_stats = TableStats()
    skill_stats = TableStats()
    for name, description, risk, skill_name in AGENTS:
        agent_id, inserted = await _seed_agent_row(session, dialect, name, description, risk)
        if inserted:
            agent_stats.inserted += 1
        else:
            agent_stats.skipped += 1
        if await _seed_skill_row(session, dialect, agent_id, name, skill_name):
            skill_stats.inserted += 1
        else:
            skill_stats.skipped += 1
    _print_stats("agents", agent_stats)
    _print_stats("agent_skills", skill_stats)


async def _seed_profile(session: AsyncSession) -> None:
    stats = TableStats()
    existing = await session.get(UserProfile, USER_DEMO_ID)
    if existing is not None:
        stats.skipped += 1
    else:
        session.add(
            UserProfile(
                user_id=USER_DEMO_ID,
                dimensions={
                    "knowledge_base": "beginner",
                    "learning_goal": "web_security",
                    "style": "case_driven",
                    "prior_courses": [],
                    "language": "zh",
                    "cognitive_load": "medium",
                },
                embedding=None,
            )
        )
        stats.inserted += 1
    _print_stats("user_profiles", stats)


async def _seed_capabilities(session: AsyncSession) -> None:
    stats = TableStats()
    for dimension, score, confidence in CAPABILITIES:
        existing = (
            await session.execute(
                select(UserCapability).where(
                    UserCapability.user_id == USER_DEMO_ID,
                    UserCapability.dimension == dimension,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            stats.skipped += 1
            continue
        session.add(
            UserCapability(
                id=stable_id(f"capability:{dimension}"),
                user_id=USER_DEMO_ID,
                dimension=dimension,
                score=score,
                confidence=confidence,
                evidence_count=0,
                metadata_={"seed": "smoke"},
            )
        )
        stats.inserted += 1
    _print_stats("user_capabilities", stats)


async def seed_smoke(session: AsyncSession) -> None:
    """幂等：如已存在则跳过。"""
    await seed_demo_user(session)
    await _seed_user(session)
    course = await _seed_course(session)
    await session.flush()
    node_ids = await _seed_nodes(session, course.id)
    await session.flush()
    await _seed_edges(session, node_ids)
    document = await _seed_document(session)
    await session.flush()
    await _seed_chunks(session, document.id, node_ids["SQL 注入基础"])
    await _seed_agents_and_skills(session)
    await _seed_profile(session)
    await _seed_capabilities(session)


async def count_seeded_agents(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count()).select_from(Agent))).scalar_one())
