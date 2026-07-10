# SecureHub 数据目录说明

> 本目录承载**所有**素材源、转换过程产物、工程运行时数据。
> 项目根 `26软件杯/` 下**不再**存放数据（历史散落已在 6-C-2-cleanup 归位）。

## 目录约定（分层清晰）

```
data/
├── raw/                                    ← 未处理原始素材（人工放入 / 用户上传）
│   ├── pdf/                                所有教材 / 白皮书 / 论文原 PDF
│   │   ├── Web安全基础教程.pdf
│   │   ├── 现代密码学教程.pdf
│   │   ├── 网络安全原理与实践.pdf
│   │   └── 汇编语言(第3版).pdf
│   └── mediacrawler/                       MediaCrawler 离线导出（6-C-3 消费）
│       ├── bili/jsonl/*.jsonl
│       ├── xhs/jsonl/
│       └── zhihu/jsonl/*.jsonl
│
├── processed/                              已转换但未入库（人工触发的中间产物）
│   └── mineru/
│       └── <教材中文名>/                   一个 MinerU 处理任务对应一个目录
│           ├── full.md                     完整 markdown
│           └── assets/                     图片资产
│
├── reports/                                审计报告 / 评估报告等（人工产出，可能敏感）
│
├── storage/course_websec/                  ★ 工程运行时目录（脚本读写）
│   ├── mineru/                             MinerU **输入**目录（脚本只读）
│   │   ├── crypto-basics/
│   │   │   ├── crypto-basics.pdf          从 raw/pdf/ 复制过来（脚本规范命名）
│   │   │   ├── full.md                    从 processed/mineru/ 复制或 db 恢复
│   │   │   └── assets/                    图片
│   │   ├── network-security/
│   │   ├── reverse-engineering/
│   │   ├── websec-textbook/                Web 安全基础教程
│   │   └── websec-upload/                  5-C seed 占位（保留，test 依赖）
│   │
│   └── mineru_ingested/                    MinerU **入库产物**（脚本写入）
│       └── <slug>/
│           ├── chapters/                   markdown_chapter asset
│           └── assets/                     图片副本
│
├── course_websec/                          课程 source manifest 等元数据
│   └── source_manifest.json
│
└── demo/                                   演示 smoke 日志、7 分钟 checklist 等
    └── smoke/
        ├── backend.stdout.log
        └── backend.stderr.log
```

## 三层严格分离原则（6-C-2 事故经验）

| 层 | 路径 | 谁写入 | 谁读取 | 允许覆盖 |
|---|---|---|---|---|
| **源素材** | `data/raw/`、`data/processed/` | 用户人工 / MinerU 手动 | 迁移脚本按需读 | **禁止**脚本写入 |
| **工程输入** | `data/storage/course_websec/mineru/` | 迁移脚本 / 手动复制 | ingestion 脚本读 | **禁止**入库脚本写入（防事故复发）|
| **工程产物** | `data/storage/course_websec/mineru_ingested/` | ingestion 脚本 | RAG 检索 / EvidenceDrawer | ✅ 脚本可写可覆盖 |

> **6-C-2 事故根因回顾**：旧 storage 默认 prefix 是 `course_websec/mineru`（工程输入），入库脚本写产物时把输入 PDF 覆盖成了 stub。事故后：
> 1. 新默认 prefix = `course_websec/mineru_ingested`（产物落到独立目录）
> 2. `pdf_mineru_import` 加了 `_ensure_storage_target_outside_inputs` 防护函数
> 3. 三层分离用目录名硬约定，绝不再重叠

## Git 追踪规则（详见 `.gitignore`）

| 内容 | Git 状态 | 原因 |
|---|---|---|
| `raw/pdf/*.pdf` | ❌ 忽略 | 教材版权 |
| `raw/mediacrawler/**/*.jsonl` | ❌ 忽略 | PII + 平台版权 |
| `processed/mineru/**/full.md` | ❌ 忽略 | 教材正文 |
| `processed/mineru/**/*.local.md` | ❌ 忽略 | 同上 |
| `processed/mineru/**/manifest.json` | ❌ 忽略 | 含教材元信息 |
| `processed/mineru/**/assets/*.jpg` | ✅ 追踪（默认） | "抽取的公开信息"，合规展示用途；可在 `.gitignore` 里取消注释以排除 |
| `storage/course_websec/mineru/**/*.pdf` | ❌ 忽略 | 工程副本 = 版权文件 |
| `storage/course_websec/mineru/**/full.md` | ❌ 忽略 | 同上 |
| `storage/course_websec/mineru/**/chapters/` | ❌ 忽略 | 章节切分产物（事故遗留兼容） |
| `storage/course_websec/mineru_ingested/**/full.md` | ❌ 忽略 | 入库过程 markdown 副本 |
| `storage/course_websec/mineru_ingested/**/chapters/` | ❌ 忽略 | 入库章节产物（每次跑都可重建） |
| `reports/*.md` | ❌ 忽略 | 可能含内部审计敏感项 |
| `course_websec/source_manifest.json` | ✅ 追踪 | 来源元数据 |
| `demo/**` | ✅ 追踪 | 演示日志需版本化 |

