# SecureHub Session Log

Status: real

## 2026-06-11

### 成员 C

## 2026-06-09（Day 0 阻塞门打开 by Codex）
### 系统
- 完成：A1–A6 + B7–B10 全部基础设施
- 阻塞：讯飞星火 KEY / MinerU 选型 / GitHub @member-X 真实账号映射 待项目负责人补
- 明日：成员 A / B / C 分别开 feature/backend-agent-harness-workflow / feature/frontend-course-showcase / feature/knowledge-seed-quality 三条分支

## 2026-06-11

Status: real

### 成员 C
- 完成：P0 知识库导入底座，包含 `manual_import`、`markdown_import`、`pdf_mineru_import`。
- 完成：本地 `StorageService`，对象写入 `data/storage` 并登记 `storage_objects`。
- 完成：Web 安全课程 seed 从占位片段升级为 SQL 注入、XSS、CSRF、文件上传等真实教学切片，并补 `document_assets / storage_objects`。
- 完成：RAG smoke、无证据回归、PDF/MinerU loader、generated_resources、user_capabilities 测试。
- 完成：`scripts/demo_smoke.ps1`、`scripts/ingest_pdf_mineru.py`、Web 安全资料清单和 7 分钟演示 checklist。
- 阻塞：未接真实 Scrapling / MediaCrawler，按分工属于 P1；未接 MindSpider，按分工属于 P2。

## 2026-07-07 6-C-1 Scrapling 真采集

### 1. 采集执行清单

| 平台 | URL | 真跑通 / 缓存回放 / 不可达 | documents_id | chunks 增量 |
|---|---|---|---|---:|
| owasp | https://owasp.org/www-community/attacks/SQL_Injection | 真跑通 | dfc4b207-d5ac-5a08-bcab-2f56485ad9ff | 39 |
| owasp | https://owasp.org/www-community/attacks/xss/ | 真跑通 | c8e5e279-a137-58f0-8572-6819bfd7e7a0 | 63 |
| owasp | https://owasp.org/www-community/OWASP_Top_Ten | 不可达 404 | - | 0 |
| owasp | https://owasp.org/www-community/attacks/csrf | 真跑通 | 3cc82e9e-85e0-5696-a68d-2c361ced834a | 52 |
| owasp | https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload | 真跑通 | 6bd947fb-10e3-5201-9dea-d11362eb2dd4 | 93 |
| owasp | https://owasp.org/www-community/attacks/Server_Side_Request_Forgery | 真跑通 | 0380db8c-de2d-525b-80f5-fb5efd0eeb69 | 8 |
| owasp | https://owasp.org/www-community/attacks/Session_hijacking_attack | 真跑通 | fb96b73c-463f-5649-b7ae-dd16d571e692 | 12 |
| owasp | https://owasp.org/www-community/Broken_Access_Control | 真跑通 | db80e614-ba49-508e-befa-cc9b86a8411d | 33 |
| owasp | https://owasp.org/www-community/attacks/Command_Injection | 真跑通 | b28afa42-0b11-50ab-a40e-09e1ff689e27 | 35 |
| owasp | https://owasp.org/www-community/vulnerabilities/Deserialization_of_untrusted_data | 真跑通 | 95daa480-a0b3-5dcc-84cd-5aa112cb8173 | 41 |
| owasp | https://owasp.org/www-community/vulnerabilities/Insecure_Cryptographic_Storage | 不可达 404 | - | 0 |
| portswigger | https://portswigger.net/web-security/sql-injection | 真跑通 | a39835be-33ef-515e-9f07-fc8ba154df18 | 29 |
| portswigger | https://portswigger.net/web-security/cross-site-scripting | 真跑通 | f25894ca-58d0-5419-86b6-f3c5314a46ea | 24 |
| portswigger | https://portswigger.net/web-security/csrf | 真跑通 | 95eb59c8-7c27-546a-8130-45c520930616 | 17 |
| portswigger | https://portswigger.net/web-security/file-upload | 真跑通 | d8f65d21-ac57-5a0d-bf57-9176ce115f03 | 45 |
| portswigger | https://portswigger.net/web-security/ssrf | 真跑通 | 79d53fb2-2187-5e03-a648-9ae4cef7be65 | 24 |
| portswigger | https://portswigger.net/web-security/authentication | 真跑通 | 072266b7-62af-55b8-9f67-1cae7963b6f9 | 12 |
| portswigger | https://portswigger.net/web-security/access-control | 真跑通 | 935e6162-2f07-51a9-9ab7-f35d2c5e9a4d | 29 |
| github | https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.md | 真跑通 | 0e17f98e-3046-5830-b0aa-cf7c6c1f5247 | 38 |
| github | https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.md | 真跑通 | 65961f1a-5504-5f91-88cc-0b7bc935d2a9 | 50 |
| github | https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.md | 真跑通 | b1a5b2f1-d348-5ea8-b512-6cf932bf8518 | 135 |
| github | https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/File_Upload_Cheat_Sheet.md | 真跑通 | cbbf15c8-0a2d-5e6e-9146-0574f3b14685 | 24 |
| github | https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.md | 真跑通 | f69dc6bd-e673-5736-93bb-828386f9c235 | 52 |
| github | https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Authentication_Cheat_Sheet.md | 真跑通 | a1b7ce48-f287-5bf4-8c03-b471210e85d0 | 75 |
| github | https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Access_Control_Cheat_Sheet.md | 真跑通 | 7ae75797-0b69-5b0c-9e9a-8a3fc5a0ee29 | 1 |

