# 成员 C P0 交接说明

Status: real

更新时间：2026-06-12  
工作目录：`F:\software_cup\SecureHub-Full-Stack-Monorepo`  
分支：`dev`  
角色：成员 C，负责知识库 / 多源采集 / PDF 转换 / 质量集成。

## 1. 本次完成了什么

本次完成的是成员 C 的 P0 数据与质量集成底座。

简单说：把 Web 安全课程知识库从“只有骨架和占位文本”，补成了一个可以导入资料、登记资产、切分 chunks、做 RAG smoke、做无证据防幻觉测试，并且能在 Docker backend 容器里通过验收的版本。

## 2. 关键成果

### 2.1 课程资料入库链路

实现位置：

```text
backend/app/knowledge/loaders/course_loader.py
backend/app/services/knowledge/ingestion_service.py
backend/app/services/knowledge/chunking_service.py
backend/app/services/storage/storage_service.py
```

已实现三条 P0 入库路径：

```text
manual_import
markdown_import
pdf_mineru_import
```

说明：

- `manual_import`：用于手工整理的课程资料入库。
- `markdown_import`：用于 Markdown 文件入库，同时登记 `markdown_full` 资产。
- `pdf_mineru_import`：用于 PDF / MinerU 输出入库。
- 如果找不到 MinerU 转出的 Markdown，会生成一个兜底 Markdown，确保原始 PDF 先进入资产链路。

所有资料统一进入：

```text
documents
document_assets
chunks
storage_objects
```

没有新增 `course_chunks`、`bilibili_chunks`、`zhihu_chunks` 等平台或 domain 专用表。

### 2.2 本地对象存储服务

实现位置：

```text
backend/app/services/storage/storage_service.py
```

P0 支持：

- `provider=local`
- 写入本地对象内容
- 生成并登记 `content_hash`
- 写入 / 更新 `storage_objects`
- 通过 `object_key` 获取本地对象

非 local 的 MinIO / S3 / OSS / COS / R2 仍属于 P1/P2，不在本次范围内。

### 2.3 Web 安全课程 seed 数据升级

实现位置：

```text
backend/app/db/seeds/seed_course_websec.py
```

原来 chunks 是占位文本，现在替换为真实教学切片。

覆盖的核心知识点包括：

```text
SQL 注入
XSS
CSRF
文件上传
SSRF
认证与会话安全
访问控制
命令执行 / RCE
OWASP Top 10
```

当前 seed 规模：

```text
1 门课程
15 个 knowledge_nodes
30 条 knowledge_edges
15 个 documents
15 个 markdown_full document_assets
15 个 storage_objects
60 个 chunks
```

每条资料和 chunk 都补齐了来源字段：

```text
platform
source_url
author
published_at
fetched_at
license
rights_note
asset_type
```

这样后续前端 EvidenceDrawer / CitationPanel 能展示来源证据。

### 2.4 RAG 检索与证据卡片

实现位置：

```text
backend/app/services/knowledge/retrieval_service.py
backend/app/services/knowledge/evidence_service.py
```

P0 检索能力：

- 必须传入 `domain`
- 支持 `domain=course_websec`
- 支持关键词召回 chunks
- 支持简单 metadata filter，例如 `platform=portswigger`
- 返回 source_url、platform、author、rights_note、asset_type、reliability 等证据字段

注意：

当前是 P0 轻量检索，不是最终的 BM25 + pgvector + RRF + rerank 完整链路。后续成员 A 可以在同一个 `RetrievalService.retrieve()` 入口替换为正式混合检索。

### 2.5 无证据防幻觉测试

实现位置：

```text
backend/tests/hallucination/test_no_evidence_queries.py
```

测试目标：

- 当 RAG 找不到足够证据时，直接抛出 `InsufficientEvidence`
- 不进入 LLM 生成步骤
- 避免裸调 LLM

### 2.6 generated_resources / user_capabilities 测试

新增测试：

```text
backend/tests/resource/test_generated_resources.py
backend/tests/identity/test_user_capabilities.py
```

覆盖内容：

- `generated_resources` 可以保存 `object_key`
- `generated_resources` 可以保存非空 evidence 引用
- `user_capabilities` 可以幂等更新能力分数
- 支撑后续 Profile 雷达图和学习评估回流

### 2.7 PDF / MinerU 导入脚本

新增脚本：

```text
scripts/ingest_pdf_mineru.py
```

示例：

```bash
cd backend
uv run python ../scripts/ingest_pdf_mineru.py ../data/raw/pdf/demo.pdf \
  --mineru-output ../data/processed/mineru/demo \
  --title "SQL 注入教材节选"
```

脚本会调用 `pdf_mineru_import`，输出：

```text
documents
chunks
assets
domain
```

### 2.8 Demo smoke 脚本

新增脚本：

```text
scripts/demo_smoke.ps1
```

它会跑成员 C 的 P0 测试集合：

```text
tests/rag
tests/hallucination
tests/knowledge
tests/resource
tests/identity
tests/db/test_seed_smoke.py
```

说明：

宿主机 PowerShell 环境如果没有 `uv/pytest`，脚本会失败；Docker backend 容器里已验证通过。

### 2.9 演示与资料文档

新增文档 / 数据：

```text
docs/demo/websec_source_inventory.md
docs/demo/seven-minute-demo-checklist.md
data/course_websec/source_manifest.json
Workout/session_log.md
```

用途：

