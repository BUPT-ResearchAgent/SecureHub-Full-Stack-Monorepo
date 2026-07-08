# MediaCrawler export structure notes

Status: real

更新时间：2026-07-08

## 调研结论

MediaCrawler 公开项目将平台数据分为 `contents`、`comments`、`creators` 三类，并支持 CSV、JSON、JSONL、Excel、SQLite、MySQL、PostgreSQL 等保存方式。SecureHub 只消费离线导出的 CSV / JSON / JSONL，不复用 MediaCrawler 的平台专用表结构。

本阶段适配范围：

| platform | content id | title | body | url | author | published_at | comments parent |
|---|---|---|---|---|---|---|---|
| `xhs` | `note_id` | `title` | `desc` | `note_url` | `nickname` | `time` | `note_id` |
| `bili` | `video_id` / `bvid` / `bv_id` | `title` | `desc` / `description` | `video_url` / `url` | `nickname` / `user_name` / `author` | `create_time` / `publish_time` / `pubdate` | `video_id` / `bvid` / `bv_id` |
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

B 站额外兼容字段：

```text
cover_url      <- video_cover_url / cover_url
metrics        <- video_comment / comment_count, video_play_count / play_count,
                  liked_count / like_count, video_favorite_count / favorite_count,
                  video_coin_count / coin_count, video_danmaku / danmaku_count,
                  video_share_count / share_count
transcript     <- transcript / subtitle / asr_text / caption_text
```

## 2026-07-08 B 站真实 export 导入

输入目录：`data/raw/mediacrawler/bili/jsonl/`

| 文件 | 类型 | 条数 | 入库行为 |
|---|---|---:|---|
| `search_contents_2026-06-15.jsonl` | contents | 19 | 入 `documents` / `document_assets(media_item_json)` / `chunks` |
| `search_creators_2026-06-15.jsonl` | creators | 19 | 跳过，不作为课程 document 入库 |

本批次没有 comments export，因此不生成 `media_comment_json`。contents 中提供 `video_cover_url`，仅写入 metadata 的 `cover_url`；未下载封面图片，也未生成 `cover_image` asset。本批次未提供 transcript/subtitle/asr/caption 字段。

写入前清洗字段：

```text
cookies / cookie / token / csrf / xsec_token / session / credential
user_id / uid / mid / sec_uid
avatar / avatar_url / face / head_url
ip_location / home_url / homepage / signature / sign
```

评论导入时只保留 `content`、`nickname`、`created_time`、`like_count`；不保留 UID、头像、主页、签名、IP 属地等 PII。

## 合规边界

- 仅支持离线导入公开样本，不执行登录、验证码、风控绕过或大规模采集。
- 对平台内容保留 `platform / source_url / author / published_at / fetched_at / rights_note`。
- B 站导入只消费人工提供的离线 export，不运行 MediaCrawler 爬虫本体，不下载原视频。
- 版权不明内容仅作为学习与比赛演示的摘要、证据与切片来源，不做完整转载展示。
- 不新增 `bili_chunks`、`zhihu_chunks`、`xhs_chunks` 等平台专用表。

## 参考来源

- MediaCrawler repository: `https://github.com/NanmiCoder/MediaCrawler`
- Store implementation examples: `store/xhs/_store_impl.py`, `store/bilibili/_store_impl.py`, `store/zhihu/_store_impl.py`
- Model field reference: `database/models.py`
