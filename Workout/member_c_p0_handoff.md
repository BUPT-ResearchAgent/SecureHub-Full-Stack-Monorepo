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

## 8. 2026-06-13 P1 多源采集补充交接

本节记录成员 C 在 P0 之后继续完成的 P1 多源采集工作，方便新对话 Codex 直接接续。

### 8.1 本次继续完成了什么

本次完成的是 P1 的公开网页采集与 MediaCrawler 离线导入适配。

通俗地说：现在系统不只支持手工 Markdown / PDF 入库，也具备了两类可控资料来源：

```text
1. Scrapling / 普通公开网页：
   OWASP、PortSwigger、GitHub README / Docs、公开技术博客等。

2. MediaCrawler 离线导出：
   B站、知乎、小红书等中文社媒平台的小规模 JSON / JSONL / CSV 导出。
```

这些内容不会变成新 agent，也不会新建平台专用表。它们统一走：

```text
外部资料
  -> 合规检查 / 字段归一化
  -> storage_objects 保存原始资产
  -> documents 记录来源文档
  -> document_assets 记录 HTML / JSON / 评论等源资料资产
  -> chunks 切片
  -> RAG 检索
```

### 8.2 Scrapling / 公开网页采集链路

新增实现位置：

```text
backend/app/services/knowledge/crawling/crawler_policy.py
backend/app/services/knowledge/crawling/scrapling_client.py
backend/app/services/knowledge/crawling/source_normalizer.py
backend/app/knowledge/loaders/generic_web_loader.py
backend/app/knowledge/loaders/github_docs_loader.py
backend/app/knowledge/loaders/owasp_loader.py
backend/app/knowledge/loaders/portswigger_loader.py
backend/tests/knowledge/test_scrapling_public_loader.py
```

#### crawler_policy.py

作用：公开采集的合规门卫。

允许：

```text
公开 HTTP / HTTPS 页面
demo 级别小批量采集
robots-aware / throttle 友好采集策略
普通 CSS / XPath / 文本抽取
```

禁止并会在测试中拦截：

```text
solve_cloudflare
captcha / turnstile 绕过
proxy / proxy_rotation
login / session_cookie / password
stealth / anti_bot / bypass
```

#### scrapling_client.py

作用：Scrapling 的安全封装。

说明：

- 优先尝试使用 Scrapling 的普通 `Fetcher` / `DynamicFetcher`。
- 如果环境里没有安装 Scrapling，则降级为 `httpx` 拉取普通公开网页。
- 不使用 StealthyFetcher、不做 Cloudflare 绕过、不做代理轮换。
- 能从 HTML 中抽取标题和正文，供后续 normalizer 使用。

#### source_normalizer.py

作用：把公开网页统一整理成 SecureHub 需要的来源结构。

会补齐：

```text
platform
source_url
author
published_at
fetched_at
license
rights_note
asset_type
reliability / trust_score
```

#### 四个 loader

```text
generic_web_loader.py      通用公开网页 loader
github_docs_loader.py      GitHub README / Docs loader
owasp_loader.py            OWASP Web 安全资料 loader
portswigger_loader.py      PortSwigger Web Security Academy loader
```

这些 loader 最终都复用：

```text
IngestionService
StorageService
ChunkingService
```

所以它们不会绕过 P0 已有的统一入库链路。

#### test_scrapling_public_loader.py

测试内容：

```text
1. 使用离线 HTML 模拟 OWASP SQL Injection 页面。
2. 验证网页正文能抽取。
3. 验证 raw_html 写入 document_assets。
4. 验证 storage_objects 通过 object_key 管理 HTML 资产。
5. 验证 chunks 可被 RetrievalService 按 platform=owasp 检索。
6. 验证 crawler_policy 会拦截 solve_cloudflare / proxy 等违规参数。
```

### 8.3 MediaCrawler 离线导入链路

新增实现位置：

