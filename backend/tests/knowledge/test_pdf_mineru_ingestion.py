# Status: real

from pathlib import Path

import pytest
from sqlalchemy import select

from app.db.models.knowledge.chunk import Chunk
from app.db.models.knowledge.document import Document
from app.db.models.knowledge.document_asset import DocumentAsset
from app.knowledge.loaders.course_loader import pdf_mineru_import
from app.services.knowledge.chapter_classifier import HeadingLevel
from app.services.knowledge.chunking_service import ChunkingService


CHINESE_TEXTBOOK_FIXTURE = """
# 示例中文教材

## 第1章 概论

### 章节内容
密码学的基本概念和安全目标。

## 1.1 信息安全目标
本节讨论机密性、完整性和可用性。

## 1.1.1 机密性
机密性的定义和典型场景。

## (1) 定义
这是条目内容。

## 第2章 对称加密
AES 算法和分组密码模式。

## 2.1 分组模式
ECB、CBC 和 CTR 模式。
""".strip()


def test_split_into_chapters_by_chinese_chapter_anchor() -> None:
    chapters = ChunkingService.split_into_chapters(CHINESE_TEXTBOOK_FIXTURE)

    assert len(chapters) == 2
    assert chapters[0].title.startswith("第1章")
    assert chapters[1].title.startswith("第2章")
    assert chapters[0].heading_path_root == ["示例中文教材"]


def test_split_into_chapters_fallback_when_no_chapter_anchor() -> None:
    chapters = ChunkingService.split_into_chapters("# 无章节教材\n\n## 1.1 绪论\n正文")

    assert len(chapters) == 1
    assert chapters[0].level == HeadingLevel.BOOK
    assert chapters[0].title == "无章节教材"


def test_split_chapter_into_chunks_carries_heading_path() -> None:
    chapter = ChunkingService.split_into_chapters(CHINESE_TEXTBOOK_FIXTURE)[0]
    chunks = ChunkingService().split_chapter_into_chunks(
        chapter,
        chunk_size=120,
        chunk_overlap=20,
    )

    assert chunks
    joined_paths = [" / ".join(chunk.heading_path) for chunk in chunks]
    assert any("第1章 概论" in path for path in joined_paths)
    assert any("1.1 信息安全目标" in path for path in joined_paths)
    assert any(chunk.section_hint == "1.1 信息安全目标" for chunk in chunks)


@pytest.mark.anyio
async def test_pdf_mineru_import_creates_chapter_assets_end_to_end(
    sqlite_session,
    tmp_path: Path,
) -> None:
    pdf_path, mineru_dir = _write_fixture_pdf_and_markdown(tmp_path)

    result = await pdf_mineru_import(
        pdf_path,
        session=sqlite_session,
        mineru_output_dir=mineru_dir,
        title="示例中文教材",
        source_url="local://fixture.pdf",
        metadata={
            "license": "proprietary-educational-use",
            "rights_note": "教材版权归原作者与出版社，仅用于 SecureHub 教学演示 RAG 检索。",
        },
        storage_local_root=tmp_path / "storage",
    )
    await sqlite_session.commit()

    assets = (await sqlite_session.execute(select(DocumentAsset))).scalars().all()
    chunks = (await sqlite_session.execute(select(Chunk))).scalars().all()

    assert result.document_ids
    assert result.asset_count == 4
    assert {asset.asset_type for asset in assets} == {
        "original_pdf",
        "markdown_full",
        "markdown_chapter",
    }
    assert sum(asset.asset_type == "markdown_chapter" for asset in assets) == 2
    assert chunks
    assert all(chunk.metadata_["source_type"] == "pdf_mineru" for chunk in chunks)
    assert all(chunk.metadata_["asset_id"] for chunk in chunks)
    assert all(chunk.metadata_["chapter"] for chunk in chunks)
    assert all(chunk.metadata_["heading_path"] for chunk in chunks)
    assert all(chunk.metadata_["book_title"] == "示例中文教材" for chunk in chunks)


@pytest.mark.anyio
async def test_pdf_mineru_import_is_idempotent_via_pdf_hash(
    sqlite_session,
    tmp_path: Path,
) -> None:
    pdf_path, mineru_dir = _write_fixture_pdf_and_markdown(tmp_path)

    first = await pdf_mineru_import(
        pdf_path,
        session=sqlite_session,
        mineru_output_dir=mineru_dir,
        title="示例中文教材",
        source_url="local://fixture.pdf",
        storage_local_root=tmp_path / "storage",
    )
    second = await pdf_mineru_import(
        pdf_path,
        session=sqlite_session,
        mineru_output_dir=mineru_dir,
        title="示例中文教材",
        source_url="local://fixture.pdf",
        storage_local_root=tmp_path / "storage",
    )
    await sqlite_session.commit()

    documents = (await sqlite_session.execute(select(Document))).scalars().all()
    chunks = (await sqlite_session.execute(select(Chunk))).scalars().all()

    assert first.chunk_count > 0
    assert second.document_ids == first.document_ids
    assert second.chunk_count == 0
    assert second.asset_count == 0
    assert len(documents) == 1
    assert len(chunks) == first.chunk_count


@pytest.mark.anyio
async def test_pdf_mineru_import_force_reingest_reuses_existing_document_chunks(
    sqlite_session,
    tmp_path: Path,
) -> None:
    pdf_path, mineru_dir = _write_fixture_pdf_and_markdown(tmp_path)

    first = await pdf_mineru_import(
        pdf_path,
        session=sqlite_session,
        mineru_output_dir=mineru_dir,
        title="示例中文教材",
        source_url="local://fixture.pdf",
        storage_local_root=tmp_path / "storage",
    )
    second = await pdf_mineru_import(
        pdf_path,
        session=sqlite_session,
        mineru_output_dir=mineru_dir,
        title="示例中文教材",
        source_url="local://fixture.pdf",
        force_reingest=True,
        storage_local_root=tmp_path / "storage",
    )
    await sqlite_session.commit()

    assert second.document_ids == first.document_ids
    assert second.chunk_count == first.chunk_count


@pytest.mark.anyio
async def test_pdf_mineru_import_rejects_storage_prefix_inside_input_dir(
    sqlite_session,
    tmp_path: Path,
) -> None:
    pdf_path, mineru_dir = _write_fixture_pdf_and_markdown(tmp_path)

    with pytest.raises(ValueError, match="MinerU input directory"):
        await pdf_mineru_import(
            pdf_path,
            session=sqlite_session,
            mineru_output_dir=mineru_dir,
            title="示例中文教材",
            storage_local_root=tmp_path,
            storage_prefix="fixture",
        )


def _write_fixture_pdf_and_markdown(tmp_path: Path) -> tuple[Path, Path]:
    pdf_path = tmp_path / "fixture.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% fixture pdf bytes\n")
    mineru_dir = tmp_path / "fixture"
    mineru_dir.mkdir()
    (mineru_dir / "full.md").write_text(CHINESE_TEXTBOOK_FIXTURE, encoding="utf-8")
    return pdf_path, mineru_dir