- `websec_source_inventory.md`：Web 安全课程资料来源清单。
- `seven-minute-demo-checklist.md`：7 分钟演示 checklist。
- `source_manifest.json`：机器可读的来源字段规范。
- `session_log.md`：成员 C 本次工作日志。

## 3. 新增 / 修改的主要文件

### 新增文件

```text
backend/tests/identity/test_user_capabilities.py
backend/tests/knowledge/test_course_loaders.py
backend/tests/resource/test_generated_resources.py
data/course_websec/source_manifest.json
docs/demo/seven-minute-demo-checklist.md
docs/demo/websec_source_inventory.md
scripts/demo_smoke.ps1
scripts/ingest_pdf_mineru.py
Workout/member_c_p0_handoff.md
```

### 主要修改文件

```text
backend/app/db/seeds/seed_course_websec.py
backend/app/knowledge/loaders/course_loader.py
backend/app/services/knowledge/chunking_service.py
backend/app/services/knowledge/evidence_service.py
backend/app/services/knowledge/ingestion_service.py
backend/app/services/knowledge/retrieval_service.py
backend/app/services/storage/storage_service.py
backend/tests/conftest.py
backend/tests/hallucination/test_no_evidence_queries.py
backend/tests/rag/test_retrieve_course_websec.py
scripts/seed_course_websec.sh
Workout/session_log.md
```

注意：

工作树中还有此前已经存在的修改：

```text
docker-compose.yml
frontend/package.json
frontend/package-lock.json
```

这些不是本次成员 C 工作主动修改的内容，不要在后续会话里误当作本次交付的一部分回滚。

## 4. Docker 验收结果

本次最终在 Docker backend 容器内完成验证。

### 4.1 服务状态

命令：

```bash
docker compose ps
```

结果摘要：

```text
backend   Up
frontend  Up
postgres  Up / healthy
redis     Up / healthy
```

### 4.2 容器环境

命令：

```bash
docker compose exec -T backend sh -lc "pwd && command -v uv && uv --version && python --version"
```

结果摘要：

```text
/app/backend
/usr/local/bin/uv
uv 0.11.20
Python 3.12.13
```

### 4.3 Alembic 迁移

命令：

```bash
docker compose exec -T backend sh -lc "uv run alembic upgrade head"
```

结果：通过。

### 4.4 成员 C P0 smoke 子集

命令：

```bash
docker compose exec -T backend sh -lc "uv run pytest tests/rag tests/hallucination tests/knowledge tests/resource tests/identity tests/db/test_seed_smoke.py"
```

结果：

```text
9 passed, 1 warning
```

### 4.5 后端全量测试

命令：

```bash
docker compose exec -T backend sh -lc "uv run pytest"
```

结果：

```text
35 items collected
25 passed
10 skipped
1 warning
```

warning 来自 passlib / Python 3.13 的 `crypt` deprecation，不是本次代码错误。

## 5. 铁律自检

本次工作遵守以下约束：

- 没有新增第 10 个 agent。
- 没有新增 crawler agent / media agent / mineru agent。
- 没有新增 `bilibili_chunks`、`zhihu_chunks`、`course_chunks` 等平台或 domain 专用表。
- 采集内容进入 `documents / document_assets / chunks`。
- 文件资产通过 `storage_objects.object_key` 管理。
- 来源字段保留 `platform / source_url / author / published_at / fetched_at / rights_note`。
- 无证据测试确认不会进入生成步骤。
- MediaCrawler / MindSpider 仍保持 P1/P2 受控适配或参考定位，没有进入 P0 主链路。

## 6. 仍需后续成员配合

### 成员 A

需要把后端生成链路接到本次完成的底座：

```text
RetrievalService.retrieve()
EvidenceService.build()
generated_resources
agent_runs
resource generation SSE
```

尤其是课程资源生成接口：

```text
POST /api/v1/courses/{cid}/resources/generate
```

需要确保：

- 第一个 token 前先发 evidence。
- evidence 不足时返回 `InsufficientEvidence`。
- 生成物写 `generated_resources`。
- 大文件写 `storage_objects`。
- agent trace 写 `agent_runs`。

### 成员 B

需要在前端展示本次补齐的证据字段：

```text
platform
source_url
author
published_at
fetched_at
rights_note
asset_type
```

并接入：

```text
user_capabilities
EvidenceDrawer
CitationPanel
AgentTracePanel
```

### 成员 C 后续 P1

下一步可以继续做：

```text
scrapling_client.py
crawler_policy.py
source_normalizer.py
generic_web_loader.py
github_docs_loader.py
owasp_loader.py
portswigger_loader.py
mediacrawler_export_import.py
media_source_normalizer.py
test_scrapling_public_loader.py
test_mediacrawler_normalizer.py
```

## 7. 给新对话 Codex 的快速提示

如果新开启一个对话，可以先让 Codex 读：

```text
CLAUDE.md
.codex/AGENTS.md
docs/api/course-contract.md
Workout/member_c_p0_handoff.md
docs/demo/websec_source_inventory.md
docs/demo/seven-minute-demo-checklist.md
```

然后用 Docker 复验：

```bash
cd F:\software_cup\SecureHub-Full-Stack-Monorepo
docker compose exec -T backend sh -lc "uv run alembic upgrade head"
docker compose exec -T backend sh -lc "uv run pytest"
```

当前已知通过结果：

```text
25 passed, 10 skipped, 1 warning
```
