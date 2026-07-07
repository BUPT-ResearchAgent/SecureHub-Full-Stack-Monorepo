# Web 安全课程资料清单

Status: real

## P0 / P1 课程范围

课程：Web 安全基础  
Domain：`course_websec`  
核心知识点：SQL 注入、XSS、CSRF、文件上传、SSRF、认证与会话安全、访问控制、命令执行、反序列化、安全编码与防护。

## Source Inventory

| Source | platform | source_url | rights_note | collection_mode | asset_type | 已入库 | 有测试 |
|---|---|---|---|---|---|---|---|
| OWASP SQL Injection | `owasp` | https://owasp.org/www-community/attacks/SQL_Injection | OWASP 社区公开资料，教学演示引用并保留来源。 | `manual` / `scrapling` fixture | `markdown_full` / `web_article` | 是：`seed_course_websec.py`，offline loader fixture | 是：RAG smoke、Scrapling loader |
| OWASP XSS | `owasp` | https://owasp.org/www-community/attacks/xss/ | OWASP 社区公开资料，按 CC BY-SA 4.0 署名引用并保留来源。 | `manual` / `scrapling` fixture | `markdown_full` / `web_article` | 是：seed 覆盖反射型/存储型 XSS，loader 有 offline fixture | 是：RAG smoke、Scrapling preset |
| PortSwigger CSRF | `portswigger` | https://portswigger.net/web-security/csrf | PortSwigger 公开学习资料，保留链接，仅做课程索引和摘要切片。 | `manual` | `markdown_full` | 是：seed 覆盖 CSRF | 是：RAG smoke |
| PortSwigger File Upload | `portswigger` | https://portswigger.net/web-security/file-upload | PortSwigger 公开学习资料，保留链接，仅做课程索引和摘要切片。 | `manual` | `markdown_full` | 是：seed 覆盖文件上传 | 是：RAG smoke |
| SecureHub 手工讲义 | `manual` | https://demo.securehub.local/websec/*.md | 团队整理的课程演示材料，可在比赛演示中展示。 | `manual` | `markdown_full` | 是：seed 覆盖认证、访问控制、命令执行等主题 | 是：RAG smoke、markdown loader |
| PDF / MinerU SSRF fixture | `mineru` | https://demo.securehub.local/pdf/websec-ssrf-mineru.pdf | PDF/MinerU 离线解析 fixture；仅用于课程知识库演示，保留原始来源。 | `manual` fixture; loader path is `pdf_mineru_import` | `pdf` | 是：seed metadata；loader 可写 `original_pdf` + `markdown_full` + `page_image` | 是：RAG smoke、course loader |
| GitHub Docs fixture | `github` | https://raw.githubusercontent.com/securehub-demo/websec-labs/main/docs/secure-coding.md | 开源仓库公开文档；遵守仓库许可证，保留来源链接。 | `scrapling` offline fixture | `raw_html` → chunks | 是：offline importer test 写入统一表 | 是：GitHub Docs loader + `platform=github` retrieval |
| B 站 MediaCrawler fixture | `bili` | https://www.bilibili.com/video/BV1securehub | MediaCrawler 离线导出样本；仅用于学习与比赛演示，保留平台链接与作者信息，不批量转载。 | `mediacrawler` export fixture | `media_item_json` / `media_comment_json` | 是：E2E fixture 写入统一表 | 是：MediaCrawler normalizer + retrieval |

## 2026-07-07 6-C-1 Scrapling 真采集

