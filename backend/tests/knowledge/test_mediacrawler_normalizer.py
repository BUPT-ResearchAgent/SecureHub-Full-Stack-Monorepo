# Status: real

import json
from pathlib import Path

from sqlalchemy import select

import pytest

from app.db.models.knowledge.document import Document
from app.db.models.knowledge.document_asset import DocumentAsset
from app.db.models.storage.storage_object import StorageObject
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
    assert source.metadata["collection_mode"] == "mediacrawler"
    assert "参数化查询" in source.raw_text
    assert source.metadata["rights_note"]


def test_media_source_normalizer_maps_zhihu_answer_fields() -> None:
    source = normalize_mediacrawler_content(
        {
            "content_id": "3248658267",
            "content_type": "answer",
            "content_text": "什么是 XSS &amp; CSRF，参数化查询如何阻断 SQL 注入。",
            "content_url": "https://www.zhihu.com/question/21606800/answer/3248658267",
            "question_id": "21606800",
            "title": "零基础如何学习 Web 安全？",
            "created_time": 1697195309,
            "updated_time": 1733046261,
            "voteup_count": 44,
            "comment_count": 3,
            "source_keyword": "web安全",
            "user_nickname": "ailx10",
            "user_id": "raw-user-id",
            "user_avatar": "https://example.test/avatar.jpg",
        },
        platform="zhihu",
        rights_note="知乎 UGC 用户内容；仅学习用途保留摘要与引用；不批量搬运。",
    )

    assert source.platform == "zhihu"
    assert source.title == "零基础如何学习 Web 安全？"
    assert source.url.endswith("/answer/3248658267")
    assert source.metadata["platform"] == "zhihu"
    assert source.metadata["question_id"] == "21606800"
    assert source.metadata["content_id"] == "3248658267"
    assert source.metadata["media_id"] == "3248658267"
    assert source.metadata["author"] == "ailx10"
    assert source.metadata["metrics"]["voteup_count"] == 44
    assert source.metadata["updated_at"]
    assert "XSS & CSRF" in source.raw_text
    assert "知乎 UGC" in source.metadata["rights_note"]


def test_media_source_normalizer_maps_xhs_field_variants() -> None:
    source = normalize_mediacrawler_content(
        {
            "id": "xhs-alt-001",
            "display_title": "什么是 SQL 注入？",
            "content": "用预编译语句隔离输入和 SQL 语法。",
            "url": "https://www.xiaohongshu.com/explore/xhs-alt-001?xsec_token=secret",
            "user": {"nickname": "安全笔记"},
            "created_time": 1779530102000,
            "images": [
                "https://example.test/cover.webp?xsec_token=secret",
                {"url": "https://example.test/second.webp?sign=secret", "user_signature": "drop-me"},
            ],
            "source_keyword": "sql注入",
        },
        platform="xhs",
        rights_note="小红书 UGC 用户内容；仅学习用途保留摘要与引用；不批量搬运。",
    )

    assert source.platform == "xhs"
    assert source.metadata["media_id"] == "xhs-alt-001"
    assert source.metadata["author"] == "安全笔记"
    assert source.metadata["source_url"] == "https://www.xiaohongshu.com/explore/xhs-alt-001"
    assert source.metadata["cover_or_images"] == [
        "https://example.test/cover.webp",
        {"url": "https://example.test/second.webp"},
    ]
    assert "预编译语句" in source.raw_text


def test_media_source_normalizer_maps_bili_field_variants() -> None:
    source = normalize_mediacrawler_content(
        {
            "bvid": "BV1variant",
            "url": "https://www.bilibili.com/video/BV1variant?spm_id_from=333.999",
            "title": "XSS 防护实战讲解",
            "description": "演示输出编码与内容安全策略。",
            "user_name": "Web安全UP",
            "pubdate": 1760000000,
            "cover_url": "https://i0.hdslb.com/bfs/archive/example.jpg",
            "play_count": "1200",
            "like_count": "88",
            "favorite_count": "12",
            "coin_count": "6",
            "danmaku_count": "3",
            "comment_count": "2",
            "subtitle": "转写文本包含 DOM XSS 与 CSP。",
        },
        platform="bili",
        comments=[
            {
                "video_id": "BV1variant",
                "content": "CSP 示例很清楚。",
                "nickname": "学生A",
            }
        ],
        rights_note="Bilibili UGC 用户内容，仅学习用途保留摘要与引用；不下载原视频，不批量转载。",
    )

    assert source.platform == "bili"
    assert source.source_type == "media_post"
    assert source.metadata["platform"] == "bili"
    assert source.metadata["media_id"] == "BV1variant"
    assert source.metadata["media_type"] == "video"
    assert source.metadata["source_url"] == "https://www.bilibili.com/video/BV1variant"
    assert source.metadata["author"] == "Web安全UP"
    assert source.metadata["published_at"]
    assert source.metadata["cover_url"].endswith("example.jpg")
    assert source.metadata["metrics"]["play_count"] == "1200"
    assert source.metadata["metrics"]["liked_count"] == "88"
    assert source.metadata["metrics"]["favorite_count"] == "12"
    assert source.metadata["metrics"]["coin_count"] == "6"
    assert source.metadata["metrics"]["danmaku_count"] == "3"
    assert source.metadata["metrics"]["comment_count"] == "2"
    assert source.metadata["collection_mode"] == "mediacrawler"
    assert source.metadata["license"] == "platform terms / non-commercial learning reference"
    assert "转写文本包含 DOM XSS 与 CSP" in source.raw_text
    assert "采样评论" in source.raw_text