## 添加新教材的标准流程

```
1. 教材 PDF → data/raw/pdf/<中文名>.pdf                      （原始命名，人类可读）
2. 用 MinerU 网页版转换 → data/processed/mineru/<中文名>/
     ├── full.md
     └── assets/
3. 手动复制到工程输入位置：
   Copy-Item data/raw/pdf/<中文名>.pdf `
             data/storage/course_websec/mineru/<slug>/<slug>.pdf
   Copy-Item -Recurse data/processed/mineru/<中文名>/* `
                      data/storage/course_websec/mineru/<slug>/
4. 更新 scripts/ingest/ingest_pdf_mineru_batch.ps1：
   - 加 <slug> 到 $Textbooks 默认数组
   - 加 <slug> → 显示标题 到 $titleMap
5. 运行 batch：
   .\scripts\ingest\ingest_pdf_mineru_batch.ps1 -Textbooks @("<slug>")
6. 更新 docs/demo/websec_source_inventory.md
7. 更新 docs/demo/textbook-rights-policy.md
8. 更新 data/course_websec/source_manifest.json
```

## 添加新爬虫来源的标准流程（6-C-3）

```
1. MediaCrawler / Scrapling / 手动整理 → data/raw/<source>/<platform>/
2. 归一化脚本消费 → 落 documents / document_assets / chunks
3. 更新 docs/demo/source-rights-note.md 补合规说明
```

## 何时可以清理

| 目录 | 何时清理 | 命令示例 |
|---|---|---|
| `storage/course_websec/mineru_ingested/**/chapters/` | 重跑 batch 前 | `Remove-Item -Recurse -Force data/storage/course_websec/mineru_ingested/**/chapters` |
| `processed/mineru/<某教材>/` | 该教材已迁移到 storage/ 且成功入库后 | 人工确认后 `Remove-Item` |
| `raw/pdf/<某教材>.pdf` | **永不清理**（源素材要留档） | — |
| `raw/mediacrawler/**/*.jsonl` | 该批次归一化入库并验收后 | 人工确认后归档到外部备份 |

## 反模式（不允许）

- ❌ 在 `raw/` 或 `processed/` 里跑入库脚本（产物会污染源）
- ❌ 把 `raw/pdf/` 里的 PDF 直接改名成 `<slug>.pdf`（原始命名要保留，转换在复制到 `storage/mineru/` 时做）
- ❌ 把 `26软件杯/data/` 里再放东西（已在 6-C-2-cleanup 归位，未来所有素材都归 `monorepo/data/`）
- ❌ push `raw/pdf/*.pdf` 到 git（`.gitignore` 已排除，若发现被 tracked 请 `git rm --cached`）

---

## 数据库服务运行选项

**当前项目栈**：PostgreSQL 16 + pgvector 扩展 + Redis 7（`docker-compose.yml`）。

### 选项 A · 本地 Docker Compose（默认，推荐日常开发）

`docker-compose.yml` 里已配好 pgvector/pg16 镜像，端口映射到本机 **15432**（避免与本机既有 postgres 冲突）：

```powershell
cd D:\Nnutural\Desktop\BUPT大全\BUPT竞赛\26软件杯\SecureHub-Full-Stack-Monorepo

# 起 postgres + redis
docker compose up -d postgres redis

# 检查健康
docker compose ps
docker compose logs postgres | Select-String "database system is ready"
```

**关键约定**：

| 场景 | DATABASE_URL |
|---|---|
| 在 docker-compose 内部起的 backend | `postgresql+asyncpg://securehub:securehub@postgres:5432/securehub` |
| 本机 `uv run` 跑 pytest / batch 脚本 | `postgresql+asyncpg://securehub:securehub@localhost:15432/securehub` |

**这两个 URL 不一样**（容器内用容器名解析，本机用映射端口）。`.env.local` 里是容器内那份，本机跑脚本时可能需要临时改为 `localhost:15432` 或在 shell 里 `$env:DATABASE_URL="..."` 覆盖。

**首次跑 migration + seed**：

```powershell
cd backend
uv sync
uv run alembic upgrade head              # 建 8 张表 + 装 pgvector 扩展
uv run python -m app.db.seeds.seed_agents        # 9 个 agent
uv run python -m app.db.seeds.seed_agent_skills  # skill 注册
uv run python -m app.db.seeds.seed_demo_user     # demo 用户 + user_profile
uv run python -m app.db.seeds.seed_course_websec # WebSec 演示 chunks
```

**停止和清理**：

```powershell
docker compose down                              # 停容器，保留数据（pgdata volume）
docker compose down -v                           # 停容器 + 删数据（慎用！会清空 db）
```

### 选项 B · 云 PostgreSQL（长期 / 演示 / 团队协作推荐）

| 服务 | 免费额度 | pgvector 支持 | 迁移难度 |
|---|---|---|---|
| **Neon**（推荐） | 3 GB / 项目暂停自动省钱 | ✅ 原生 | 一行改 DATABASE_URL |
| **Supabase** | 500 MB / 需暖机 | ✅ 原生 | 同上 |
| **Aiven** | 30 天试用 | ✅ | 同上 |
| **阿里云 RDS** | 首年优惠 | ✅ 但需选 pgvector 版本 | 需白名单 IP |
| **腾讯云 PostgreSQL** | 试用 | ⚠️ 部分版本支持 | 需白名单 IP |

**切换到 Neon 的 5 步**：

```powershell
# 1. neon.tech 注册 → 建项目（选 PostgreSQL 16 + region us-east）
# 2. Neon dashboard → SQL Editor → 执行 CREATE EXTENSION vector;
# 3. 本地 pg_dump 备份
docker compose exec postgres pg_dump -U securehub -Fc securehub > backup.dump

# 4. pg_restore 到 Neon
$NEON_URL = "postgresql://user:pass@ep-xxx.us-east.aws.neon.tech/securehub"
pg_restore -d $NEON_URL backup.dump

# 5. 改 backend/.env.local
# DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxx.us-east.aws.neon.tech/securehub
# （注意去掉 ?sslmode=require，asyncpg 用 ssl=true 参数）
```

**何时应该切云**：

- ✅ 三人 A / B / C 需要共享同一份 db（每人本地维护 pg_dump 同步成本太高）
- ✅ 演示环境需外部访问（评委 / 教师从校外看 demo）
- ✅ 数据量超过 3 GB（本机磁盘紧张）
- ✅ 团队 CI / GitHub Actions 需要连数据库跑测试

**何时不切云**：

- ❌ 只有一个人开发，本机跑就够
- ❌ 数据敏感（教材版权内容不宜上第三方）
- ❌ 网络不稳定（Neon 需持续在线）

### 选项 C · 本地原生 PostgreSQL

**不推荐**（配置繁琐）：需自装 pg16 + 手动编译 pgvector 扩展 + 权限 / 网络配置。仅在无法用 Docker 时考虑（如 macOS ARM64 早期 pgvector 镜像有问题时）。

---

## 多设备 / 多成员数据同步

### 分层同步矩阵

| 数据层 | 同步方式 | 频率 | 存储介质 | 备注 |
|---|---|---|---|---|
| **代码 + 配置** | `git pull` / `git push` | 实时 | git upstream/dev | 权威源 |
| **元数据 + full.md + README** | 同上 | 实时 | git | v1.1 起 full.md 已进 git |
| **教材 PDF**（202 MB） | 云盘 / 外部硬盘 | 手动 | 云盘 | 不进 git（版权） |
| **MinerU 转换产物**（39 MB） | 云盘 | 手动 | 云盘 | 或从 raw/pdf 重跑 MinerU 重建 |
| **mineru/<slug>/assets/**（80+ MB） | 云盘 | 手动 | 云盘 | 或复制自 processed/mineru/ |
| **mineru_ingested/**（20+ MB） | **不同步** | — | — | 每设备跑 batch 重建，10 分钟 |
| **PostgreSQL db** | `pg_dump` / `pg_restore` 或**云 db 共享** | 增量 | 云盘 dump 文件 or 云 db | 教材 chunks 重跑 batch 也能重建 |
| **MediaCrawler jsonl** | 云盘 | 手动 | 云盘 | 或再次跑 MediaCrawler |

**核心原则**：**git 只同步"可编辑的规范化产物"，大文件走云盘，db 走 dump/restore 或云 db 共享**。

### 场景 1 · 新设备首次搭建（20 分钟）

```powershell
# 1. clone repo
git clone https://github.com/Nnutural/SecureHub-Full-Stack-Monorepo.git
cd SecureHub-Full-Stack-Monorepo

# 2. 从云盘拉大文件（本地 gitignore 排除的部分）
# 手工下载到：
#   data/raw/pdf/*.pdf                                          （202 MB）
#   data/processed/mineru/**/*                                  （39 MB）
#   data/storage/course_websec/mineru/**/assets/*.jpg           （80+ MB）
#   data/storage/course_websec/mineru/**/*.pdf                  （202 MB，同 raw）
# 用 rclone / OneDrive / 百度网盘 / 群晖 均可

