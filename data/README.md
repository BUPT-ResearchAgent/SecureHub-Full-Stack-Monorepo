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

**维护者**：成员 C
**首次建立**：2026-07-07（6-C-2-cleanup）
**规范化状态**：draft-by-C，待 B/A review
