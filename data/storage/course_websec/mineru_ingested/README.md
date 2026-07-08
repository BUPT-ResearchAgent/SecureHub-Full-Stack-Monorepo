# mineru_ingested/ — MinerU 入库产物目录

> 6-C-2 事故后创建的**工程产物**目录。脚本运行时会把入库产物写入这里，
> 与 `../mineru/`（工程**输入**目录）**严格分离**，防止入库时污染源文件。

## 内容约定

```
mineru_ingested/
├── README.md                    ← 本文件（git tracked）
├── <slug>/                      ← 每本教材一个子目录
│   ├── chapters/                ← markdown_chapter asset 副本（.gitignore 排除）
│   │   ├── 0000_第1章_XXX.md
│   │   ├── 0001_第2章_XXX.md
│   │   └── ...
│   ├── full.md                  ← markdown_full asset 副本（.gitignore 排除）
│   └── assets/                  ← page_image 副本（.gitignore 排除）
│       └── image_XXXX_hash.jpg
```

## 与 mineru/ 的差异

| 维度 | `mineru/<slug>/` | `mineru_ingested/<slug>/` |
|---|---|---|
| 角色 | 工程**输入**（脚本只读） | 工程**产物**（脚本读写） |
| 内容 | 用户手工放置的真教材（PDF + full.md + 原始 assets） | `pdf_mineru_import` 生成的 chapter markdown / assets 副本 |
| 幂等 | 内容变化（换教材版本）时 hash 变，重新入库 | 每次跑 batch 都会重建 |
| git | 保留目录树 + full.md（本仓库策略） | 全部 `.gitignore` 排除（可从 db + mineru/ 完全重建） |
| 事故 | 6-C-2 前曾被产物覆盖过（35/38/41 字节 stub） | 事故后新建，防护函数 `_ensure_storage_target_outside_inputs` 强制隔离 |

## 何时该有内容

- **首次跑 batch 后**：`.\scripts\ingest\ingest_pdf_mineru_batch.ps1` 会在这里落产物
- **重跑 batch（`-ForceReingest`）**：产物覆盖式重建
- **db 里 `document_assets(asset_type='markdown_chapter')` 数** 与本目录 `<slug>/chapters/*.md` 数应保持一致

## 清理时机

- 更换教材版本前：`Remove-Item -Recurse -Force <slug>/chapters/`（配合 db SQL 清理）
- 事故恢复：可以全清空，重跑 batch 会重建（源在 `../mineru/<slug>/`，不会被污染）