```text
backend/app/services/knowledge/crawling/media_source_normalizer.py
backend/app/services/knowledge/crawling/mediacrawler_export_import.py
scripts/crawl/mediacrawler_export_import.py
backend/tests/knowledge/test_mediacrawler_normalizer.py
docs/demo/mediacrawler-export-structure.md
```

#### MediaCrawler 输出结构调研

调研记录写入：

```text
docs/demo/mediacrawler-export-structure.md
```

调研结论：

MediaCrawler 公开项目通常把导出数据分为：

```text
contents
comments
creators
```

并支持多种保存格式。SecureHub 目前只消费离线：

```text
JSON
JSONL
CSV
```

不复用 MediaCrawler 自带的平台专用 DB schema。

当前支持的平台字段映射：

```text
小红书 xhs:
  note_id / title / desc / note_url / nickname / time

B站 bili:
  video_id / title / desc / video_url / nickname / create_time

知乎 zhihu:
  content_id / title / content_text / content_url / user_nickname / created_time
```

#### media_source_normalizer.py

作用：把 B站、知乎、小红书不同字段统一成 SecureHub 标准字段。

例如：

```text
note_url / video_url / content_url
  -> source_url

nickname / user_nickname
  -> author

note_id / video_id / content_id
  -> media_id
```

它还会把正文、互动指标、采样评论整理成适合 RAG 的 Markdown-like 文本。

已支持：

```text
xhs
bili / bilibili
zhihu
```

#### mediacrawler_export_import.py

作用：把 MediaCrawler 离线导出的 JSON / JSONL / CSV 导入 SecureHub。

导入规则：

```text
内容项:
  -> documents
  -> chunks
  -> document_assets.asset_type = media_item_json

评论项:
  -> document_assets.asset_type = media_comment_json

原始 JSON:
  -> storage_objects
```

它会按平台 ID 自动把评论挂到对应内容上：

```text
xhs   使用 note_id
bili  使用 video_id
zhihu 使用 content_id
```

#### scripts/crawl/mediacrawler_export_import.py

命令行用法：

```bash
cd backend
uv run python ../scripts/crawl/mediacrawler_export_import.py \
  ../data/raw/mediacrawler/bili \
  --platform bili \
  --domain course_websec
```

输出会显示：

```text
documents
chunks
assets
contents
comments
domain
```

#### test_mediacrawler_normalizer.py

测试内容：

```text
1. 小红书样例内容能被归一化。
2. B站 contents.jsonl + comments.jsonl 能被离线导入。
3. 内容写入 documents。
4. 原始内容写入 document_assets: media_item_json。
5. 评论写入 document_assets: media_comment_json。
6. chunks 可被 RetrievalService 按 platform=bili 检索。
```

### 8.4 本次 P1 已完成清单

当前 P1 中这些项已经完成：

```text
1. scrapling_client.py
2. crawler_policy.py
3. source_normalizer.py
4. generic_web_loader.py / github_docs_loader.py / owasp_loader.py / portswigger_loader.py
5. 调研 MediaCrawler 输出结构
6. mediacrawler_export_import.py
7. media_source_normalizer.py
8. 先支持 bili / zhihu / xhs 三个平台输出映射
9. test_scrapling_public_loader.py
10. test_mediacrawler_normalizer.py
```

### 8.5 验证结果

本地宿主机 PowerShell 没有可用 `uv / pytest`，因此使用 Docker backend 容器验证。

新增 Scrapling 测试：

```bash
docker compose run --rm --no-deps backend sh -lc "pip install uv >/dev/null && uv sync >/dev/null && uv run pytest tests/knowledge/test_scrapling_public_loader.py -q"
```

结果：

```text
3 passed, 1 warning
```

新增 MediaCrawler 测试：

```bash
docker compose run --rm --no-deps backend sh -lc "pip install uv >/dev/null && uv sync >/dev/null && uv run pytest tests/knowledge/test_mediacrawler_normalizer.py -q"
```

