# MindSpider Reference Structure

Status: real

更新时间：2026-07-08

## 定位

MindSpider 在 SecureHub 中只作为 P2 参考级主题发现输入，用于 hot_analyst 未来 demo 的舆情背景。当前实现只消费本地 fixture，不运行 MindSpider 爬虫本体，不注册 `mindspider_agent`，不新增平台专用表。

## Fixture 结构

输入文件：`data/raw/mindspider/hot_topics_fixture.json`

```json
{
  "topics": [
    {
      "topic_id": "ms_topic_001",
      "keyword": "SQL 注入 2026 新型攻击",
      "platforms": ["weibo", "zhihu", "bili"],
      "hot_score": 87,
      "sample_urls": ["https://example.org/security/sql-injection-2026"],
      "collected_at": "2026-07-08T00:00:00Z",
      "sentiment": "concern",
      "abstract": "近期 SQL 注入讨论集中在 ..."
    }
  ]
}
```

## 落库映射

```text
MindSpider fixture topic
  -> mindspider_adapter.normalize_mindspider_topic
  -> storage_objects
  -> documents
  -> document_assets(media_item_json)
  -> chunks
```

字段约定：

| 字段 | 值 |
|---|---|
| `documents.domain` | `news` |
| `documents.source_type` | `mindspider_reference` |
| `documents.metadata.platform` | `mindspider_reference` |
| `documents.metadata.collection_mode` | `mindspider_reference` |
| `documents.metadata.rights_note` | `MindSpider 参考级；仅 hot_analyst P2 demo；不涉及实际爬虫` |
| `documents.metadata.hot_score` | fixture `hot_score` |
| `documents.metadata.sentiment` | fixture `sentiment` |
| `documents.metadata.cross_platforms` | fixture `platforms` |
| `document_assets.asset_type` | `media_item_json` |

## 合规边界

- 只使用人工构造 fixture，不连接真实平台。
- 不保存真实用户 ID、头像、cookie、token、IP 属地等 PII。
- 不进入生产采集主链路；只作为 P2 demo reference。
- 统一复用 `documents / document_assets / chunks / storage_objects`，不新增 topic/comment 专用表。