@pytest.mark.anyio
async def test_mediacrawler_export_import_writes_assets_and_chunks(
    sqlite_session,
    tmp_path: Path,
) -> None:
    export_dir = tmp_path / "mediacrawler" / "bili"
    storage_root = tmp_path / "storage"
    export_dir.mkdir(parents=True)
    (export_dir / "bili_contents.jsonl").write_text(
        json.dumps(
            {
                "bvid": "BV1securehub",
                "video_url": "https://www.bilibili.com/video/BV1securehub",
                "title": "SQL 注入基础讲解",
                "desc": "演示联合查询注入与参数化查询防护。",
                "author": "Web安全讲师",
                "publish_time": 1760000000,
                "liked_count": "100",
                "video_comment": "2",
                "video_play_count": "1000",
                "video_favorite_count": "30",
                "video_coin_count": "5",
                "video_danmaku": "7",
                "video_cover_url": "https://i0.hdslb.com/bfs/archive/cover.jpg",
                "transcript": "这段转写讨论 union select 与 prepared statement。",
                "user_id": "raw-user-id",
                "avatar": "https://example.test/avatar.jpg",
                "cookie": "SESSDATA=secret",
                "xsec_token": "xsec-secret",
                "ip_location": "北京",
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
                "uid": "comment-uid",
                "mid": "comment-mid",
                "avatar": "https://example.test/comment-avatar.jpg",
                "ip_location": "上海",
                "home_url": "https://space.bilibili.com/123",
                "csrf_token": "csrf-secret",
                "created_time": 1760000001,
                "like_count": 3,
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
        storage_prefix="course_websec/test/mediacrawler",
        storage_local_root=storage_root,
    )
    await sqlite_session.commit()

    documents = (await sqlite_session.execute(select(Document))).scalars().all()
    assets = (await sqlite_session.execute(select(DocumentAsset))).scalars().all()
    objects = (await sqlite_session.execute(select(StorageObject))).scalars().all()
    hits = await RetrievalService(sqlite_session).retrieve(
        "联合查询 参数化查询",
        domain="course_websec",
        top_k=3,
        filters={"platform": "bili"},
    )

    assert result.content_count == 1
    assert result.comment_count == 1
    assert result.asset_count == 2
    assert result.chunk_count >= 1
    assert documents[0].metadata_["platform"] == "bili"
    assert documents[0].metadata_["collection_mode"] == "mediacrawler"
    assert documents[0].metadata_["source_url"] == "https://www.bilibili.com/video/BV1securehub"
    assert documents[0].metadata_["author"] == "Web安全讲师"
    assert documents[0].metadata_["published_at"]
    assert documents[0].metadata_["fetched_at"]
    assert documents[0].metadata_["rights_note"]
    assert documents[0].metadata_["media_id"] == "BV1securehub"
    assert documents[0].metadata_["media_type"] == "video"
    assert documents[0].metadata_["license"] == "platform terms / non-commercial learning reference"
    assert {asset.asset_type for asset in assets} == {"media_item_json", "media_comment_json"}
    assert hits
    assert hits[0].metadata["platform"] == "bili"
    assert hits[0].metadata["collection_mode"] == "mediacrawler"

    stored_payloads = "\n".join(
        (storage_root / obj.object_key).read_text(encoding="utf-8")
        for obj in objects
    )
    for forbidden in (
        "raw-user-id",
        "comment-uid",
        "comment-mid",
        "SESSDATA",
        "xsec-secret",
        "csrf-secret",
        "avatar.jpg",
        "comment-avatar",
        "ip_location",
        "space.bilibili.com",
    ):
        assert forbidden not in stored_payloads

    comment_asset = next(asset for asset in assets if asset.asset_type == "media_comment_json")
    comment_payload = json.loads((storage_root / comment_asset.object_key).read_text(encoding="utf-8"))
    assert comment_payload == [
        {
            "content": "联合查询前先判断列数这个点很清楚。",
            "nickname": "学生甲",
            "created_time": 1760000001,
            "like_count": 3,
        }
    ]


@pytest.mark.anyio
async def test_mediacrawler_export_import_skips_bad_jsonl_lines(
    sqlite_session,
    tmp_path: Path,
) -> None:
    export_dir = tmp_path / "mediacrawler" / "xhs"
    storage_root = tmp_path / "storage"
    export_dir.mkdir(parents=True)
    (export_dir / "xhs_contents.jsonl").write_text(
        "{bad json line}\n"
        + json.dumps(
            {
                "note_id": "xhs-parse-ok",
                "title": "SQL 注入小红书笔记",
                "desc": "参数化查询是基础防护。",
                "note_url": "https://www.xiaohongshu.com/explore/xhs-parse-ok?xsec_token=secret",
                "nickname": "安全学习者",
                "time": 1779530102000,
                "user_id": "raw-user-id",
                "avatar": "https://example.test/avatar.jpg",
                "xsec_token": "secret",
                "user_signature": "signature-secret",
                "ip_location": "北京",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = await import_mediacrawler_exports(
        [export_dir],
        session=sqlite_session,
        platform="xhs",
        storage_prefix="course_websec/test/mediacrawler",
        storage_local_root=storage_root,
        rights_note="小红书 UGC 用户内容；仅学习用途保留摘要与引用；不批量搬运。",
    )
    await sqlite_session.commit()

    documents = (await sqlite_session.execute(select(Document))).scalars().all()
    objects = (await sqlite_session.execute(select(StorageObject))).scalars().all()
    stored_payloads = "\n".join(
        (storage_root / obj.object_key).read_text(encoding="utf-8")
        for obj in objects
    )

    assert result.skipped_count == 1
    assert result.content_count == 1
    assert documents[0].metadata_["platform"] == "xhs"
    assert documents[0].metadata_["source_url"] == "https://www.xiaohongshu.com/explore/xhs-parse-ok"
    for forbidden in ("raw-user-id", "avatar.jpg", "xsec_token", "signature-secret", "ip_location"):
        assert forbidden not in stored_payloads


@pytest.mark.anyio
async def test_mediacrawler_export_import_writes_zhihu_documents(
    sqlite_session,
    tmp_path: Path,
) -> None:
    export_dir = tmp_path / "mediacrawler" / "zhihu"
    storage_root = tmp_path / "storage"
    export_dir.mkdir(parents=True)
    (export_dir / "zhihu_contents.jsonl").write_text(
        json.dumps(
            {
                "content_id": "zhihu-answer-1",
                "content_type": "answer",
                "content_text": "授权检查缺失会导致越权漏洞，RBAC 是常见防护模型。",
                "content_url": "https://www.zhihu.com/question/1/answer/zhihu-answer-1",
                "question_id": "1",
                "title": "Web 安全如何理解授权？",
                "created_time": 1779937204,
                "updated_time": 1779937204,
                "voteup_count": 3,
                "comment_count": 0,
                "source_keyword": "web安全",
                "user_nickname": "web安全成长日记",
                "user_id": "raw-user-id",
                "user_link": "https://www.zhihu.com/people/example",
                "user_avatar": "https://example.test/avatar.jpg",
                "user_url_token": "example",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = await import_mediacrawler_exports(
        [export_dir],
        session=sqlite_session,
        platform="zhihu",
        storage_prefix="course_websec/test/mediacrawler",
        storage_local_root=storage_root,
        rights_note="知乎 UGC 用户内容；仅学习用途保留摘要与引用；不批量搬运。",
    )
    await sqlite_session.commit()

    document = (await sqlite_session.execute(select(Document))).scalar_one()
    hits = await RetrievalService(sqlite_session).retrieve(
        "授权 越权 RBAC",
        domain="course_websec",
        top_k=3,
        filters={"platform": "zhihu"},
    )

    assert result.content_count == 1
    assert result.skipped_count == 0
    assert document.metadata_["platform"] == "zhihu"
    assert document.metadata_["question_id"] == "1"
    assert document.metadata_["content_id"] == "zhihu-answer-1"
    assert document.metadata_["rights_note"].startswith("知乎 UGC")
    assert hits
    assert hits[0].metadata["platform"] == "zhihu"
