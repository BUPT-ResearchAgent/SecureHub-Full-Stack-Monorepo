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
from hashlib import sha256

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
    stable_id,
)
from app.db.session import get_sessionmaker
from app.repositories.knowledge.chunks import ChunkRepository
from app.repositories.knowledge.courses import CourseRepository
from app.repositories.knowledge.document_assets import DocumentAssetRepository
from app.repositories.knowledge.documents import DocumentRepository
from app.repositories.knowledge.knowledge_graph import KnowledgeGraphRepository
from app.repositories.storage.storage_objects import StorageObjectRepository

CHUNKS_PER_DOC = 4
DOMAIN = "course_websec"

SOURCE_PROFILES: dict[str, dict[str, object]] = {
    "sql-injection": {
        "platform": "owasp",
        "url": "https://owasp.org/www-community/attacks/SQL_Injection",
        "author": "OWASP",
        "license": "CC BY-SA 4.0",
        "rights_note": "OWASP 社区公开资料，教学演示引用并保留来源。",
    },
    "xss-reflected": {
        "platform": "owasp",
        "url": "https://owasp.org/www-community/attacks/xss/#reflected-xss",
        "author": "OWASP",
        "license": "CC BY-SA 4.0",
        "rights_note": "OWASP 社区公开资料，教学演示引用并保留来源。",
    },
    "xss-stored": {
        "platform": "owasp",
        "url": "https://owasp.org/www-community/attacks/xss/#stored-xss",
        "author": "OWASP",
        "license": "CC BY-SA 4.0",
        "rights_note": "OWASP 社区公开资料，教学演示引用并保留来源。",
    },
    "xss-dom": {
        "platform": "portswigger",
        "url": "https://portswigger.net/web-security/cross-site-scripting/dom-based",
        "author": "PortSwigger Web Security Academy",
        "license": "Public learning material",
        "rights_note": "PortSwigger 公开学习资料，保留链接，仅做课程索引和摘要切片。",
    },
    "csrf": {
        "platform": "portswigger",
        "url": "https://portswigger.net/web-security/csrf",
        "author": "PortSwigger Web Security Academy",
        "license": "Public learning material",
        "rights_note": "PortSwigger 公开学习资料，保留链接，仅做课程索引和摘要切片。",
    },
    "file-upload": {
        "platform": "portswigger",
        "url": "https://portswigger.net/web-security/file-upload",
        "author": "PortSwigger Web Security Academy",
        "license": "Public learning material",
        "rights_note": "PortSwigger 公开学习资料，保留链接，仅做课程索引和摘要切片。",
    },
}