结果：

```text
2 passed, 1 warning
```

knowledge 测试集合：

```bash
docker compose run --rm --no-deps backend sh -lc "pip install uv >/dev/null && uv sync >/dev/null && uv run pytest tests/knowledge -q"
```

结果：

```text
7 passed, 1 warning
```

后端全量测试：

```bash
docker compose run --rm --no-deps backend sh -lc "pip install uv >/dev/null && uv sync >/dev/null && uv run pytest -q"
```

结果：

```text
30 passed, 10 skipped, 1 warning
```

warning 仍是 passlib / Python `crypt` deprecation，不是本次功能错误。

### 8.6 铁律自检

本次 P1 工作仍然遵守：

```text
没有新增 crawler_agent / media_agent / spider_agent。
没有新增 bili_chunks / zhihu_chunks / xhs_chunks 等平台专用表。
Scrapling / MediaCrawler 都只是横切采集能力。
MediaCrawler 只消费离线导出，不复用外部平台表结构。
所有采集内容统一进入 documents / document_assets / chunks。
所有原始 HTML / JSON / 评论资产通过 storage_objects.object_key 管理。
所有来源保留 platform / source_url / author / published_at / fetched_at / rights_note。
没有实现登录绕过、验证码绕过、Cloudflare 绕过、代理轮换、大规模采集。
```

### 8.7 给新对话 Codex 的快速提示补充

新对话如果继续成员 C P1 / P2，请先读：

```text
CLAUDE.md
.codex/AGENTS.md
docs/api/course-contract.md
Workout/member_c_p0_handoff.md
docs/demo/mediacrawler-export-structure.md
backend/app/services/knowledge/crawling/
backend/app/knowledge/loaders/
backend/tests/knowledge/
```

优先复验：

```bash
cd F:\software_cup\SecureHub-Full-Stack-Monorepo
docker compose run --rm --no-deps backend sh -lc "pip install uv >/dev/null && uv sync >/dev/null && uv run pytest tests/knowledge -q"
```

当前已知通过结果：

```text
7 passed, 1 warning
```

后续可以继续做：

```text
1. 扩展 MediaCrawler 的 douyin / weibo / tieba / kuaishou 映射。
2. 实现 mindspider_export_import.py 轻量适配。
3. 为 hot_analyst 准备舆情 demo 数据。
4. 补充 fund / policy / job / competition domain seed。
5. 完善演示脚本与素材清单。
```

## 9. 2026-06-13 真实公开网页导入补充交接

本节记录一次后续对话中新增的正式网页导入脚本，以及已经写入 Docker PostgreSQL 的真实 Web 安全公开资料。

### 9.1 新增正式 Scrapling public import 脚本

新增脚本：

```text
scripts/crawl/scrapling_public_import.py
```

用途：

```text
把公开网页资料导入 SecureHub data-layer v2：
公开网页 -> generic_web_loader -> storage_objects -> documents -> document_assets -> chunks
```

支持三种导入方式：

```bash
# 1. 导入内置 Web 安全核心资料
cd backend
uv run python ../scripts/crawl/scrapling_public_import.py --preset websec-core

# 2. 导入单个网页
uv run python ../scripts/crawl/scrapling_public_import.py \
  --url https://portswigger.net/web-security/sql-injection \
  --platform portswigger \
  --title "PortSwigger SQL injection"

# 3. 从 JSON / JSONL / CSV URL 清单批量导入
uv run python ../scripts/crawl/scrapling_public_import.py \
  --source-file ../data/raw/websec_sources.jsonl
```

source-file 行字段可包含：

```text
url
title
platform
author
published_at
license
rights_note
source_type
reliability
```

脚本特点：