### 2. 数据规模变化

- documents 增量：23（当前 `scrapling` 三平台：owasp 9 / portswigger 7 / github 7）
- document_assets 增量：46（raw_html: 23, markdown_full: 23）
- chunks 增量：931
- knowledge_nodes 增量：0（本轮只做采集物入库，不改图谱生成链路）

### 3. 合规判断记录

- robots.txt 拒绝：0 个。
- 401 / 403：0 个。
- 404：2 个，均为 OWASP 社区页，源码已标注 `UNREACHABLE 2026-07-07`。
- 本地缓存回放代替真跑：0 个；测试新增的是本地缓存 replay，不计为采集执行。
- `scrapling` Python 包未安装，本轮实际走 `scrapling_client.py` 的 httpx fallback 路径。
- 未使用 `proxy` / `solve_cloudflare` / `login` / `stealth` / CAPTCHA 绕过参数；`crawler_policy.py` 未改动。

### 4. 契约触碰情况

- 新增 `platform` 枚举值：无，使用既有 `owasp / portswigger / github`。
- 新增 `asset_type` 枚举值：无，新增 document assets 使用既有 `raw_html / markdown_full`。
- `collection_mode`：统一写入 `scrapling`。
- `docs/api/evidence-contract.md` draft-by-C 已追加，等待 B/C 双 review 后再升级为权威版。

### 5. 需 tag 关注

- @member-a：`scripts/demo_smoke.ps1 -BackendUrl` 只改请求 URL，自动启动仍硬编码 `--port 8000`；本轮未改 smoke 脚本，默认端口被 TIME_WAIT/占用影响时需手动预启动 8001 并加 `-NoStartBackend`。
- @member-b：EvidenceDrawer 侧可 review `platform / source_url / rights_note / fetched_at / collection_mode / asset_type` 展示字段，C 侧 draft 已列明。

### 6. 本轮 commit 列表

- `f1e80842 docs(demo): record 6-C-1 source inventory and evidence draft`
- `1dc0c384 test(knowledge): add Scrapling cache replay coverage`
- `85b9b244 feat(crawl): expand Scrapling public ingestion sources`
- 本节将随 `docs(log): record 6-C-1 Scrapling ingestion session` 提交。

### 7. 验收结果

- `uv run pytest tests/knowledge/test_scrapling_public_loader.py tests/knowledge/test_github_docs_loader.py -q -m "not llm_live"`：12 passed。
- `uv run pytest tests/knowledge/ -q -m "not llm_live"`：17 passed。
- `uv run pytest tests/rag/test_retrieve_course_websec.py -q -m "not llm_live"`：6 passed。
- `uv run pytest -m "not llm_live" -q`：114 passed, 2 deselected, 2 pre-existing async cleanup warnings。
- SQL 数据规模校验：全部满足，`bad_metadata=0`，`chunks_added=931`，`raw_html=23`，`markdown_full=23`。
- `./scripts/demo_smoke.ps1`：默认 8000 启动因端口 bind conflict 失败；手动预启动 8001 后 `./scripts/demo_smoke.ps1 -BackendUrl http://127.0.0.1:8001 -NoStartBackend` 命中 7 个 API 步骤并退出 0。