| 状态 | platform | source_url | rights_note | collection_mode | chunks | 有无测试 |
|---|---|---|---|---|---:|---|
| [真采集/2026-07-07] | `owasp` | https://owasp.org/www-community/attacks/SQL_Injection | OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。 | `scrapling` | 39 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `owasp` | https://owasp.org/www-community/attacks/xss/ | OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。 | `scrapling` | 63 | 是：cache replay + metadata |
| [不可达/2026-07-07] | `owasp` | https://owasp.org/www-community/OWASP_Top_Ten | OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。 | `scrapling` | 0 | 源码标注 404，不入库 |
| [真采集/2026-07-07] | `owasp` | https://owasp.org/www-community/attacks/csrf | OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。 | `scrapling` | 52 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `owasp` | https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload | OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。 | `scrapling` | 93 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `owasp` | https://owasp.org/www-community/attacks/Server_Side_Request_Forgery | OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。 | `scrapling` | 8 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `owasp` | https://owasp.org/www-community/attacks/Session_hijacking_attack | OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。 | `scrapling` | 12 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `owasp` | https://owasp.org/www-community/Broken_Access_Control | OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。 | `scrapling` | 33 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `owasp` | https://owasp.org/www-community/attacks/Command_Injection | OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。 | `scrapling` | 35 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `owasp` | https://owasp.org/www-community/vulnerabilities/Deserialization_of_untrusted_data | OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。 | `scrapling` | 41 | 是：cache replay + metadata |
| [不可达/2026-07-07] | `owasp` | https://owasp.org/www-community/vulnerabilities/Insecure_Cryptographic_Storage | OWASP 公开社区文档；按 CC BY-SA 4.0 署名引用，保留来源链接。 | `scrapling` | 0 | 源码标注 404，不入库 |
| [真采集/2026-07-07] | `portswigger` | https://portswigger.net/web-security/sql-injection | PortSwigger Web Security Academy 公开学习内容，仅引用摘要与切片供教学演示，链接回原页 | `scrapling` | 29 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `portswigger` | https://portswigger.net/web-security/cross-site-scripting | PortSwigger Web Security Academy 公开学习内容，仅引用摘要与切片供教学演示，链接回原页 | `scrapling` | 24 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `portswigger` | https://portswigger.net/web-security/csrf | PortSwigger Web Security Academy 公开学习内容，仅引用摘要与切片供教学演示，链接回原页 | `scrapling` | 17 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `portswigger` | https://portswigger.net/web-security/file-upload | PortSwigger Web Security Academy 公开学习内容，仅引用摘要与切片供教学演示，链接回原页 | `scrapling` | 45 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `portswigger` | https://portswigger.net/web-security/ssrf | PortSwigger Web Security Academy 公开学习内容，仅引用摘要与切片供教学演示，链接回原页 | `scrapling` | 24 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `portswigger` | https://portswigger.net/web-security/authentication | PortSwigger Web Security Academy 公开学习内容，仅引用摘要与切片供教学演示，链接回原页 | `scrapling` | 12 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `portswigger` | https://portswigger.net/web-security/access-control | PortSwigger Web Security Academy 公开学习内容，仅引用摘要与切片供教学演示，链接回原页 | `scrapling` | 29 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `github` | https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.md | OWASP CheatSheetSeries 官方仓库；按 CC BY-SA 4.0 署名引用；raw markdown 直取 | `scrapling` | 38 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `github` | https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.md | OWASP CheatSheetSeries 官方仓库；按 CC BY-SA 4.0 署名引用；raw markdown 直取 | `scrapling` | 50 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `github` | https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.md | OWASP CheatSheetSeries 官方仓库；按 CC BY-SA 4.0 署名引用；raw markdown 直取 | `scrapling` | 135 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `github` | https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/File_Upload_Cheat_Sheet.md | OWASP CheatSheetSeries 官方仓库；按 CC BY-SA 4.0 署名引用；raw markdown 直取 | `scrapling` | 24 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `github` | https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.md | OWASP CheatSheetSeries 官方仓库；按 CC BY-SA 4.0 署名引用；raw markdown 直取 | `scrapling` | 52 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `github` | https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Authentication_Cheat_Sheet.md | OWASP CheatSheetSeries 官方仓库；按 CC BY-SA 4.0 署名引用；raw markdown 直取 | `scrapling` | 75 | 是：cache replay + metadata |
| [真采集/2026-07-07] | `github` | https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/Access_Control_Cheat_Sheet.md | OWASP CheatSheetSeries 官方仓库；按 CC BY-SA 4.0 署名引用；raw markdown 直取 | `scrapling` | 1 | 是：cache replay + metadata |

## 2026-07-07 6-C-2 中文教材章节级入库

| 状态 | platform | 教材 | source_url | rights_note | collection_mode | chapters | chunks | 有无测试 |
|---|---|---|---|---|---|---:|---:|---|
| [已入库/2026-07-07] | `mineru` | 现代密码学教程（第2版） | `local://crypto-basics.pdf` | 教材版权归原作者与出版社；仅用于 SecureHub 内部教学演示 RAG 检索，不对外分发原文。 | `manual` / `pdf_mineru` | 12 | 1218 | 是：chapter classifier、MinerU ingestion、RAG fixture |
| [已入库/2026-07-07] | `mineru` | 网络安全原理与实践 | `local://network-security.pdf` | 同上 | `manual` / `pdf_mineru` | 23 | 724 | 是：chapter classifier、MinerU ingestion、RAG fixture |
| [已入库/2026-07-07] | `mineru` | 汇编语言（第3版） | `local://reverse-engineering.pdf` | 同上 | `manual` / `pdf_mineru` | 13 | 538 | 是：chapter classifier、MinerU ingestion、RAG fixture |

说明：三本教材按“第 X 章”语义切出 `markdown_chapter` assets，并把 `chapter / heading_path / section_hint / asset_id / book_title` 写入每个 chunk metadata。PDF 和整本 `full.md` 均被 `.gitignore` 排除；本地 PDF 本体需由项目负责人保留或重新复制，不进入 git。

## Metadata Floor

每条资料进入 `documents.metadata` 与 `chunks.metadata` 时必须包含：

`platform`、`source_url`、`author`、`rights_note`、`collection_mode`、`asset_type`。

建议同时保留：

`published_at`、`fetched_at`、`license`、`chapter`、`page_no`、`reliability`。

当前 seed 验收：

- 17 `knowledge_nodes`
- 68 `chunks`
- 5 SQL 注入 `quiz_items`
- official source：OWASP / PortSwigger
- markdown/manual source：SecureHub 手工讲义
- PDF/MinerU evidence：`platform=mineru`，`asset_type=pdf`，`page_no=12`

## 合规边界

- Scrapling / GitHub Docs / OWASP / PortSwigger 测试使用离线 fixture，不依赖外网跑 CI。
- MediaCrawler 只消费一个平台的最小离线 export fixture，不爬公网、不引入登录态。
- MindSpider 仅保留 P2 reference demo 说明，不进入生产采集链路，不新增 agent，不新增并列表。
- fund / policy / job / competition 扩展数据若需要展示，只能少量 seed/fixture，继续使用统一 `documents/chunks` 并按 `domain` 区分。