# 3. 起 db 服务
docker compose up -d postgres redis

# 4. 初始化 db
cd backend
uv sync
uv run alembic upgrade head

# 5. 恢复 seed（选一）
# 5a. 从云盘拉 pg_dump 恢复（推荐，1 分钟）：
docker compose exec -T postgres pg_restore -U securehub -d securehub < ..\backup.dump

# 5b. 或从 seed + batch 重建（10 分钟）：
uv run python -m app.db.seeds.seed_agents
uv run python -m app.db.seeds.seed_agent_skills
uv run python -m app.db.seeds.seed_demo_user
uv run python -m app.db.seeds.seed_course_websec
cd ..
.\scripts\ingest\ingest_pdf_mineru_batch.ps1
.\scripts\crawl\mediacrawler_bili_import.ps1

# 6. 验证（30 秒快查）
git ls-files "data/raw/pdf/*.pdf" | Measure-Object -Line     # 应为 0 行
Get-ChildItem data\storage\course_websec\mineru\*\full.md | Measure-Object  # 应为 5
cd backend
uv run pytest -m "not llm_live" -q
```

### 场景 2 · 日常增量同步（多设备开发）

```powershell
# 代码 / 元数据 / full.md 变化：
git pull origin dev
git push origin dev

# 教材 PDF / assets 新增或版本更新：
# → 手动上传 / 下载云盘对应目录

