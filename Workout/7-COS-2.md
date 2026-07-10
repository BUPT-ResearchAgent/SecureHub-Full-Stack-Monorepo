# 7-COS-2 交付报告：COS 小样本资产迁移与 manifest 同步

## 1. 本轮目标

本轮目标是从仓库内 `data/storage/course_websec/mineru_ingested/**/assets/*` 选择最多 10 个可重建图片资产，小样本迁移到 COS `runtime/course_websec/mineru_ingested/**/assets/**`，生成无敏感信息 manifest，并提供 Signed URL 下载校验脚本。

## 2. 小样本选择

- 文件数量：0。
- slug 分布：无。
- 文件类型：无。
- 原因：当前 `SecureHub-Full-Stack-Monorepo/data/storage/course_websec/mineru_ingested/` 只有 `README.md`，没有 `**/assets/*` 图片候选。
- 未触碰 PDF / `full.md`：脚本只扫描 `mineru_ingested/**/assets/*` 且仅允许 `.png` / `.jpg` / `.jpeg` / `.webp`。

## 3. 实现摘要

- 已将 7-COS-1 报告同步到项目根 `Workout/7-COS-1.md`，未删除仓库内旧报告。
- 新增 `backend/scripts/migrate_cos_assets_sample.py`：
  - 支持 `--dry-run`、`--limit`、`--verify`、`--manifest`。
  - 只扫描 `data/storage/course_websec/mineru_ingested/**/assets/*`。
  - 正式迁移时上传 COS、HEAD 校验、可选 GET hash 校验、写 manifest、upsert `storage_objects`。
  - 当前候选为 0，因此没有实际上传 COS 对象，也没有新增 `storage_objects` 行。
- 新增 `backend/scripts/verify_cos_asset_urls.py`：
  - 读取 manifest，生成 Signed GET URL，用 `httpx` 下载并校验 hash。
  - 不打印完整 Signed URL。

## 4. 文件变更清单

- `backend/scripts/migrate_cos_assets_sample.py`
- `backend/scripts/verify_cos_asset_urls.py`
- `data/manifests/cos_runtime_assets_sample.jsonl`
- `Workout/7-COS-1.md`
- `Workout/7-COS-2.md`

## 5. manifest 说明

- 路径：`SecureHub-Full-Stack-Monorepo/data/manifests/cos_runtime_assets_sample.jsonl`
- 当前条数：0。
- 字段设计：`provider` / `bucket` / `object_key` / `source_relpath` / `sha256` / `size_bytes` / `mime_type` / `rights_note` / `migration_batch` / `created_at`。
- 安全性：manifest 当前为空；脚本不会写入 Secret、Signed URL 或本地用户目录绝对路径。

## 6. 数据库校验

- 当前候选资产数为 0，未执行任何 COS 样本 upsert。
- 预期有候选时，脚本通过 `StorageService` upsert `storage_objects`：
  - `provider = "cos"`
  - `bucket = COS_BUCKET`
  - `status = "ready"`
  - `metadata` 包含 `migration_batch` / `rights_note` / `source_relpath`

## 7. 测试结果

- dry-run：`cd backend && uv run python scripts/migrate_cos_assets_sample.py --dry-run --limit 10`
  - 输出：`COS_ASSET_DRY_RUN count=0`
- upload / verify：`cd backend && uv run python scripts/migrate_cos_assets_sample.py --limit 10 --verify`
  - `COS_ASSET_UPLOAD_OK count=0`
  - `COS_ASSET_HEAD_OK count=0`
  - `COS_ASSET_GET_HASH_OK count=0`
  - `STORAGE_OBJECTS_UPSERT_OK count=0`
  - `LOCAL_SOURCE_OK count=0`
  - `MANIFEST_WRITE_OK count=0`
- Signed URL 校验：`cd backend && uv run python scripts/verify_cos_asset_urls.py --manifest data/manifests/cos_runtime_assets_sample.jsonl --limit 10`
  - `COS_ASSET_URL_OK count=0`
  - `COS_ASSET_HASH_OK count=0`
- 语法检查：`cd backend && uv run python -m compileall scripts/migrate_cos_assets_sample.py scripts/verify_cos_asset_urls.py`
  - 结果：通过。

## 8. 安全自检

- Secret 未写入 Git、manifest、日志或报告。
- 未打印完整 Signed URL。
- 未迁移教材 PDF / `full.md`。
- 本轮未删除任何本地文件；local 回滚副本保持原状。
- 未修改前端、agent、harness、migration 或 storage provider 核心实现。
- `backend/.env` 仍为 ignored。

## 9. 未做事项

- 未做浏览器直传。
- 未做全量迁移。
- 未做 CDN / 自定义域名。
- 未迁移教材 PDF / `full.md`。

## 10. 下一轮建议

先补齐或重建 `data/storage/course_websec/mineru_ingested/<slug>/assets/*` 小样本图片资产，再重新运行本轮脚本迁移最多 10 个样本。10 个样本稳定后，再讨论是否扩大到全部 `mineru_ingested/**/assets`；不要自动扩大。
