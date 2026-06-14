# MediaCrawler export structure notes

Status: real

更新时间：2026-06-13

## 调研结论

MediaCrawler 公开项目将平台数据分为 `contents`、`comments`、`creators` 三类，并支持 CSV、JSON、JSONL、Excel、SQLite、MySQL、PostgreSQL 等保存方式。SecureHub 只消费离线导出的 CSV / JSON / JSONL，不复用 MediaCrawler 的平台专用表结构。

本阶段适配范围：

| platform | content id | title | body | url | author | published_at | comments parent |
|---|---|---|---|---|---|---|---|
| `xhs` | `note_id` | `title` | `desc` | `note_url` | `nickname` | `time` | `note_id` |
| `bili` | `video_id` | `title` | `desc` | `video_url` | `nickname` | `create_time` | `video_id` |
| `zhihu` | `content_id` | `title` | `content_text` / `desc` | `content_url` | `user_nickname` | `created_time` | `content_id` |

## SecureHub 落库映射

所有内容项进入统一知识资产层：

```text
MediaCrawler export item
  -> media_source_normalizer
  -> storage_objects
  -> documents
  -> document_assets
  -> chunks
```

字段映射：

```text
platform      -> documents.metadata.platform / chunks.metadata.platform
source_url    -> documents.url / metadata.source_url
author        -> metadata.author
published_at  -> metadata.published_at
fetched_at    -> metadata.fetched_at
rights_note   -> metadata.rights_note
raw item      -> document_assets.asset_type=media_item_json
comments      -> document_assets.asset_type=media_comment_json
```

## 合规边界

- 仅支持离线导入公开样本，不执行登录、验证码、风控绕过或大规模采集。
- 对平台内容保留 `platform / source_url / author / published_at / fetched_at / rights_note`。
- 版权不明内容仅作为学习与比赛演示的摘要、证据与切片来源，不做完整转载展示。
- 不新增 `bili_chunks`、`zhihu_chunks`、`xhs_chunks` 等平台专用表。

## 参考来源

- MediaCrawler repository: `https://github.com/NanmiCoder/MediaCrawler`
- Store implementation examples: `store/xhs/_store_impl.py`, `store/bilibili/_store_impl.py`, `store/zhihu/_store_impl.py`
- Model field reference: `database/models.py`
