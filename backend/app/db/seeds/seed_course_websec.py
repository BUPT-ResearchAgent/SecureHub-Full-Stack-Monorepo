# Status: real

"""Idempotent seed for the Web Security demo course.

Seeds:

- 1 course row
- 15 ``knowledge_nodes`` (one per knowledge-point slug)
- 30 ``knowledge_edges`` (prerequisite DAG)
- 1 placeholder ``documents`` row per knowledge point + 4 ``chunks`` per
  document = 60 chunks total. Embeddings stay ``NULL`` with
  ``embedding_status='pending'`` for the embedding pipeline to fill in.
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge.chunk import Chunk
from app.db.seeds._constants import (
    COURSE_WEBSEC_CODE,
    COURSE_WEBSEC_DESCRIPTION,
    COURSE_WEBSEC_ID,
    COURSE_WEBSEC_TITLE,
    WEBSEC_EDGES,
    WEBSEC_NODES,
    chunk_id,
    document_id,
    node_id,
)
from app.db.session import get_sessionmaker
from app.repositories.knowledge.chunks import ChunkRepository
from app.repositories.knowledge.courses import CourseRepository
from app.repositories.knowledge.documents import DocumentRepository
from app.repositories.knowledge.knowledge_graph import KnowledgeGraphRepository

CHUNKS_PER_DOC = 4
DOMAIN = "course_websec"


async def _seed(session: AsyncSession) -> dict[str, int]:
    courses = CourseRepository(session)
    graph = KnowledgeGraphRepository(session)
    documents = DocumentRepository(session)
    chunks = ChunkRepository(session)

    course_count = 0
    node_count = 0
    edge_count = 0
    doc_count = 0
    chunk_count = 0

    # ---- course ----
    if await courses.get_by_code(COURSE_WEBSEC_CODE) is None:
        await courses.create(
            course_id=COURSE_WEBSEC_ID,
            code=COURSE_WEBSEC_CODE,
            title=COURSE_WEBSEC_TITLE,
            domain=DOMAIN,
            description=COURSE_WEBSEC_DESCRIPTION,
        )
        course_count = 1

    # ---- nodes ----
    for slug, name, level in WEBSEC_NODES:
        nid = node_id(slug)
        if await graph.get_node(nid) is None:
            await graph.create_node(
                node_id=nid,
                domain=DOMAIN,
                name=name,
                course_id=COURSE_WEBSEC_ID,
                description=f"《Web 安全基础》知识点：{name}",
                node_type="concept",
                level=level,
                metadata={"slug": slug},
            )
            node_count += 1

    # ---- edges ----
    existing_edges = {
        (e.source_id, e.target_id, e.edge_type) for e in await graph.list_edges()
    }
    for src_slug, tgt_slug in WEBSEC_EDGES:
        src_id = node_id(src_slug)
        tgt_id = node_id(tgt_slug)
        if (src_id, tgt_id, "prerequisite") in existing_edges:
            continue
        await graph.create_edge(
            source_id=src_id,
            target_id=tgt_id,
            edge_type="prerequisite",
            weight=1.0,
        )
        edge_count += 1

    # ---- documents + chunks ----
    fetched_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
    for slug, name, level in WEBSEC_NODES:
        did = document_id(slug)
        if await documents.get_by_id(did) is None:
            await documents.create(
                document_id=did,
                domain=DOMAIN,
                source_type="course_handout",
                title=f"{name} · 教学讲义",
                url=f"https://demo.securehub.local/websec/{slug}.md",
                content_hash=None,
                raw_text=None,
                metadata={
                    "kp_slug": slug,
                    "level": level,
                    "type": "概念",
                },
                trust_score=0.9,
                status="ready",
                fetched_at=fetched_at,
            )
            doc_count += 1

        existing_chunks = await chunks.list_by_document(did)
        if existing_chunks:
            continue
        chunk_rows: list[Chunk] = []
        for i in range(CHUNKS_PER_DOC):
            chunk_rows.append(
                Chunk(
                    id=chunk_id(slug, i),
                    document_id=did,
                    domain=DOMAIN,
                    chunk_text=(
                        f"[{name}] 段落 {i + 1}：占位文本，"
                        "待 ETL 替换为真正的教学正文片段。"
                    ),
                    chunk_index=i,
                    token_count=None,
                    embedding=None,
                    embedding_status="pending",
                    metadata_={"kp_slug": slug, "section": i + 1},
                )
            )
        await chunks.bulk_create(chunk_rows)
        chunk_count += len(chunk_rows)

    return {
        "courses": course_count,
        "nodes": node_count,
        "edges": edge_count,
        "documents": doc_count,
        "chunks": chunk_count,
    }


async def run(session: AsyncSession | None = None) -> dict[str, int]:
    if session is not None:
        return await _seed(session)

    sm = get_sessionmaker()
    async with sm() as own_session:
        stats = await _seed(own_session)
        await own_session.commit()
    return stats


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(run())
