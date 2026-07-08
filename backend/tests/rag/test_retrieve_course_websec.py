# Status: real

from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db.models.knowledge.chunk import Chunk
from app.db.models.knowledge.document import Document
from app.db.models.knowledge.knowledge_node import KnowledgeNode
from app.db.models.learning.quiz_item import QuizItem
from app.db.seeds.seed_course_websec import run as seed_course_websec
from app.knowledge.loaders.course_loader import pdf_mineru_import
from app.services.knowledge.retrieval_service import RetrievalService


RAG_SMOKE_QUERIES = [
    ("SQL 注入是什么", {"SQL", "注入"}),
    ("SQL 注入如何防御", {"SQL", "防御"}),
    ("参数化查询的作用", {"参数化", "查询"}),
    ("XSS 和 SQL 注入的区别", {"XSS", "SQL"}),
    ("文件上传漏洞风险", {"文件", "上传"}),
    ("CSRF Token SameSite 防御", {"CSRF", "SameSite"}),
    ("SSRF 内网 云元数据 防御", {"SSRF", "内网"}),
    ("访问控制 越权 权限校验", {"访问控制", "权限"}),
    ("命令执行 RCE 如何修复", {"命令执行", "RCE"}),
    ("反序列化漏洞 如何防御", {"反序列化", "防御"}),
    ("安全编码 修复闭环", {"安全编码", "修复"}),
]


@pytest.mark.anyio
async def test_retrieve_course_websec_returns_evidence_fields(sqlite_session) -> None:
    await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    hits = await RetrievalService(sqlite_session).retrieve(
        "SQL 注入 参数化查询",
        domain="course_websec",
        top_k=5,
    )

    assert len(hits) >= 3
    assert hits[0].score > 0
    assert "SQL" in hits[0].snippet or "参数化" in hits[0].snippet
    for hit in hits:
        assert hit.metadata["source_url"]
        assert hit.metadata["platform"]
        assert hit.metadata["author"]
        assert "rights_note" in hit.metadata
        assert hit.metadata["collection_mode"] == "manual"
        assert hit.metadata["asset_type"] in {"markdown_full", "manual_import"}


@pytest.mark.anyio
async def test_retrieve_course_websec_supports_platform_filter(sqlite_session) -> None:
    await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    hits = await RetrievalService(sqlite_session).retrieve(
        "CSRF Token SameSite",
        domain="course_websec",
        top_k=5,
        filters={"platform": "portswigger"},
    )

    assert hits
    assert all(hit.metadata["platform"] == "portswigger" for hit in hits)


@pytest.mark.anyio
async def test_course_websec_fixed_rag_smoke_queries(sqlite_session) -> None:
    await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    retriever = RetrievalService(sqlite_session)
    for query, expected_terms in RAG_SMOKE_QUERIES:
        hits = await retriever.retrieve(query, domain="course_websec", top_k=12)

        assert len(hits) >= 3, f"{query!r} should have enough evidence"
        joined = "\n".join(f"{hit.title}\n{hit.snippet}" for hit in hits)
        for term in expected_terms:
            assert term in joined, f"{query!r} should retrieve evidence containing {term!r}"


@pytest.mark.anyio
async def test_course_websec_seeds_sql_injection_quiz_items(sqlite_session) -> None:
    await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    quiz_items = (
        await sqlite_session.execute(
            select(QuizItem).where(QuizItem.question.like("%SQL 注入%"))
        )
    ).scalars().all()

    assert len(quiz_items) >= 5
    assert {item.type for item in quiz_items} >= {
        "single_choice",
        "multi_choice",
        "short_answer",
    }
    assert all(item.kp_id for item in quiz_items)


@pytest.mark.anyio
async def test_course_websec_seed_is_idempotent_and_covers_required_floor(
    sqlite_session,
) -> None:
    first = await seed_course_websec(sqlite_session)
    await sqlite_session.commit()
    second = await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    chunk_total = await sqlite_session.scalar(
        select(func.count()).select_from(Chunk).where(Chunk.domain == "course_websec")
    )
    node_total = await sqlite_session.scalar(
        select(func.count()).select_from(KnowledgeNode).where(
            KnowledgeNode.domain == "course_websec"
        )
    )
    quiz_total = await sqlite_session.scalar(
        select(func.count()).select_from(QuizItem).where(
            QuizItem.question.like("%SQL 注入%")
        )
    )

    assert first["chunks"] >= 10
    assert first["nodes"] >= 3
    assert first["quiz_items"] >= 5
    assert second == {
        "courses": 0,
        "nodes": 0,
        "edges": 0,
        "documents": 0,
        "chunks": 0,
        "quiz_items": 0,
    }
    assert chunk_total >= 10
    assert node_total >= 3
    assert quiz_total >= 5