### 8. 遗留与下一步

- 未跑通 URL：`https://owasp.org/www-community/OWASP_Top_Ten`、`https://owasp.org/www-community/vulnerabilities/Insecure_Cryptographic_Storage`（均 404）。
- 建议 6-C-2 承接：MinerU PDF 批量入库时复用 `documents / document_assets / chunks` 与 draft EvidenceDTO 字段；另行评估 smoke 脚本端口参数是否需要 C/A 协调修复。

## 2026-07-07 6-C-2 中文教材章节级完整入库

### 0. 起手

- `.gitignore` 已排除教材 PDF、MinerU `full.md`、`mineru_ingested` 本地对象与 chapter 输出目录。
- 首个版权保护 commit 清理了已跟踪的 5-C seed PDF/full.md：`websec-textbook/full.md`、`websec-textbook/websec-textbook.pdf`、`websec-upload/full.md`、`websec-upload/websec-upload.pdf`。
- 本轮不 push、不建 PR；三本真教材 PDF 和完整 `full.md` 不进入 git。

### 1. 三本教材入库结果

| 教材 | document_id | chapter_count | chunk_count | 备注 |
|---|---|---:|---:|---|
| 现代密码学教程（第2版） | `7b89565f-0ba1-52fb-b91e-8a7e95469602` | 12 | 1218 | `ChineseTextbookHeadingClassifier` 按“第 X 章”切 chapter |
| 网络安全原理与实践 | `3fbaeff8-7996-5a0d-b99d-df12aea31c8c` | 23 | 724 | 同上 |
| 汇编语言（第3版） | `4776c945-bd89-5e54-a60d-720aaf7048af` | 13 | 538 | 同上 |

### 2. SQL 验收结果

- `documents`: 26
- `chunks`: 3411
- `markdown_chapter`: 48
- `original_pdf`: 3
- `pdf_mineru_chunks`: 2480
- `bad_chunks`: 0
- `rights_docs`: 3

### 3. Heading 分类器命中

- `crypto-basics`: BOOK 3, CHAPTER 12, SECTION 63, SUBSECTION 180, ITEM 498, UNKNOWN 65
- `network-security`: BOOK 2, CHAPTER 23, SECTION 81, SUBSECTION 189, ITEM 290, UNKNOWN 24
- `reverse-engineering`: BOOK 7, CHAPTER 13, SECTION 146, ITEM 77, UNKNOWN 143

### 4. 契约与合规

- `docs/api/evidence-contract.md` 升级为 v1.1，登记 `platform=mineru`、`asset_type=markdown_chapter`、`license=proprietary-educational-use`。
- `docs/demo/textbook-rights-policy.md` 新增三本教材版权处理策略；inventory、rights note、source manifest 已同步。
- `documents.metadata.rights_note` 使用教材版权模板：仅用于 SecureHub 内部教学演示 RAG 检索，不对外分发原文。

### 5. 重要事故与修复

- 发现旧 storage 默认前缀会把导入对象写回 `data/storage/course_websec/mineru/<name>/...` 输入目录，导致三本本地 PDF 被测试 fixture 覆盖成小文件。
- 已修复根因：默认 `storage_prefix` 改为 `course_websec/mineru_ingested`，测试传入独立 `storage_local_root`，并新增 `_ensure_storage_target_outside_inputs` 防止目标目录落入 MinerU 输入目录。
- `full.md` 已从 PostgreSQL `documents.raw_text` 恢复，当前大小约 1.10 MB / 835 KB / 553 KB。
- 三本 PDF 本体仍损坏：`crypto-basics.pdf` 35 bytes，`network-security.pdf` 38 bytes，`reverse-engineering.pdf` 41 bytes。已在本机搜索工作区与用户目录，未找到备份；需项目负责人重新拷贝三本教材 PDF 到本地。

