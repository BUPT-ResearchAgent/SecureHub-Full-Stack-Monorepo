# Status: real

import json
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db.models.knowledge.chunk import Chunk
from app.db.models.knowledge.document import Document
from app.db.models.knowledge.document_asset import DocumentAsset
from app.db.models.storage.storage_object import StorageObject
from app.services.knowledge.crawling.mindspider_adapter import (
    RIGHTS_NOTE,
    import_mindspider_fixture,
    normalize_mindspider_topic,
    redact_fixture_topic,
)


def test_mindspider_topic_normalizer_maps_reference_metadata() -> None:
    source = normalize_mindspider_topic(
        {
            "topic_id": "ms_topic_test",
            "keyword": "SQL 注入热点",
            "platforms": ["zhihu", "bili"],
            "hot_score": 88,
            "sample_urls": ["https://example.org/sql"],
            "collected_at": "2026-07-08T00:00:00Z",
            "sentiment": "concern",
            "abstract": "参数化查询与输入校验被反复讨论。",
        }
    )

    assert source.domain == "news"
    assert source.source_type == "mindspider_reference"
    assert source.metadata["platform"] == "mindspider_reference"
    assert source.metadata["collection_mode"] == "mindspider_reference"
    assert source.metadata["rights_note"] == RIGHTS_NOTE
    assert source.metadata["hot_score"] == 88
    assert source.metadata["cross_platforms"] == ["zhihu", "bili"]
    assert "参数化查询" in source.raw_text


def test_mindspider_redaction_keeps_only_fixture_fields() -> None:
    redacted = redact_fixture_topic(
        {
            "topic_id": "ms_topic_test",
            "keyword": "XSS",
            "user_id": "raw-user",
            "avatar": "https://example.org/avatar.png",
            "token": "secret",
            "abstract": "demo",
        }
    )

    assert redacted == {
        "topic_id": "ms_topic_test",
        "keyword": "XSS",
        "abstract": "demo",
    }


@pytest.mark.anyio
async def test_mindspider_fixture_import_writes_documents_assets_chunks(
    sqlite_session,
    tmp_path: Path,
) -> None:
    fixture = _write_fixture(tmp_path, count=2)

    result = await import_mindspider_fixture(
        fixture,
        session=sqlite_session,
        storage_prefix="news/test/mindspider_reference",
        storage_local_root=tmp_path / "storage",
    )
    await sqlite_session.commit()

    documents = (await sqlite_session.execute(select(Document))).scalars().all()
    assets = (await sqlite_session.execute(select(DocumentAsset))).scalars().all()
    chunks = (await sqlite_session.execute(select(Chunk))).scalars().all()

    assert result.topic_count == 2
    assert len(result.document_ids) == 2
    assert result.asset_count == 2
    assert result.chunk_count >= 2
    assert {document.metadata_["platform"] for document in documents} == {"mindspider_reference"}
    assert all(document.metadata_["collection_mode"] == "mindspider_reference" for document in documents)
    assert {asset.asset_type for asset in assets} == {"media_item_json"}
    assert chunks
    assert all(chunk.metadata_["platform"] == "mindspider_reference" for chunk in chunks)
    assert all(chunk.chunk_text for chunk in chunks)


@pytest.mark.anyio
async def test_mindspider_fixture_import_is_idempotent(
    sqlite_session,
    tmp_path: Path,
) -> None:
    fixture = _write_fixture(tmp_path, count=1)

    first = await import_mindspider_fixture(
        fixture,
        session=sqlite_session,
        storage_prefix="news/test/mindspider_reference",
        storage_local_root=tmp_path / "storage",
    )
    second = await import_mindspider_fixture(
        fixture,
        session=sqlite_session,
        storage_prefix="news/test/mindspider_reference",
        storage_local_root=tmp_path / "storage",
    )
    await sqlite_session.commit()

    documents = (await sqlite_session.execute(select(Document))).scalars().all()
    chunks = (await sqlite_session.execute(select(Chunk))).scalars().all()
    assert first.document_ids == second.document_ids
    assert len(documents) == 1
    assert len(chunks) == first.chunk_count


@pytest.mark.anyio
async def test_mindspider_stored_json_has_no_unexpected_pii(
    sqlite_session,
    tmp_path: Path,
) -> None:
    fixture = _write_fixture(tmp_path, count=1, include_pii=True)
    storage_root = tmp_path / "storage"

    await import_mindspider_fixture(
        fixture,
        session=sqlite_session,
        storage_prefix="news/test/mindspider_reference",
        storage_local_root=storage_root,
    )
    await sqlite_session.commit()

    objects = (await sqlite_session.execute(select(StorageObject))).scalars().all()
    stored = "\n".join((storage_root / obj.object_key).read_text(encoding="utf-8") for obj in objects)
    assert "raw-user-id" not in stored
    assert "secret-token" not in stored
    assert "avatar.png" not in stored


def _write_fixture(tmp_path: Path, *, count: int, include_pii: bool = False) -> Path:
    topics = []
    for index in range(count):
        topic = {
            "topic_id": f"ms_topic_{index:03d}",
            "keyword": f"Web 安全热点 {index}",
            "platforms": ["zhihu", "bili"],
            "hot_score": 80 + index,
            "sample_urls": [f"https://example.org/topic/{index}"],
            "collected_at": "2026-07-08T00:00:00Z",
            "sentiment": "learning",
            "abstract": f"SQL 注入、XSS 与访问控制讨论 {index}。",
        }
        if include_pii:
            topic.update(
                {
                    "user_id": "raw-user-id",
                    "token": "secret-token",
                    "avatar": "https://example.org/avatar.png",
                }
            )
        topics.append(topic)
    fixture = tmp_path / "hot_topics_fixture.json"
    fixture.write_text(json.dumps({"topics": topics}, ensure_ascii=False), encoding="utf-8")
    return fixture