# Db 数据变化（新入库了教材 / 新采集了 bili）：
# 方案 A：pg_dump 交换（快）
docker compose exec postgres pg_dump -U securehub -Fc securehub > backup_$(Get-Date -Format yyyyMMdd).dump
# 上传到云盘
# 另一台设备下载 backup_YYYYMMDD.dump 后：
docker compose exec -T postgres pg_restore -U securehub -d securehub --clean --if-exists < backup_YYYYMMDD.dump

# 方案 B：让 batch 从 mineru/ 重跑（幂等，慢一点但可靠）
.\scripts\ingest\ingest_pdf_mineru_batch.ps1
```

### 场景 3 · 灾难恢复（本机数据丢失）

**假设**：本机 `data/` 目录被误删 + docker volume 被清 + 只有 git repo 剩下。

**恢复顺序**（数据来源梯度）：

1. **git 里有的**：`git pull` 拿到 `full.md` + README + 代码 + `source_manifest.json`（约 3 MB） ✅
2. **云盘 pg_dump**：如果有备份，1 分钟恢复整个 db（含 chunks / assets / storage_objects） ✅
3. **云盘大文件**：从云盘拉 `raw/pdf/` + `processed/mineru/` + `mineru/**/assets/`（几分钟到几十分钟）✅
4. **重跑 batch**：从 `mineru/` 里重跑 `ingest_pdf_mineru_batch.ps1`（10 分钟）✅
5. **重跑 MediaCrawler import**：`mediacrawler_bili_import.ps1`（1 分钟）✅

**最坏情况**（连云盘 db 备份都没）：
- 教材 PDF 必须重新下载（从原网站或 U 盘）
- MinerU 转换必须重跑（一本 30 分钟）
- 或从 `full.md`（git 里已有）反向工程出章节（能恢复 chunks 但没有 image assets）

### 场景 4 · 云 db 三人共享（推荐长期）

**目标**：A / B / C 三人共用同一个 Neon db，本地只放大文件。

**架构**：

```
       [Neon cloud PostgreSQL]
              ↑↓ (asyncpg over SSL)
    ┌─────────┼─────────┐
   [A 本机]  [B 本机]  [C 本机]
    ├ code (git)      ├ code (git)      ├ code (git)
    └ 无 data/*        └ 无 data/*       └ raw/pdf/ + processed/ (只 C 维护)
```

**约定**：
- **只有 C 有权跑 batch / MediaCrawler**（避免多人重复入库）
- A / B 通过 db 查询获取现有 chunks，本地不放大文件
- C 每次入库新数据后在 team 频道 tag "@a @b db 已更新，schema 无变化"
- Schema 变化（新迁移）时，A / B 只需 `alembic upgrade head`（对着云 db 跑）

**Secret 管理**：
- Neon connection string 存 `.env.local`（`.gitignore` 已排除）
- 或用 GitHub Codespaces secrets（团队共享）
- **绝不**把 Neon URL 提交到 git 或 PR body

### 云盘工具推荐

| 工具 | 大文件 | 增量同步 | 团队共享 | 免费额度 |
|---|---|---|---|---|
| **OneDrive** | ✅ | ✅ | ✅ | 5 GB |
| **Google Drive** | ✅ | ✅ | ✅ | 15 GB |
| **rclone**（推荐 CLI 用户） | ✅ | ✅（`rclone sync`）| 手动 | 依赖后端 |
| **百度网盘**（大陆备选） | ✅ 但慢 | ⚠️ 需付费 | ⚠️ | 2 TB 免费但限速 |
| **群晖 NAS**（校内 / 家用） | ✅ | ✅ | ✅ | 依设备 |

**推荐目录约定**（云盘上）：

```
SecureHub-Data-Sync/                     ← 云盘共享目录
├── raw/pdf/*.pdf                        （202 MB）
├── processed/mineru/**/*                （39 MB）
├── db-backups/
│   ├── backup_20260707_after_6-C-2.dump
│   ├── backup_20260708_after_6-C-3.dump
│   └── LATEST.dump -> backup_20260708_after_6-C-3.dump  （软链接指向最新）
└── mineru-input-cache/                  可选：mineru/**/assets/ 的备份
```

配套的**同步脚本**（放到 `scripts/sync/` 后续可维护）：

```powershell
# scripts/sync/pull_from_cloud.ps1     — 从云盘拉最新到本地
# scripts/sync/push_db_to_cloud.ps1    — pg_dump 后上传到云盘
# scripts/sync/verify_sync_state.ps1   — 校验本地 vs 云盘 diff
```

---

## 数据库整理与长期治理（沿用 6-C-2 事故经验 + Plan §6）

### 1. Content-hash 幂等模型

`documents.content_hash` = `sha256(pdf_bytes)`。此字段是**入库幂等的唯一 key**：

- 同一 PDF 二次入库 → hash 相同 → 跳过（返回既有 `document_id`）
- PDF 内容变化（换版本 / 事故覆盖）→ hash 变 → 走"新入库"分支
- **危险**：若旧 hash 对应的 documents / chunks 未清理，会产生**幂等假象**（新旧共存，重复检索）

**核心约束**：更换任何一本教材（如从第 2 版换到第 3 版）前，**必须**先清理旧的 db 记录，再重跑 batch。

### 2. Db 清理标准 SQL（教材场景）

**清理某类教材全部记录**（沿用 6-C-2 事故恢复流程）：

```sql
-- 备份：先看会删多少
SELECT count(*) FROM documents WHERE metadata->>'license'='proprietary-educational-use';
SELECT count(*) FROM chunks WHERE document_id IN (
  SELECT id FROM documents WHERE metadata->>'license'='proprietary-educational-use'
);