### 6. 验收命令

- `uv run pytest tests/knowledge/ -q -m "not llm_live"`：30 passed。
- `uv run pytest tests/rag/test_retrieve_course_websec.py -q -m "not llm_live"`：7 passed。
- `uv run pytest -m "not llm_live" -q`：128 passed, 2 deselected, 2 async cleanup warnings。
- `uv run python -m json.tool ../data/course_websec/source_manifest.json`：通过。
- `git ls-files "data/storage/course_websec/mineru/*/*.pdf"` 与 `git ls-files "data/storage/course_websec/mineru/*/full.md"`：均为空。
- `git check-ignore -v`：三本教材 PDF/full.md、`mineru_ingested` PDF/full.md、chapter 目录均命中 `.gitignore`。
- Docker compose 侧 Redis 6379 被其他项目占用；PostgreSQL 已可用并完成 SQL 校验。

### 7. 需 tag 关注

- @member-b：EvidenceDrawer 未来可展示 `book_title / chapter / heading_path / section_hint`，形成“《教材》第 X 章 X.Y 小节”式引用。
- @project-lead：本地三本 PDF 需要重新复制；git 与 RAG 数据库已避免再次覆盖原始 MinerU 输入目录。

### 8. 本轮 commit 列表

- `5edc7547 chore(git): ignore textbook PDFs and full markdown from vcs`
- `97294198 feat(loader): ingest MinerU textbooks by chapter`
- `045adc76 test(knowledge): cover chaptered MinerU ingestion`
- `91212b8a chore(git): ignore MinerU ingested textbook outputs`
- `a243191c docs(demo): record textbook evidence contract and rights`
- 本节将随 `docs(log): record 6-C-2 textbook ingestion session` 提交。

### 9. 遗留与下一步

- 重新拷贝三本 PDF 后，可重跑 `.\scripts\ingest\ingest_pdf_mineru_batch.ps1` 验证幂等输出 `already ingested, skipped`；如需刷新 PDF hash，再使用 `-ForceReingest`。
- 建议 6-C-3 承接 MediaCrawler B 站真 export，补 Web 安全主战场视频转写证据。

## 2026-07-08 6-C-3 MediaCrawler B 站真 export 端到端

### 1. 输入数据

- RawDir: `data/raw/mediacrawler/bili/jsonl/`
- 文件数量：2（`search_contents_2026-06-15.jsonl`、`search_creators_2026-06-15.jsonl`）
- 是否真实 export：是，人工提供的 B 站 MediaCrawler 离线 export；本轮未运行 MediaCrawler 爬虫本体。
- 是否含评论：否，未发现 `*comments*.jsonl/json/csv`；本批次 `comments=0`。
- 是否含封面：含 `video_cover_url` 字段 19 条；仅写入 metadata，不下载封面图片。
- 是否含转写：否，`transcript/subtitle/asr_text/caption_text` 命中 0 条。

### 2. 入库结果

- documents 增量：19（导入前 `platform=bili` 为 0，导入后为 19）
- document_assets 增量：19（全部 `media_item_json`；无 comments export，因此无 `media_comment_json`）
- chunks 增量：21
- storage_objects 增量：19
- platform=bili documents：19
- collection_mode=mediacrawler documents：19

### 3. 合规判断

- 未绕登录 / 验证码 / 风控：是；只消费离线 export。
- 未下载原视频：是。
- PII 清洗字段：`cookies/cookie`、`token/csrf/xsec_token/session/credential`、`user_id/uid/mid/sec_uid`、`avatar/avatar_url/face/head_url`、`ip_location/home_url/homepage/signature/sign`。
- rights_note：`Bilibili UGC 用户内容，仅学习用途保留摘要与引用；不下载原视频，不批量转载。`
- 结构化 storage JSON key 校验：19 个对象 `bad_key_paths={}`。

### 4. 验收命令