TOPIC_HINTS: dict[str, list[str]] = {
    "sql-injection": [
        "SQL 注入发生在未受信任输入被拼接进数据库语句时，攻击者可以改变查询结构，而不只是提交普通数据。",
        "登录、搜索和筛选接口是教学中最容易观察的入口；典型危害包括绕过认证、读取敏感数据和修改记录。",
        "参数化查询会把用户输入与 SQL 语法分离，是比手工转义更稳定的主要防御方式。",
        "盲注、联合查询和报错注入都应结合最小权限数据库账号与统一数据访问层一起讲解。",
    ],
    "xss-reflected": [
        "反射型 XSS 通常把请求参数立即回显到响应页面，攻击载荷需要诱导用户点击构造好的链接。",
        "教学重点是输出编码与上下文：HTML 文本、属性、JavaScript 字符串和 URL 参数需要不同处理方式。",
        "输入过滤只能降低风险，真正的边界在模板引擎自动转义、CSP 和危险 sink 审计。",
        "证据展示应保留触发 URL、参数名和页面上下文，避免把 payload 当作可执行攻击教程扩散。",
    ],
    "xss-stored": [
        "存储型 XSS 会把恶意内容写入评论、资料、工单等持久化位置，后续访问者都会触发风险。",
        "比反射型 XSS 更适合说明服务端净化、富文本白名单和内容安全策略的组合防护。",
        "演示时可使用本地靶场和无害 payload，重点观察数据从提交、存储到渲染的完整路径。",
        "修复验收要覆盖新增、编辑、预览和历史数据迁移，避免只修一个入口。",
    ],
    "xss-dom": [
        "DOM-based XSS 的污染源和危险 sink 都在浏览器端，例如 location、postMessage 与 innerHTML。",
        "学生需要用浏览器 DevTools 追踪数据流，而不是只看服务端响应体。",
        "安全写法包括 textContent、严格 URL 解析、可信模板和框架默认转义机制。",
        "测试用例应覆盖 hash、query、localStorage 和跨窗口消息等前端状态来源。",
    ],
    "csrf": [
        "CSRF 利用用户已登录态发起非预期请求，核心条件是浏览器会自动携带 Cookie。",
        "防御应组合 SameSite Cookie、CSRF Token、关键操作二次确认与 Origin/Referer 校验。",
        "只依赖验证码或检查是否登录并不能证明请求来自用户主动操作。",
        "教学场景可以用转账、改邮箱、绑定账号等状态变更接口说明风险。",
    ],
    "file-upload": [
        "文件上传漏洞的风险来自扩展名校验不足、MIME 信任、路径穿越、解析器差异和上传后可执行。",
        "安全设计应把文件存到 Web 根目录外，重命名对象 key，并按白名单校验类型与大小。",
        "图片处理、压缩包解压和 Office/PDF 预览都需要单独的沙箱或异步扫描流程。",
        "演示时强调 object_key 与 storage_objects 管理，避免把大文件直接塞进业务表。",
    ],
}


def _source_profile(slug: str) -> dict[str, object]:
    default = {
        "platform": "manual",
        "url": f"https://demo.securehub.local/websec/{slug}.md",
        "author": "SecureHub 课程组",
        "license": "demo-only",
        "rights_note": "团队整理的课程演示材料，可在比赛演示中展示。",
    }
    return SOURCE_PROFILES.get(slug, default)


def _chunk_texts(slug: str, name: str) -> list[str]:
    hints = TOPIC_HINTS.get(
        slug,
        [
            f"{name} 是 Web 安全基础课程中的关键概念，需要先理解 HTTP 请求、响应、状态与浏览器安全边界。",
            f"学习 {name} 时应把攻击面、触发条件、影响范围和防御控制拆开分析，避免只记 payload。",
            f"工程修复要结合输入校验、输出编码、权限控制、日志监控和安全测试形成闭环。",
            f"课程演示围绕 {name} 提供讲解、测验、实操和证据卡片，所有来源保留 platform、url、author 与 rights_note。",
        ],
    )
    return hints[:CHUNKS_PER_DOC]