-- 清理（顺序敏感：先删外键子表，再删父表）
DELETE FROM chunks WHERE document_id IN (
  SELECT id FROM documents WHERE metadata->>'license'='proprietary-educational-use'
);
DELETE FROM document_assets WHERE document_id IN (
  SELECT id FROM documents WHERE metadata->>'license'='proprietary-educational-use'
);
DELETE FROM documents WHERE metadata->>'license'='proprietary-educational-use';
```

**清理某单本教材**（更精细）：

```sql
-- 用 book_title 精确定位（推荐）
DELETE FROM chunks WHERE metadata->>'book_title' = '现代密码学教程（第2版）';
DELETE FROM document_assets WHERE document_id IN (
  SELECT id FROM documents WHERE title = '现代密码学教程（第2版）'
);
DELETE FROM documents WHERE title = '现代密码学教程（第2版）';
```

**清理某类 collection_mode**（如 MediaCrawler 全部）：

```sql
DELETE FROM chunks WHERE document_id IN (
  SELECT id FROM documents WHERE metadata->>'collection_mode'='mediacrawler'
);
DELETE FROM document_assets WHERE document_id IN (
  SELECT id FROM documents WHERE metadata->>'collection_mode'='mediacrawler'
);
DELETE FROM documents WHERE metadata->>'collection_mode'='mediacrawler';
```

### 3. Db 健康检查（每次交付前跑一次）

```sql
-- 1. Documents 分布（各来源 / license 数量）
SELECT
  metadata->>'platform' AS platform,
  metadata->>'collection_mode' AS mode,
  metadata->>'license' AS license,
  count(*)