```text
1. 逐个 URL 导入，单个页面失败不会中断整个批次。
2. 每个页面独立 commit / rollback。
3. 最后打印 imported / failed 汇总。
4. 使用已有 generic_web_import，不绕过 crawler_policy / source_normalizer / IngestionService / StorageService。
5. 不实现登录绕过、验证码绕过、Cloudflare 绕过、代理轮换或大规模采集。
```

### 9.2 已导入的真实 Web 安全资料

已经在 Docker compose 的 PostgreSQL 中执行过真实导入：

```text
数据库：postgresql://securehub:securehub@postgres:5432/securehub
宿主机端口：15432
domain：course_websec
```

由于 `docker-compose.yml` 的 backend 服务只挂载了 `backend/`，运行脚本时额外挂载了 `scripts/`：

```bash
cd F:\software_cup\SecureHub-Full-Stack-Monorepo

docker compose run --rm --volume ./scripts:/app/scripts backend sh -lc \
  "pip install uv >/dev/null && uv sync >/dev/null && \
   uv run python /app/scripts/crawl/scrapling_public_import.py --preset websec-core"
```

导入结果：

```text
imported=10
failed=0
domain=course_websec
```

成功导入的真实公开网页：

```text
OWASP:
1. https://owasp.org/www-community/attacks/SQL_Injection
2. https://owasp.org/www-community/attacks/xss/
3. https://owasp.org/www-community/attacks/csrf
4. https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload

PortSwigger Web Security Academy:
5. https://portswigger.net/web-security/sql-injection
6. https://portswigger.net/web-security/cross-site-scripting
7. https://portswigger.net/web-security/csrf
8. https://portswigger.net/web-security/file-upload
9. https://portswigger.net/web-security/ssrf
10. https://portswigger.net/web-security/access-control
```

### 9.3 当前数据库中的新增真实数据规模

导入后通过 PostgreSQL 查询确认：

```text
documents:
owasp       4
portswigger 6

chunks:
owasp       218
portswigger 228

document_assets:
raw_html    10

storage_objects:
local       10
```

也就是说，本次真实公开网页导入新增：

```text
10 个 documents
10 个 raw_html document_assets
10 个 local storage_objects
446 个真实网页 chunks
```

这些数据全部进入统一表：

```text
documents
document_assets
storage_objects
chunks
```

没有新增：

```text
owasp_chunks
portswigger_chunks
web_chunks
```

### 9.4 已验证的查询结果

执行过数据库查询，确认 SQL 注入相关真实网页 chunks 已入库，例如：

```sql
SELECT d.title, d.metadata->>'platform' AS platform, d.url, left(c.chunk_text, 160) AS excerpt
FROM chunks c
JOIN documents d ON d.id = c.document_id
WHERE c.domain = 'course_websec'
  AND (c.chunk_text ILIKE '%SQL injection%' OR c.chunk_text ILIKE '%parameterized%')
ORDER BY d.metadata->>'platform', d.title
LIMIT 5;
```

查询结果能返回：

```text
OWASP SQL Injection
platform=owasp
url=https://owasp.org/www-community/attacks/SQL_Injection
```

说明真实网页内容已经写入 chunks，可供后续 RAG / evidence 检索使用。

### 9.5 当前启动后能否看到这些数据

可以，但要区分后端和前端：

```text
1. 后端数据库已经有这些真实网页资料。
2. 后端如果连接 compose PostgreSQL，就能查询这些 documents / chunks。
3. 前端是否直接显示这些来源，取决于 /course / EvidenceDrawer / RAG 搜索接口是否已接真实后端。
4. 如果前端仍使用 mock 数据，页面不会自动出现 OWASP / PortSwigger 列表。
```

启动方式：

```bash
cd F:\software_cup\SecureHub-Full-Stack-Monorepo
docker compose up
```

或只启动后端相关服务：

```bash
docker compose up postgres redis backend
```

### 9.6 后续建议

真实网页导入已经可用，但 OWASP 页面里有少量导航 / 脚本文本混入 chunk，这是公开网页直接抽正文的常见噪声。

