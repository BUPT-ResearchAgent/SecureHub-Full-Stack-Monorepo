# Web 安全课程资料清单

Status: real

## P0 课程范围

课程：Web 安全基础  
Domain：`course_websec`  
核心知识点：SQL 注入、XSS、CSRF、文件上传、SSRF、认证与会话安全、访问控制、命令执行、反序列化、安全编码与防护。

## 新增采集来源

| 来源 | platform | 阶段 | 入库方式 | 合规说明 |
|---|---|---:|---|---|
| OWASP SQL Injection | `owasp` | P0 | `manual_import` / Markdown 摘要 | 公开社区资料，保留来源链接和 CC BY-SA 说明 |
| OWASP XSS | `owasp` | P0 | `manual_import` / Markdown 摘要 | 公开社区资料，保留来源链接和 CC BY-SA 说明 |
| PortSwigger CSRF | `portswigger` | P0 | `manual_import` / Markdown 摘要 | 公开学习资料，只做课程索引和摘要切片 |
| PortSwigger File Upload | `portswigger` | P0 | `manual_import` / Markdown 摘要 | 公开学习资料，只做课程索引和摘要切片 |
| SecureHub 课程组手工讲义 | `manual` | P0 | `markdown_import` | 团队整理演示材料，可展示全文 |
| PDF / MinerU 解析输出 | `mineru` | P0 | `pdf_mineru_import` | 原 PDF 和 Markdown 分别登记为资产，保留原始来源 |

## 字段要求

每条资料进入 `documents.metadata` 与 `chunks.metadata` 时必须包含：

`platform`、`source_url`、`author`、`published_at`、`fetched_at`、`license`、`rights_note`、`asset_type`。

## P1 / P2 预留

Scrapling：OWASP、PortSwigger、GitHub Docs、公开安全博客。  
MediaCrawler：B 站、知乎、小红书的小规模离线 export。  
MindSpider：仅作 P2 舆情流程参考，不进入 P0 主链路。