FROM documents
GROUP BY 1, 2, 3
ORDER BY count DESC;

-- 2. Chunks 密度（每 document 平均 chunk 数）
SELECT
  metadata->>'collection_mode' AS mode,
  count(DISTINCT document_id) AS docs,
  count(*) AS chunks,
  round(count(*)::numeric / NULLIF(count(DISTINCT document_id), 0), 2) AS chunks_per_doc
FROM chunks
JOIN documents ON documents.id = chunks.document_id
GROUP BY 1
ORDER BY 2 DESC;

-- 3. 孤儿 chunks（document 已删但 chunks 残留 —— 应为 0）
SELECT count(*) FROM chunks c
WHERE NOT EXISTS (SELECT 1 FROM documents d WHERE d.id = c.document_id);

-- 4. 孤儿 assets（同上）
SELECT count(*) FROM document_assets a
WHERE NOT EXISTS (SELECT 1 FROM documents d WHERE d.id = a.document_id);

-- 5. Bad metadata（关键字段缺失）
SELECT count(*) AS bad
FROM documents
WHERE metadata->>'collection_mode' IS NULL
   OR metadata->>'platform' IS NULL
   OR metadata->>'rights_note' IS NULL;

-- 6. Bad chunks（缺 chapter 关联的 pdf_mineru chunks）
SELECT count(*) AS bad
FROM chunks
WHERE metadata->>'source_type'='pdf_mineru'
  AND (metadata->>'asset_id' IS NULL OR metadata->>'chapter' IS NULL);
```

**期望**：孤儿计数 = 0；bad metadata = 0；`chunks_per_doc` 教材类 ≥ 40，视频类 ≥ 1.0，scrapling 类 ≥ 30。

### 4. Storage_objects 清理

`storage_objects.object_key` 指向物理文件。孤儿检查：

```sql
-- storage_objects 存在但对应 document_assets 已删
SELECT count(*) FROM storage_objects so
WHERE NOT EXISTS (
  SELECT 1 FROM document_assets da WHERE da.object_key = so.object_key
);
```

对孤儿 storage_objects：

- 如果 `object_key` 指向 `mineru_ingested/`：**可删物理文件**（重跑 batch 会重建）
- 如果指向 `mineru/`：**不删物理文件**（那是源素材），只删 db 记录

---

## 周期性维护清单

### 每次交付 / PR 前（5 分钟）

- [ ] `git ls-files "data/raw/pdf/*.pdf"` 输出为空
- [ ] `git ls-files "data/raw/mediacrawler/**/*.jsonl"` 输出为空
- [ ] `git ls-files "data/processed/mineru/**/manifest.json"` 输出为空
- [ ] `pytest -m "not llm_live" -q` 全绿
- [ ] `.\scripts\demo_smoke.ps1` 7/7 PASS
- [ ] 上面 §3 六段 SQL 校验都符合预期

### 每周（半小时）

- [ ] `du -sh data/` 磁盘占用是否合理（当前基线约 400 MB，含教材 200 MB）
- [ ] `mineru_ingested/` 是否堆积未清理产物
- [ ] `.codegraph/` 是否有 `codegraph.db` 快速膨胀（>500 MB 时应重建索引）
- [ ] 检查 `Workout/session_log.md` 是否有未处理的 `@tag` 关注项

### 每月 / 每交付前（1 小时）

- [ ] 备份 `data/raw/pdf/` 到外部存储（U 盘 / 云盘）—— 大 PDF 一旦丢失只能重下载
- [ ] 备份 postgres db（`pg_dump` 到外部）—— 教材 chunks 若丢失需重跑 batch
- [ ] Review `data/reports/` 里的审计报告，识别未处理项
- [ ] 检查 `.gitignore` 里的规则是否与新增数据源一致（新加平台时不要漏加）

---

## 教材版本更新流程（未来换新版）

如需把《汇编语言 第 3 版》换成第 4 版：

```
1. 新 PDF → data/raw/pdf/汇编语言(第4版).pdf
2. 重跑 MinerU → data/processed/mineru/汇编语言(第4版)/
3. Db 清理旧版：
   DELETE FROM chunks WHERE metadata->>'book_title'='汇编语言（第3版）';
   DELETE FROM document_assets WHERE document_id IN (
     SELECT id FROM documents WHERE title='汇编语言（第3版）'
   );
   DELETE FROM documents WHERE title='汇编语言（第3版）';
