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