后续如果要提升 RAG 质量，可以继续做：

```text
1. 给 generic_web_loader 增加更细的正文抽取规则。
2. 针对 OWASP / PortSwigger 分别设置 css_selector / xpath。
3. 增加 HTML 清洗，去掉 nav / script / footer / sidebar。
4. 给导入脚本增加 --dry-run 和 --limit。
5. 把真实导入结果写入 docs/demo/websec_source_inventory.md。
```

## 10. 2026-06-14 网页正文清洗与重导入结果

本节记录一次针对 OWASP / PortSwigger 公开网页 chunks 噪声的修复。

### 10.1 问题现象

数据库中已经有 `documents / chunks` 数据，但查询 `OWASP SQL Injection` 时，部分 chunk 开头是网页脚本和导航内容，例如：

```text
mlistr += ...
$('#midmenu').html(...)
$(".accordion").click(...)
#banner img
This website uses cookies
```

这说明数据已经入库，但 HTML 正文抽取太宽，把 JS / CSS / nav / banner / cookie 等页面噪声切进了 RAG chunks。

### 10.2 修复内容

修改位置：

```text
backend/app/services/knowledge/crawling/scrapling_client.py
backend/app/knowledge/loaders/owasp_loader.py
backend/app/knowledge/loaders/portswigger_loader.py
scripts/crawl/scrapling_public_import.py
backend/tests/knowledge/test_scrapling_public_loader.py
```

具体做了：

```text
1. 在 ScrapedPage.extract_text() 中先删除 script / style / noscript / template / nav / header / footer / aside / form 等噪声节点。
2. 增加通用正文候选选择逻辑：优先 main / article / #main / #content / .page-content / .post-content / .markdown-body。
3. 增加行级过滤，丢弃明显的 JS / CSS / cookie / banner / navigation 文本。
4. 为 OWASP 增加 OWASP_CONTENT_XPATH。
5. 为 PortSwigger 增加 PORTSWIGGER_CONTENT_XPATH。
6. 同步更新 scripts/crawl/scrapling_public_import.py 的 websec-core 预设，确保命令行重导入也使用新选择器。
7. 增加测试 test_public_loader_strips_page_chrome_before_chunking，防止以后回归。
```

### 10.3 数据库清理与重导入

清理旧脏数据：

```sql
WITH target_docs AS (
  SELECT id
  FROM documents
  WHERE domain='course_websec'
    AND metadata->>'platform' IN ('owasp','portswigger')
    AND source_type IN ('owasp_public','portswigger_public','scrapling_public')
)
DELETE FROM documents
WHERE id IN (SELECT id FROM target_docs);

DELETE FROM storage_objects
WHERE object_key LIKE 'course_websec/owasp/%'
   OR object_key LIKE 'course_websec/portswigger/%'
   OR object_key LIKE 'course_websec/scrapling_public/owasp/%'
   OR object_key LIKE 'course_websec/scrapling_public/portswigger/%';
```

执行结果：

```text
DELETE 10
DELETE 10
```

随后用新清洗逻辑重新导入公开网页资料。当前数据库中已恢复的 public web 文档包括：

```text
owasp       OWASP SQL Injection
owasp       OWASP Unrestricted File Upload
portswigger PortSwigger Access control vulnerabilities
portswigger PortSwigger CSRF
portswigger PortSwigger File upload vulnerabilities
portswigger PortSwigger SQL injection
portswigger PortSwigger SSRF
```

### 10.4 验证结果

重新查询 `OWASP SQL Injection`，chunk 开头已经变成真实正文：

```text
SQL Injection
Contributor(s): kingthorin, zbraiterman
Overview
A SQL injection attack consists of insertion
or “injection” of a SQL query via the input data from the client to the
application...
```

噪声统计：

