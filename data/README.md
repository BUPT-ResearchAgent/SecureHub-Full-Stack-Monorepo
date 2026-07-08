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

---

**维护者**：成员 C
**首次建立**：2026-07-07（6-C-2-cleanup）
**规范化状态**：v1.1，待 A / B / 项目负责人 review

