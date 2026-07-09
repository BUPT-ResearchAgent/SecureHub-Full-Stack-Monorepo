# 7-COS-3 交付报告：GitHub 外数据私有同步到 COS 与上传门禁预留

## 1. 本轮目标

将 GitHub 不保存但团队需要同步的数据按 allowlist 上传到私有 COS 前缀，生成无 Secret、可审计的 JSONL manifest，并通过 HEAD / GET hash / Signed URL / `storage_objects` 校验确认 COS 可作为团队私有同步介质。同时预留后端上传门禁接口 `POST /api/v1/uploads/init`，不做前端、不做 `/uploads/complete`。

## 2. Inventory 分类结果

命令：

```powershell
cd SecureHub-Full-Stack-Monorepo\backend
uv run python scripts/sync_cos_private_data.py --inventory-only
```

结果摘要：

- `GIT_IGNORED_DISCOVERY count=966`
- `PRIVATE_SYNC_INVENTORY_TOTAL count=1094`
- `allowed_runtime_asset=870`
- `allowed_private_textbook=18`
- `allowed_db_backup=0`
- `blocked_secret=7`
- `blocked_pii_or_platform_raw=65`
- `blocked_tool_cache=3`
- `blocked_unknown=131`

## 3. 上传范围与未上传范围

已上传：20 个默认 allowlist 图片资产，均来自：

```text
data/processed/mineru/Web安全基础教程/assets/image_0001_*.jpg
...
data/processed/mineru/Web安全基础教程/assets/image_0020_*.jpg
```

未上传：

- 未上传 `.env*`、`SecretKey.csv`、`account.csv`。
- 未上传 raw MediaCrawler、sqlite/db、`.codegraph`、`data/reports`。
- 未上传 PDF / `full.md`，因为本轮没有传 `--include-textbook-private`。
- 未上传 `.dump` / `.backup`，因为本轮没有传 `--include-db-dump` 且 inventory 中为 0。

## 4. COS 前缀与 manifest 摘要

COS object_key 前缀：

```text
private/team-sync/data/data/processed/mineru/Web安全基础教程/assets/
```

manifest：

```text
SecureHub-Full-Stack-Monorepo/data/manifests/cos_private_team_sync_manifest.jsonl
```

manifest 共 20 行，字段为：

```text
provider / bucket / object_key / source_relpath / classification / sha256 / size_bytes / mime_type / rights_note / migration_batch / created_at
```

manifest 不包含 Secret、Signed URL、本地用户目录绝对路径。

## 5. storage_objects 校验

DB 连接使用本地 compose PostgreSQL，宿主机端口为 `15432`；报告不记录数据库凭据。

统计结果：

```text
provider=cos bucket=anshu-skq-1385633904 status=ready count=20
```

每条记录由 `StorageService.put_bytes()` upsert，metadata 包含 `classification` / `migration_batch` / `rights_note` / `source_relpath`。

## 6. Signed URL / hash 验证结果

命令：

```powershell
uv run python scripts/verify_cos_private_sync.py --limit 10
```

结果：

```text
COS_PRIVATE_SYNC_URL_OK count=10
COS_PRIVATE_SYNC_HASH_OK count=10
STORAGE_OBJECTS_PRIVATE_SYNC_OK count=10
```

验证脚本只输出状态标记，不打印完整 Signed URL。

## 7. 上传门禁接口与规则

新增后端接口：

```text
POST /api/v1/uploads/init
```

新增配置项：

```text
UPLOAD_GATE_ENABLED
UPLOAD_GATE_SECRET_HASH
UPLOAD_GATE_MAX_BYTES
UPLOAD_GATE_ALLOWED_MIME_PREFIXES
UPLOAD_GATE_ALLOWED_PREFIXES
UPLOAD_GATE_PRESIGNED_EXPIRES_SECONDS
```

规则：

- `X-SecureHub-Upload-Key` 只与 `UPLOAD_GATE_SECRET_HASH` 做 SHA-256 常量时间比较，不存明文密钥。
- 超过 `UPLOAD_GATE_MAX_BYTES` 返回 413。
- 不允许的 MIME 返回 400。
- 不允许的 target prefix 返回 400。
- 后端忽略客户端完整 object_key，只生成 `tmp/uploads/<uuid>/<safe_filename>`。
- 不允许写入 `private/team-sync/`、`runtime/`、`backups/`。
- 本轮未实现 `/uploads/complete`、浏览器 UI、CDN。

## 8. 测试结果

dry-run：

```powershell
uv run python scripts/sync_cos_private_data.py --dry-run --limit 20
```

结果：`COS_PRIVATE_SYNC_DRY_RUN count=20`，未上传、未写 manifest。

upload / verify：

```powershell
uv run python scripts/sync_cos_private_data.py --upload --verify --limit 20
```

结果：

```text
COS_PRIVATE_SYNC_UPLOAD_OK count=20
COS_PRIVATE_SYNC_HEAD_OK count=20
COS_PRIVATE_SYNC_GET_HASH_OK count=20
STORAGE_OBJECTS_PRIVATE_SYNC_UPSERT_OK count=20
LOCAL_PRIVATE_SYNC_SOURCE_OK count=20
MANIFEST_PRIVATE_SYNC_WRITE_OK count=20
```

pytest：

```powershell
uv run pytest tests/services/storage tests/api tests/scripts -q
```

结果：`22 passed`。

兼容性抽测：

```powershell
uv run pytest tests/knowledge/test_course_loaders.py tests/knowledge/test_mindspider_adapter.py -q
```

结果：`8 passed`。

## 9. 安全自检

- Secret 未写入 Git、manifest、日志或报告。
- 未打印完整 Signed URL。
- 未上传 `.env*`、`SecretKey.csv`、`account.csv`。
- 未上传 raw MediaCrawler / sqlite / `.codegraph`。
- Bucket 仍按私有读写 + Signed URL 使用。
- local 原始数据未删除。
- `backend/.env` 仍为 ignored：`!! backend/.env`。
- 未修改 frontend、agents、runtime harness、DB migrations、EvidenceDTO 契约。

## 10. 回滚方式

代码回滚：仅回滚本轮新增的 private sync 脚本、上传门禁文件、路由注册、配置项、测试和报告；不要对当前脏工作区执行全量 reset。

COS 数据回滚：按 `data/manifests/cos_private_team_sync_manifest.jsonl` 中的 20 个 `object_key` 由项目负责人在控制台或后续专用脚本删除。本轮不开放 `private/team-sync/*` Delete。

DB 回滚：按 `metadata.migration_batch = "7-COS-3-private-sync"` 或 `object_key like 'private/team-sync/%'` 定位清理，不要全表删除。

## 11. 下一轮建议

先观察这 20 个私有图片资产在多成员环境中的可恢复性和 manifest 消费流程。稳定后再讨论是否扩大到更多 `data/processed/mineru/**/assets`；教材 PDF / `full.md` 只应在项目负责人明确确认后用 `--include-textbook-private` 单独执行。