async def _seed(session: AsyncSession) -> dict[str, int]:
    courses = CourseRepository(session)
    graph = KnowledgeGraphRepository(session)
    documents = DocumentRepository(session)
    chunks = ChunkRepository(session)
    assets = DocumentAssetRepository(session)
    storage_objects = StorageObjectRepository(session)

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

    # ---- documents + assets + chunks ----
    fetched_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
    for slug, name, level in WEBSEC_NODES:
        did = document_id(slug)
        profile = _source_profile(slug)
        markdown_body = "\n\n".join([f"# {name}", *_chunk_texts(slug, name)])
        markdown_bytes = markdown_body.encode("utf-8")
        markdown_hash = sha256(markdown_bytes).hexdigest()
        object_key = f"course_websec/seed/{slug}.md"
        if await storage_objects.get_by_key(object_key) is None:
            await storage_objects.create(
                storage_id=stable_id(f"storage:websec:{slug}:markdown"),
                object_key=object_key,
                provider="local",
                bucket="securehub-demo",
                original_filename=f"{slug}.md",
                mime_type="text/markdown; charset=utf-8",
                size_bytes=len(markdown_bytes),
                content_hash=markdown_hash,
                status="ready",
                metadata={
                    "domain": DOMAIN,
                    "asset_type": "markdown_full",
                    "seed": "seed_course_websec",
                },
            )
        source_metadata = {
            "platform": profile["platform"],
            "source_url": profile["url"],
            "author": profile["author"],
            "published_at": None,
            "fetched_at": fetched_at.isoformat(),
            "license": profile["license"],
            "rights_note": profile["rights_note"],
            "asset_type": "markdown_full",
            "kp_slug": slug,
            "level": level,
            "type": "概念",
        }
        existing_document = await documents.get_by_id(did)
        if existing_document is None:
            await documents.create(
                document_id=did,
                domain=DOMAIN,
                source_type="manual_import",
                title=f"{name} · 教学讲义",
                url=str(profile["url"]),
                content_hash=markdown_hash,
                raw_text=markdown_body,
                metadata=source_metadata,
                trust_score=0.9,
                status="ready",
                fetched_at=fetched_at,
            )
            doc_count += 1
        else:
            existing_document.source_type = "manual_import"
            existing_document.title = f"{name} · 教学讲义"
            existing_document.url = str(profile["url"])
            existing_document.content_hash = markdown_hash
            existing_document.raw_text = markdown_body
            existing_document.metadata_ = source_metadata
            existing_document.trust_score = 0.9
            existing_document.status = "ready"
            existing_document.fetched_at = fetched_at
            await session.flush()
        existing_assets = await assets.list_by_document(did)
        if not any(asset.object_key == object_key for asset in existing_assets):
            await assets.create(
                asset_id=stable_id(f"asset:websec:{slug}:markdown_full"),
                document_id=did,
                asset_type="markdown_full",
                object_key=object_key,
                mime_type="text/markdown; charset=utf-8",
                size_bytes=len(markdown_bytes),
                content_hash=markdown_hash,
                metadata={"kp_slug": slug, "source": "seed_course_websec"},
            )

        existing_chunks = await chunks.list_by_document(did)
        if existing_chunks:
            by_index = {row.chunk_index: row for row in existing_chunks}
            for i, chunk_text in enumerate(_chunk_texts(slug, name)):
                row = by_index.get(i)
                if row is None:
                    continue
                row.chunk_text = chunk_text
                row.token_count = len(chunk_text.split())
                row.embedding_status = row.embedding_status or "pending"
                row.metadata_ = {
                    "kp_slug": slug,
                    "kp_ids": [str(node_id(slug))],
                    "section": i + 1,
                    "platform": profile["platform"],
                    "source_url": profile["url"],
                    "author": profile["author"],
                    "published_at": None,
                    "fetched_at": fetched_at.isoformat(),
                    "license": profile["license"],
                    "rights_note": profile["rights_note"],
                    "asset_type": "markdown_full",
                    "chapter": name,
                    "reliability": 0.9,
                }
            await session.flush()
            continue
        chunk_rows: list[Chunk] = []
        for i, chunk_text in enumerate(_chunk_texts(slug, name)):
            chunk_rows.append(
                Chunk(
                    id=chunk_id(slug, i),
                    document_id=did,
                    domain=DOMAIN,
                    chunk_text=chunk_text,
                    chunk_index=i,
                    token_count=len(chunk_text.split()),
                    embedding=None,
                    embedding_status="pending",
                    metadata_={
                        "kp_slug": slug,
                        "kp_ids": [str(node_id(slug))],
                        "section": i + 1,
                        "platform": profile["platform"],
                        "source_url": profile["url"],
                        "author": profile["author"],
                        "published_at": None,
                        "fetched_at": fetched_at.isoformat(),
                        "license": profile["license"],
                        "rights_note": profile["rights_note"],
                        "asset_type": "markdown_full",
                        "chapter": name,
                        "reliability": 0.9,
                    },
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
