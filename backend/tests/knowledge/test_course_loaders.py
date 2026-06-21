# Status: real

from pathlib import Path

import pytest
from sqlalchemy import select

from app.db.models.knowledge.document_asset import DocumentAsset
from app.db.models.storage.storage_object import StorageObject
from app.knowledge.loaders.course_loader import markdown_import, pdf_mineru_import
from app.services.knowledge.retrieval_service import RetrievalService


@pytest.mark.anyio
async def test_markdown_import_writes_assets_and_retrievable_chunks(
    sqlite_session,
    tmp_path: Path,
) -> None:
    source = tmp_path / "sql-injection.md"
    source.write_text(
        """---
title: SQL 注入教学片段
platform: manual
source_url: https://demo.securehub.local/manual/sql-injection
author: SecureHub 课程组
rights_note: 团队整理的课程演示材料。
---
# SQL 注入教学片段

SQL 注入的核心问题是把未受信任输入拼接进查询语句。参数化查询可以把输入与 SQL 语法分离。
""",
        encoding="utf-8",
    )

    result = await markdown_import([source], session=sqlite_session)
    await sqlite_session.commit()

    assets = (await sqlite_session.execute(select(DocumentAsset))).scalars().all()
    objects = (await sqlite_session.execute(select(StorageObject))).scalars().all()
    hits = await RetrievalService(sqlite_session).retrieve(
        "SQL 注入 参数化查询",
        domain="course_websec",
        top_k=3,
    )

    assert result.document_ids
    assert result.asset_count == 1
    assert assets[0].asset_type == "markdown_full"
    assert objects[0].object_key.endswith("sql-injection.md")
    assert hits


@pytest.mark.anyio
async def test_pdf_mineru_import_fallback_registers_pdf_and_markdown_assets(
    sqlite_session,
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "websec-upload.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% demo pdf bytes\n")

    result = await pdf_mineru_import(
        pdf_path,
        session=sqlite_session,
        title="文件上传漏洞讲义",
        source_url="https://demo.securehub.local/pdf/websec-upload.pdf",
    )
    await sqlite_session.commit()

    assets = (await sqlite_session.execute(select(DocumentAsset))).scalars().all()
    objects = (await sqlite_session.execute(select(StorageObject))).scalars().all()

    assert result.asset_count == 2
    assert {asset.asset_type for asset in assets} == {"original_pdf", "markdown_full"}
    assert {obj.mime_type for obj in objects} >= {
        "application/pdf",
        "text/markdown; charset=utf-8",
    }


@pytest.mark.anyio
async def test_pdf_mineru_import_registers_local_markdown_images(
    sqlite_session,
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "websec-textbook.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% demo pdf bytes\n")
    mineru_dir = tmp_path / "mineru"
    image_dir = mineru_dir / "assets"
    image_dir.mkdir(parents=True)
    image_path = image_dir / "page-001.jpg"
    image_path.write_bytes(b"fake jpeg bytes")
    markdown_path = mineru_dir / "full.md"
    markdown_path.write_text(
        "# Web Security Textbook\n\n![page](assets/page-001.jpg)\n\nSQL injection basics.",
        encoding="utf-8",
    )

    result = await pdf_mineru_import(
        pdf_path,
        session=sqlite_session,
        mineru_output_dir=mineru_dir,
        title="Web Security Textbook",
    )
    await sqlite_session.commit()

    assets = (await sqlite_session.execute(select(DocumentAsset))).scalars().all()
    objects = (await sqlite_session.execute(select(StorageObject))).scalars().all()

    assert result.asset_count == 3
    assert {asset.asset_type for asset in assets} == {
        "original_pdf",
        "markdown_full",
        "page_image",
    }
    image_asset = next(asset for asset in assets if asset.asset_type == "page_image")
    image_object = next(obj for obj in objects if obj.object_key == image_asset.object_key)
    assert image_object.mime_type == "image/jpeg"
    assert image_asset.metadata_["markdown_ref"] == "assets/page-001.jpg"