```sql
SELECT count(*) AS noisy_chunks
FROM chunks c
JOIN documents d ON d.id = c.document_id
WHERE c.domain='course_websec'
  AND d.metadata->>'platform' IN ('owasp','portswigger')
  AND (
    c.chunk_text ILIKE '%mlistr +=%'
    OR c.chunk_text ILIKE '%#banner img%'
    OR c.chunk_text ILIKE '%toggleClass%'
    OR c.chunk_text ILIKE '%This website uses cookies%'
    OR c.chunk_text ILIKE '%mobile primary navigation%'
  );
```

结果：

```text
noisy_chunks = 0
```

测试：

```bash
docker compose exec -T backend sh -lc "uv run pytest tests/knowledge -q"
```

结果：

```text
8 passed, 1 warning
```

后端全量测试：

```bash
docker compose exec -T backend sh -lc "uv run pytest -q"
```

结果：

```text
31 passed, 10 skipped, 1 warning
```

## 11. 2026-06-14 GitHub-friendly public web import script

Goal: teammates should not need committed crawl output data. After pulling the
repo, they can run the importer and fetch the public Web Security sources into
the unified data-layer v2 tables.

### 11.1 Files changed

- Added backend-runnable CLI module:
  `backend/app/knowledge/loaders/scrapling_public_importer.py`
- Kept repo script as a thin host-side wrapper:
  `scripts/crawl/scrapling_public_import.py`
- Added importer tests in:
  `backend/tests/knowledge/test_scrapling_public_loader.py`

### 11.2 Why the old script needed refactor

The previous `scripts/crawl/scrapling_public_import.py` worked from the host
when run as `cd backend && uv run python ../scripts/...`, but the backend
Docker service only mounts the backend app by default. That means a running
backend container cannot reliably see the repo-level `scripts/` directory.

The new structure puts the real CLI in `backend/app/...`, so Docker users can
run it with Python module execution.

### 11.3 Main commands

Host-side run:

```bash
cd backend
uv run python ../scripts/crawl/scrapling_public_import.py --preset websec-core --replace
```

Docker backend-container run:

```bash
docker compose exec backend sh -lc "uv run python -m app.knowledge.loaders.scrapling_public_importer --preset websec-core --replace"
```

Smoke check without network/database writes:

```bash
docker compose exec backend sh -lc "uv run python -m app.knowledge.loaders.scrapling_public_importer --preset websec-core --limit 1 --dry-run"
```

### 11.4 Importer behavior

- `--preset websec-core` includes OWASP and PortSwigger public Web Security
  sources.
- `--source-file` supports JSON, JSONL, and CSV rows.
- Row fields: `url`, `title`, `platform`, `author`, `published_at`, `license`,
  `rights_note`, `source_type`, `asset_type`, `reliability`, `css_selector`,
  `xpath`, `metadata`.
- `--limit N` imports only the first N resolved sources for smoke testing.
- `--dry-run` prints resolved sources and summary without database or network
  writes.
- `--replace` deletes existing `documents`, cascaded `chunks` /
  `document_assets`, and related `storage_objects` for the selected URLs before
  importing. This is important because the current chunker returns existing
  chunks when a document already exists, so cleaning or selector changes require
  replacement.

### 11.5 Validation

Dry-run command passed in the backend Docker container:

```text
[scrapling_public_import] dry-run platform=owasp title=OWASP SQL Injection url=https://owasp.org/www-community/attacks/SQL_Injection
[scrapling_public_import] summary
{
  "domain": "course_websec",
  "requested": 1,
  "deleted_documents": 0,
  "deleted_storage_objects": 0,
  "imported": [],
  "failed": []
}
```

Focused test command:

```bash
docker compose exec -T backend sh -lc "uv run pytest tests/knowledge/test_scrapling_public_loader.py -q"
```

Result:

```text
7 passed, 1 warning
```

warning 仍是 passlib / Python `crypt` deprecation，不是本次清洗逻辑错误。