- pytest：`uv run pytest tests/knowledge/test_mediacrawler_normalizer.py -q`：3 passed；`uv run pytest tests/knowledge/ -q -m "not llm_live"`：31 passed；`uv run pytest tests/rag/test_retrieve_course_websec.py -q -m "not llm_live"`：7 passed；`uv run pytest -m "not llm_live" -q`：129 passed, 2 deselected, 2 pre-existing async cleanup warnings。
- RAG：`RetrievalService.retrieve("SQL 注入 XSS Web安全", domain="course_websec", filters={"platform": "bili"})`：召回 5 条。
- SQL / Python 校验：`platform_bili_documents=19`，`collection_mode_mediacrawler_documents=19`，`chunks=21`，`document_assets=19`，`storage_objects=19`，`missing_metadata=[]`。
- git check-ignore：`data/raw/mediacrawler/**/*.jsonl/json/csv` 命中 `.gitignore`；本轮新增 `data/storage/course_websec/mediacrawler/**/*.json/jsonl/csv` ignore，防止归一化 UGC JSON 误提交。
- JSON：`uv run python -m json.tool ..\data\course_websec\source_manifest.json`：通过。
- demo smoke：`.\scripts\demo_smoke.ps1`：7 passed（Postgres / Redis 使用 docker compose 本地容器）。

### 5. 遗留与下一步

- 样本数量不足：否，本批次 19 条 contents，满足至少 5 个真实 B 站视频 document。
- cover_image 是否缺失：缺失；仅有 `cover_url` metadata，未启用封面安全下载。
- transcript 是否缺失：缺失；本批次 export 未提供转写字段。
- 交给 6-C-4 的事项：继续补 Web 安全 10 主题覆盖时，可优先补带转写或评论摘要的人工 export，提高视频证据 chunk 密度。
## 2026-07-08 6-C-5 半截交付（爬虫扩展完成，embedding 交接给 6-C-6）

### 1. 完成部分
- §4 B.1 MindSpider reference adapter：完整（adapter + fixture + CLI + tests + docs）
- §4 B.2 MediaCrawler zhihu + xhs：完整（normalizer + CLIs + tests + docs）
  * zhihu 真采集 18 documents（真扁平结构 + 纯文本 content_text）
  * xhs graceful skip 首行解析错误

### 2. 交接给 6-C-6 部分
- §3 A BGE-M3 embedding：跑到 2096/3555（59%）后暂停
- BGE-M3 相关代码全部 revert（embedding_service.py / embed_chunks.py / pyproject.toml）
- DB 中 2096 条 BGE-M3 ready 向量待 6-C-6 Phase 6 reset

### 3. 需 tag
- @codex-6-c-6: 请从空白 embedding_service 开始，按 Plan/7-8 §11-31 做 Qwen 迁移
- @member-a: rag/retriever.py fallback 阈值判断（本轮未改）

### 4. Commit 列表
- e5cf6af3 chore(git): ignore MindSpider runtime output data/storage/news/
- 2a947bbd feat(mediacrawler): zhihu and xhs export normalizers with graceful skip
- 1cd57315 feat(mindspider): P2 reference adapter with topic normalizer and fixture import

### 5. 遗留
- 3555 chunks 待 Qwen 全量重跑（交接给 6-C-6）
- .codegraph/codegraph.db 无关脏，不 commit

## 2026-07-08 6-C-6 Embedding 迁移到 Qwen text-embedding-v4

### 0. 与 6-C-5 半截交付的关系
- 6-C-5 §3 A（BGE-M3）已 revert，本轮代码侧改为 Qwen OpenAI-compatible provider 架构
- 6-C-5 §4 B（爬虫扩展）保留，未触碰 crawling 代码

### 1. Phase 完成度
| Phase | 结果 | 关键数据 |
|---|---|---|
| 0. 安全准备 | 通过 | API Key 不打印；当前环境未暴露 DASHSCOPE_* |
| 1. 只读审计 | 通过 | 发现 hash stub、retriever 动态猜维度、profile 缺失、异常吞掉等问题 |
| 2. Provider 实现 | 通过 | `backend/app/llm/embeddings/` 7 文件；Qwen + fixture + factory + service |
| 3. 单元测试 | 通过 | `uv run pytest -m "not llm_live and not embedding_live" -q`：153 passed, 3 deselected |
| 4. Live Test | 阻塞 | 当前配置中 `DASHSCOPE_API_KEY` / `DASHSCOPE_OPENAI_COMPATIBLE_BASE_URL` 不存在；live test skipped |
| 5. DB Preflight | 阻塞 | 当前连接 DB：total=10, pending=10, ready=0；与交接 baseline 3555/2096 不符 |
| 6. Reset 旧向量 | 未执行 | dry-run 命中 legacy_unprofiled_ready=0；按 Plan 停止破坏性步骤 |
| 7. 全量重嵌入 | 未执行 | 因 Phase 4/5 门禁未满足，未调用真实 API 写库 |
| 8. Postflight | 部分完成 | 代码/测试/安全自查完成；DB postflight 不适用 |

