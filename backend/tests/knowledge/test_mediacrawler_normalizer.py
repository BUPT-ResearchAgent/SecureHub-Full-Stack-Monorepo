# Status: real

import json
from pathlib import Path

from sqlalchemy import select

import pytest

from app.db.models.knowledge.document import Document
from app.db.models.knowledge.document_asset import DocumentAsset
from app.services.knowledge.crawling.media_source_normalizer import (
    normalize_mediacrawler_content,
)
from app.services.knowledge.crawling.mediacrawler_export_import import (
    import_mediacrawler_exports,
)
from app.services.knowledge.retrieval_service import RetrievalService


def test_media_source_normalizer_maps_xhs_content() -> None:
    source = normalize_mediacrawler_content(
        {
            "note_id": "xhs-001",
            "title": "SQL 注入学习笔记",
            "desc": "参数化查询能阻断大多数拼接型 SQL 注入。",
            "note_url": "https://www.xiaohongshu.com/explore/xhs-001",
            "nickname": "安全学习者",
            "time": 1760000000,
            "liked_count": "12",
            "tag_list": '["Web安全", "SQL注入"]',
        },
        platform="xhs",
        comments=[{"note_id": "xhs-001", "content": "这条适合新手复习", "nickname": "同学A"}],
    )

    assert source.platform == "xhs"
    assert source.metadata["platform"] == "xhs"
    assert source.metadata["source_url"].endswith("xhs-001")
    assert source.metadata["author"] == "安全学习者"
    assert "参数化查询" in source.raw_text
    assert source.metadata["rights_note"]


@pytest.mark.anyio
async def test_mediacrawler_export_import_writes_assets_and_chunks(
    sqlite_session,
    tmp_path: Path,
) -> None:
    export_dir = tmp_path / "mediacrawler" / "bili"
    export_dir.mkdir(parents=True)
    (export_dir / "bili_contents.jsonl").write_text(
        json.dumps(
            {
                "video_id": "BV1securehub",
                "video_url": "https://www.bilibili.com/video/BV1securehub",
                "title": "SQL 注入基础讲解",
                "desc": "演示联合查询注入与参数化查询防护。",
                "nickname": "Web安全讲师",
                "create_time": 1760000000,
                "liked_count": "100",
                "video_comment": "2",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (export_dir / "bili_comments.jsonl").write_text(
        json.dumps(
            {
                "comment_id": "c1",
                "video_id": "BV1securehub",
                "content": "联合查询前先判断列数这个点很清楚。",
                "nickname": "学生甲",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = await import_mediacrawler_exports(
        [export_dir],
        session=sqlite_session,
        platform="bili",
    )
    await sqlite_session.commit()

    documents = (await sqlite_session.execute(select(Document))).scalars().all()
    assets = (await sqlite_session.execute(select(DocumentAsset))).scalars().all()
    hits = await RetrievalService(sqlite_session).retrieve(
        "联合查询 参数化查询",
        domain="course_websec",
        top_k=3,
        filters={"platform": "bili"},
    )

    assert result.content_count == 1
    assert result.comment_count == 1
    assert result.asset_count == 2
    assert documents[0].metadata_["platform"] == "bili"
    assert {asset.asset_type for asset in assets} == {"media_item_json", "media_comment_json"}
    assert hits
