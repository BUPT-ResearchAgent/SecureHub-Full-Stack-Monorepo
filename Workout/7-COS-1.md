# 7-COS-1 交付报告：Tencent COS Storage Provider

## 1. 本轮目标

完成 SecureHub storage layer 第一档工程化接入：保留 local provider，新增 Tencent COS provider，补齐配置、依赖、mock 单测与真实 COS smoke，不做业务数据迁移、不做浏览器直传、不改前端。

## 2. 实现摘要

- `StorageService` 已从直接本地文件 I/O 重构为 provider-backed 服务，继续负责 SHA-256、`storage_objects` 写入/更新与状态字段。
- `StorageService(session, local_root=...)` 保持旧语义：调用方显式传 `local_root` 且未显式传 `settings` / `storage_provider` 时，强制使用 local provider，避免离线 loader 在本机 COS 环境下误触真实云。
- 新增 `StorageProvider` Protocol、`LocalStorageProvider`、`CosStorageProvider` 与 provider factory。
- COS SDK 同步调用已用 `asyncio.to_thread()` 包裹。
- local provider 保留目录穿越防护。
- COS provider 支持 `put_bytes` / `get_bytes` / `exists` / `delete` / `presigned_url`，并将 404 映射为 `None` / `False` / 幂等删除。
- 新增手动 smoke 脚本，只操作 `tmp/smoke/<uuid>.txt`。

## 3. 文件变更清单

- `backend/pyproject.toml`
- `backend/uv.lock`
- `backend/.env.example`
- `backend/app/core/config.py`
- `backend/app/services/storage/storage_service.py`
- `backend/app/services/storage/provider_factory.py`
- `backend/app/services/storage/providers/__init__.py`
- `backend/app/services/storage/providers/base.py`
- `backend/app/services/storage/providers/local.py`
- `backend/app/services/storage/providers/cos.py`
- `backend/tests/services/storage/test_local_provider.py`
- `backend/tests/services/storage/test_cos_provider.py`
- `backend/tests/services/storage/test_storage_service.py`
- `backend/scripts/smoke_cos_storage.py`

## 4. 配置说明

`.env.example` 默认仍为：

```env
STORAGE_PROVIDER=local
```

新增变量名：

- `STORAGE_PROVIDER`
- `STORAGE_LOCAL_ROOT`
- `COS_SECRET_ID`
- `COS_SECRET_KEY`
- `COS_REGION`
- `COS_BUCKET`
- `COS_SCHEME`
- `COS_PRESIGNED_EXPIRES_SECONDS`
- `COS_UPLOAD_MAX_BYTES`

`STORAGE_PROVIDER=cos` 时，`COS_SECRET_ID`、`COS_SECRET_KEY`、`COS_REGION`、`COS_BUCKET` 必须非空，否则配置初始化 fail-fast。

## 5. 测试结果

- 单元测试：`cd backend && uv run pytest tests/services/storage`
  - 结果：`10 passed`
- 兼容性抽测：`cd backend && uv run pytest tests/knowledge/test_course_loaders.py tests/knowledge/test_mindspider_adapter.py`
  - 结果：`8 passed`
- 真实 smoke：`cd backend && uv run python scripts/smoke_cos_storage.py`
  - `COS_UPLOAD_OK`
  - `COS_HEAD_OK`
  - `COS_DOWNLOAD_OK`
  - `COS_SIGNED_URL_OK`
  - `COS_DELETE_OK`

## 6. 安全自检

- Secret 未写入 Git；`.env.example` 只包含空值模板。
- `git status --short --ignored -- backend/.env` 显示 `backend/.env` 仍为 ignored。
- smoke 脚本不打印 Secret，不打印完整 Signed URL。
- 本轮未修改 Bucket ACL；代码不设置公开读，继续按私有读写 Bucket + Signed URL 使用。
- 未迁移教材 PDF / `full.md`。
- 未修改前端、agent、harness、migration、data 目录。
- 未新增第 10 个 agent。
- 未新增 storage 相关数据库表。

## 7. 未做事项

- 未做浏览器直传。
- 未做全量迁移。
- 未做 CDN / 自定义域名。
- 未迁移教材 PDF / `full.md`。

## 8. 下一轮建议

进入 7-COS-2：选择 10 个 `mineru_ingested` assets 做小样本迁移，生成 manifest，并通过 EvidenceDrawer 验证 Signed URL 展示链路。