### 2. 迁移前后对比
- 交接预期：ready=2096 (BGE-M3 legacy 无 profile) + pending=1459，总数 3555
- 当前实际连接 DB：pending=10, ready=0, embedding NULL=10
- 迁移后数据库状态：未改动（Phase 6/7 未执行）
- 累计 API 消耗：0 tokens / 0 元（未真实调用）
- 首次 Qwen 请求延迟 / 平均延迟 / p95 延迟：未获取（live 配置缺失）

### 3. 契约触碰
- `backend/.env.example` 新增 DASHSCOPE_* + EMBEDDING_* Qwen 配置空占位
- `chunks.metadata.embedding_profile` 契约引入，锁定 `qwen-openai-compatible:text-embedding-v4:1024:dense:v1`
- `backend/app/llm/embeddings/` 新目录 7 文件
- `docs/api/evidence-contract.md` v1.1 -> v1.2（新增 embedding profile 字段说明）
- `pyproject.toml` 无净新增依赖（沿用 httpx）

### 4. 合规
- API Key 从环境变量 / `.env.local` 读取，未打印完整 Key
- 禁止跨模型 fallback：Qwen provider 失败抛领域异常，不回 hash / BGE / fixture
- `reset_embeddings` 默认 dry-run，真正执行必须 `--yes`
- 日志不记录 Authorization / 完整原文 / 完整 vector

### 5. rag/retriever 修改（3 处最小安全接入）
- 禁止动态猜维度：query embedding 维度必须等于 `settings.EMBEDDING_DIM`
- 过滤仅当前 profile：`metadata->>'embedding_profile' = EMBEDDING_PROFILE`
- API 故障不吞异常：`EmbeddingError` 显式传播

### 6. 需 tag
- @member-a: `backend/app/llm/embeddings/` 归 LLM Provider 家族，长期归你维护；本轮由 C 完成搬迁
- @member-b: EvidenceDrawer 未来可展示 embedding_profile 徽章
- @project-lead: API 消耗成本 0；需补齐 DashScope env 与目标 3555 chunks DB 后再跑 Phase 4-7

### 7. Commit 列表（按 Phase 切分）
- 待提交：`feat(embedding): [Phase 2] add Qwen embedding provider @member-a`
- 待提交：`feat(embedding): [Phase 6-7] add reset and recoverable embedding jobs @member-a`
- 待提交：`test(embedding): [Phase 3] cover Qwen fixture retriever contracts @member-a`
- 待提交：`docs(embedding): [Phase 8] record Qwen profile contract and log @member-a`

### 8. Review QA 结论
- 自查 13 项：生产 hash vector 已移除；无 Qwen -> BGE fallback；retriever profile 过滤已测；API Key 无实值入库；batch 上限 10；返回顺序/维度/NaN/Inf/429/500/timeout 均有单测；reset 默认 dry-run；job 可恢复并保留非 embedding metadata
- 剩余阻塞：真实 live API 和 DB reset/re-embedding 未执行，原因是环境 Qwen 变量缺失且当前 DB baseline 不符

### 9. 遗留
- 补齐 `backend/.env.local` 的 `DASHSCOPE_API_KEY` / `DASHSCOPE_OPENAI_COMPATIBLE_BASE_URL`
- 切回交接目标 DB（应为 3555 chunks，其中 2096 legacy ready）后重跑 Phase 4-7
- Batch File API 迁移（Plan §十建议后续单独轮次）
- Sparse embedding / Reranker（Plan §1 明确本轮不做）
- rag/retriever fallback 阈值调优（A 的领地，本轮不改）