4. 物理清理：
   Remove-Item -Recurse -Force data/storage/course_websec/mineru_ingested/reverse-engineering/*
5. 覆盖工程输入（新版 PDF + full.md + assets 替换 mineru/reverse-engineering/ 里的旧文件）
6. 更新 batch 脚本 $titleMap（如果书名变了）
7. 重跑 batch：.\scripts\ingest\ingest_pdf_mineru_batch.ps1 -Textbooks @("reverse-engineering")
8. 更新 data/course_websec/source_manifest.json（版本 + 日期）
9. 更新 docs/demo/textbook-rights-policy.md 补新版说明
10. 加一节 Workout/session_log.md 记录换版原因 + 数据规模变化
```

**❌ 不允许**：在不清 db 的情况下直接换 PDF（content_hash 变 → 双版本共存 → RAG 检索混乱）。

---

## Slug 命名规范（避免命名歧义）

**教材 slug** 必须满足：
- 全部小写 kebab-case（如 `crypto-basics`）
- 与教材主题对齐，不含版本号（版本变化时不改 slug，避免 db 记录迁移）
- 与 batch 脚本 `$Textbooks` 数组、`$titleMap` key 一致
- 与 `data/storage/course_websec/mineru/<slug>/` 目录名一致

**PDF 命名映射**：
- `data/raw/pdf/<原始中文名>.pdf` — 人类可读，原始命名
- `data/storage/course_websec/mineru/<slug>/<slug>.pdf` — 工程规范
- 映射关系维护在 `scripts/ingest/ingest_pdf_mineru_batch.ps1` 的 `$titleMap` 里

**Domain slug**（PostgreSQL `domain` 字段值）：
- `course_websec` — Web 安全课程（当前主 domain）
- `policy` — 政策法规
- `fund` — 基金 / 论文
- `job` — 招聘 / 岗位
- `competition` — 竞赛 / CTF
- `paper` — 论文 / 研究
- `news` — 时事 / CVE 公告

**平台 slug**（`documents.metadata.platform` 枚举，见 `docs/api/evidence-contract.md`）：
- 已锁定枚举：`owasp / portswigger / github / bili / zhihu / xhs / mineru / manual / cve / ctftime / wechat_mp / csdn / mindspider_reference`
- 新增前必须在 evidence-contract v1.x 里登记

---

## 数据健康检查三档

**30 秒快查**（本地 shell）：

```bash
git ls-files "data/raw/pdf/*.pdf" "data/raw/mediacrawler/**/*.jsonl" | wc -l  # 期望 0
du -sh data/                                                                    # 期望 ~400 MB
ls data/storage/course_websec/mineru/*/full.md | wc -l                          # 期望 5（4 教材 + upload seed）
```

**5 分钟核对**（跑测试 + smoke）：

```powershell
cd backend
uv run pytest -m "not llm_live" -q
cd ..
.\scripts\demo_smoke.ps1 -BackendUrl http://127.0.0.1:8001 -NoStartBackend
```

**完整验收**（跑 §3 六段 SQL + 交付报告结构）：

参考 `Workout/session_log.md` 里 6-C-2 §6、6-C-3 §4 的验收命令模板，作为 gold standard。

---

## 备份与灾备策略

| 内容 | 大小 | 备份方式 | 恢复途径 |
|---|---|---|---|
| `data/raw/pdf/*.pdf` | 202 MB | **必须**外部备份（U 盘 / 云盘），源素材丢失不可逆 | 重新下载（若在线仍可获取） |
| `data/processed/mineru/**/` | 39 MB | 建议外部备份 | 重跑 MinerU（成本 ~30 min/本） |
| `data/storage/course_websec/mineru/**/` | 200+ MB | 从 raw + processed 重建 | 跑 6-C-2-cleanup PowerShell 迁移脚本 |
| `data/storage/course_websec/mineru_ingested/**/` | 20+ MB | **不用备份** | 跑 batch 从 mineru/ 重建 |
| PostgreSQL `documents / chunks / document_assets / storage_objects` | ~30 MB | 建议 `pg_dump` 到外部 | 从 mineru/ 重跑 batch 全量恢复 |
| `data/raw/mediacrawler/**/*.jsonl` | 小 | 建议外部备份 | 无法自动重建（依赖 MediaCrawler 再跑） |

---

## A / B / C 三人数据边界（沿用 Plan §6）

| 边界 | 谁能改 | 谁能读 | 反模式 |
|---|---|---|---|
| `data/raw/**` | C 主责，项目负责人可放素材 | 所有人 | A/B 直接从 raw 读取（应从 storage/ 读） |
| `data/processed/**` | C 主责 | 所有人 | 脚本自动写入（应由 MinerU 手动放） |
| `data/storage/course_websec/mineru/**` | C 主责 | ingestion 脚本、A 的 Harness（间接经 db） | 入库脚本直接写这里（应写 mineru_ingested/） |
| `data/storage/course_websec/mineru_ingested/**` | C 主责的脚本自动写 | RAG 检索、Harness（间接经 db） | 手工放文件（应通过 batch 生成） |
| `data/course_websec/source_manifest.json` | C 主责，需同步更新 | 所有人 | 各人各写不同来源（应集中维护） |
| `data/reports/**` | 谁产出谁放 | 相关方 | 提交敏感审计到公开 git |

---

## 未来数据源扩展路线

按 `Plan/C角色爬虫与数据入库推进计划.md` §5-8：

| 阶段 | 内容 | 需新增目录 |
|---|---|---|
| 6-C-4 | Web 安全 10 主题手工补齐 | 无（复用 `data/raw/pdf/` + `data/processed/mineru/`） |
| 6-C-5 | BGE-M3 embedding 真跑 | 无（用现有 chunks） + 可能加 `data/models/bge-m3/` 存本地模型 |
| P2 | MindSpider 舆情参考 | `data/raw/mindspider/` |
| P2 | 政策 domain | `data/raw/pdf/policy/` + `data/storage/policy/` |
| P2 | 基金 / 招聘 domain | `data/raw/pdf/fund/` + `data/storage/fund/` 等 |

**扩展时必须做的**：
1. 加对应 `.gitignore` 规则（版权 + PII 保护）
2. 更新本 README 目录约定表
3. 更新 `docs/api/evidence-contract.md` 的 `platform` / `collection_mode` / `domain` 枚举
4. 更新 `data/course_websec/source_manifest.json` 追加条目
5. 更新 `docs/demo/source-rights-note.md` 补合规说明

---

## 关联文档

| 文档 | 用途 |
|---|---|
| `data/storage/course_websec/mineru_ingested/README.md` | 产物目录用途说明 |
| `docs/api/evidence-contract.md` v1.1 | 字段真理源、枚举锁定 |
| `docs/demo/textbook-rights-policy.md` | 教材版权与引用边界 |
| `docs/demo/source-rights-note.md` | 各来源合规说明 |
| `docs/demo/websec_source_inventory.md` | 来源清单 + 状态跟踪 |
| `Plan/C角色爬虫与数据入库推进计划.md` | 6-C-1 到 6-C-5 阶段规划 |
| `Plan/SecureHub_三人工程化分工与真实LLM接入规划.md` | §6 C 边界定义 |
| `Prompt/6-C-2.md` §5 | 教材版权合规 SOP |
| `.codex/AGENTS.md` §3.3 / §3.9 / §10.5 / §10.6 | 铁律：统一知识资产层、采集合规、MinerU 三条路线 |
| `Workout/session_log.md` | 每轮交付验收命令 + 数据规模变化 |

---

## 变更记录

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-07-07 | v1 | 首次建立（6-C-2-cleanup），三层分离原则 |
| 2026-07-08 | v1.1 | 追加：db 治理 SQL、周期性维护清单、教材换版流程、slug 命名规范、备份策略、A/B/C 边界表、扩展路线 |
| 2026-07-08 | v1.2 | 追加：数据库服务运行（本地 Docker / Neon / 阿里云）、多设备/多成员同步矩阵、4 类场景 runbook（新设备 / 日常增量 / 灾难恢复 / 云 db 共享）、云盘工具与目录约定 |

---

**维护者**：成员 C
**首次建立**：2026-07-07（6-C-2-cleanup）
**规范化状态**：v1.2，待 A / B / 项目负责人 review