@pytest.mark.anyio
async def test_course_websec_seed_covers_official_manual_and_pdf_evidence(
    sqlite_session,
) -> None:
    await seed_course_websec(sqlite_session)
    await sqlite_session.commit()

    documents = (
        await sqlite_session.execute(
            select(Document).where(Document.domain == "course_websec")
        )
    ).scalars().all()
    retriever = RetrievalService(sqlite_session)
    pdf_hits = await retriever.retrieve(
        "SSRF 云元数据 内网",
        domain="course_websec",
        top_k=5,
        filters={"asset_type": "pdf"},
    )

    platforms = {document.metadata_.get("platform") for document in documents}
    required_metadata = {
        "platform",
        "source_url",
        "author",
        "rights_note",
        "collection_mode",
        "asset_type",
    }

    assert {"owasp", "portswigger", "manual", "mineru"} <= platforms
    for document in documents:
        missing = required_metadata - set(document.metadata_)
        assert not missing, f"{document.title} missing metadata fields: {missing}"
        assert document.metadata_["source_url"]
        assert document.metadata_["rights_note"]

    assert pdf_hits
    assert any(
        hit.metadata.get("page_no") or hit.metadata.get("chapter") for hit in pdf_hits
    )
    assert all(hit.metadata["platform"] == "mineru" for hit in pdf_hits)


@pytest.mark.anyio
async def test_course_websec_retrieves_textbook_mineru_topics(
    sqlite_session,
    tmp_path: Path,
) -> None:
    fixtures = [
        (
            "crypto-basics",
            "现代密码学教程（第2版）",
            """# 现代密码学教程

## 第1章 密码学概论
密码学讨论 ECB 分组模式、RSA 公钥密码、哈希函数和 TLS 协议。

## 1.1 信息安全目标
机密性、完整性和认证都依赖密码算法。""",
            {"ECB", "RSA"},
            "ECB RSA 哈希 TLS",
        ),
        (
            "network-security",
            "网络安全原理与实践",
            """# 网络安全原理与实践

## 第4章 对称加密
网络安全课程覆盖 IPSec、防火墙、入侵检测系统和无线网络安全。

## 4.1 安全体系
访问控制与身份认证是网络防护的重要基础。""",
            {"IPSec", "防火墙"},
            "IPSec 防火墙 入侵检测 无线网络安全",
        ),
        (
            "reverse-engineering",
            "汇编语言（第3版）",
            """# 汇编语言

## 第2章 寄存器
汇编语言使用寄存器、内存地址和 loop 指令组织底层程序。

## 2.1 通用寄存器
AX、BX、CX、DX 是典型的 8086 通用寄存器。""",
            {"寄存器", "loop"},
            "汇编语言 寄存器 loop 指令",
        ),
    ]

    for index, (name, title, markdown, _terms, _query) in enumerate(fixtures):
        mineru_dir = tmp_path / name
        mineru_dir.mkdir()
        (mineru_dir / "full.md").write_text(markdown, encoding="utf-8")
        pdf_path = mineru_dir / f"fixture-{name}.pdf"
        pdf_path.write_bytes(f"%PDF-1.4\n% {name} fixture {index}\n".encode("utf-8"))
        await pdf_mineru_import(
            pdf_path,
            session=sqlite_session,
            mineru_output_dir=mineru_dir,
            title=title,
            source_url=f"local://{name}.pdf",
            storage_local_root=tmp_path / "storage",
        )
    await sqlite_session.commit()

    retriever = RetrievalService(sqlite_session)
    for _name, _title, _markdown, expected_terms, query in fixtures:
        hits = await retriever.retrieve(
            query,
            domain="course_websec",
            top_k=8,
            filters={"source_type": "pdf_mineru"},
        )

        assert hits, f"{query!r} should retrieve textbook evidence"
        joined = "\n".join(f"{hit.title}\n{hit.snippet}" for hit in hits)
        for term in expected_terms:
            assert term in joined
        assert all(hit.metadata["platform"] == "mineru" for hit in hits)
        assert all(hit.metadata["asset_type"] == "markdown_chapter" for hit in hits)
