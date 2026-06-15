# Evidence Contract v1 — frozen 2026-06-16

> Status: **frozen** — 任何字段增删 / 重命名 / 必填等级变更，必须同时更新：
> - `backend/app/schemas/evidence.py`（Pydantic 真理源）
> - `frontend/src/lib/sse.types.ts` 的 `EvidenceChunkDTO`
> - 本文件 §3 字段表 + §6 changelog
> - `backend/tests/schemas/test_contract_alignment.py` 与 `backend/tests/rag/test_evidence_contract.py`
>
> 与 `docs/api/course-contract.md §2 evidence` 的关系：那里描述 SSE event 信封（`event: "evidence"` + `data: EvidenceChunkDTO[]`），本文件描述 `EvidenceChunkDTO` 的字段语义。

## 0. 设计原则

- **wire 字段就是 DTO 字段**：传过去的字段名 / 类型 / 必填状态 = 这里写的。前后端 1:1 对齐。
- **DTO 仅作 UI 投影**：后端内部使用 `EvidenceCard` / `ChunkHit` 等结构；DTO 只负责跨网络。
- **无 `metadata: dict[str, Any]` 兜底**：所有需要展示的字段都是 top-level；不能展示的字段不应出现在 DTO。
- **不动数据层**：所有字段都从已有的 `documents` / `chunks` / `document_assets` 行 + JSONB metadata 派生，不增列。
- **多源采集合规**：`platform / source_url / collection_mode / rights_note / license` 一并记录，避免 A3 合规复审时漏字段。

## 1. 字段分层

| 层级 | 字段 | 必填条件 |
|---|---|---|
| 身份 | `chunk_id`, `document_id` | 永远必填 |
| 正文 | `chunk_text`, `score` | 永远必填 |
| 来源 | `platform`, `rights_note` | 永远必填 |
| 来源链接 | `source_url` | **当 `platform != "manual"` 时必填**；`platform == "manual"` 时允许为 `null` |
| 展示 | `title`, `author`, `published_at`, `fetched_at`, `collection_mode`, `asset_type`, `page_no`, `chapter`, `timestamp`, `license`, `reliability` | 可选 |

总字段数 18。

## 2. 字段表

| 字段 | 类型 | 必填 | 来源（数据层 → DTO） | 用途 | 示例 |
|---|---|---|---|---|---|
| `chunk_id` | UUID string | ✅ | `chunks.id` | 稳定身份；落 `agent_runs.evidence_chunk_ids[]` | `"00000000-0000-0000-0000-000000000501"` |
| `document_id` | UUID string | ✅ | `chunks.document_id` | 跳转文档详情；UI 折叠时按 doc 分组 | `"00000000-0000-0000-0000-000000000601"` |
| `chunk_text` | string | ✅ | `chunks.chunk_text`（必要时高亮裁剪到 ≤500 字符） | EvidenceDrawer / CitationPanel 正文 | `"SQL 注入通常发生在未受信任输入被拼接进查询语句时…"` |
| `score` | float ∈ [0,1] | ✅ | `retriever` 的 BM25 + 向量混合最终得分 | 用于在 UI 排序、显示相关度 | `0.87` |
| `platform` | string | ✅ | `chunks.metadata.platform` 或 `documents.metadata.platform` | 平台 badge；触发合规策略 | 见 §4.1 枚举 |
| `source_url` | string \| null | 条件必填 | `chunks.metadata.source_url` ↩ `documents.url` | 外链；UI "打开来源" 按钮 | `"https://owasp.org/www-community/attacks/SQL_Injection"` |
| `rights_note` | string | ✅ | `chunks.metadata.rights_note` ↩ `documents.metadata.rights_note` | UI 抽屉底部显示；版权合规 | `"CC BY-SA 4.0"` |
| `title` | string \| null | optional | `documents.title` | EvidenceCard 标题；CitationPanel 列表项 | `"OWASP SQL Injection 攻击说明"` |
| `author` | string \| null | optional | `documents.metadata.author` | 署名展示 | `"OWASP"` |
| `published_at` | ISO 8601 datetime \| null | optional | `documents.metadata.published_at` | 发布日期；UI 显示 `YYYY-MM-DD` | `"2025-11-18T00:00:00Z"` |
| `fetched_at` | ISO 8601 datetime \| null | optional | `documents.fetched_at` | 抓取日期；判断时效性 | `"2026-06-09T00:00:00Z"` |
| `collection_mode` | enum string \| null | optional | `documents.metadata.collection_mode` | 采集管道徽章；A3 合规审计字段 | 见 §4.2 枚举 |
| `asset_type` | string \| null | optional | `documents.source_type` ↩ `documents.metadata.asset_type` | 决定 §5 中字段差异 | 见 §4.3 枚举 |
| `page_no` | int \| null | optional | `chunks.metadata.page_no` | PDF 页码 | `42` |
| `chapter` | string \| null | optional | `chunks.metadata.chapter` | 章节定位 | `"SQL 注入基础"` |
| `timestamp` | float (秒) \| null | optional | `chunks.metadata.timestamp` | 视频时间戳 | `183` |
| `license` | string \| null | optional | `documents.metadata.license` | 显式 license（与 `rights_note` 互补） | `"CC BY-SA 4.0"` |
| `reliability` | float ∈ [0,1] \| null | optional | `documents.trust_score` 映射 | 来源可信度徽章 | `0.92` |

> ⚠️ `score` 与 `reliability` 不同：`score` 是与当前 query 的相关度，`reliability` 是来源本身的可信度。两者都是 0-1，但语义独立。UI 在抽屉里同时显示。

## 3. 数据层映射

```
+--------------------+        +-----------------+
| documents          |        | chunks          |
+--------------------+        +-----------------+
| id (UUID)          |◀──────| document_id     |
| title              |        | id (UUID)       |
| url                |        | domain          |
| source_type        |        | chunk_text      |
| fetched_at         |        | metadata (JSONB)|
| trust_score        |        +-----------------+
| metadata (JSONB):  |
|   platform         |
|   author           |
|   published_at     |
|   rights_note      |
|   license          |
|   asset_type       |
|   collection_mode  |
+--------------------+
```

`document_assets` 表用于存原始文件 / 转写 / 缩略图等的对象存储引用，**不进 DTO**（DTO 通过 `source_url` 暴露用户可点击的外链；`document_assets.object_key` 仅后端内部使用）。

合并规则（构造 DTO 时）：

1. 优先使用 `chunks.metadata` 中的字段，命中则用之。
2. `chunks.metadata` 缺失则向 `documents.metadata` 兜底；再缺则向 `documents.<column>` 兜底（如 `documents.url` 兜底 `source_url`）。
3. `score` 来自 retriever 的混合得分，与表行无关。
4. `chunk_text` 在 RAG 拼 prompt 时使用全文；在 DTO 中可裁剪到 500 字符（按高亮上下文）。

## 4. 枚举值

### 4.1 `platform`（开放字符串，建议枚举）

| 值 | 含义 | 合规要求 |
|---|---|---|
| `owasp` | OWASP 文档 | `rights_note` 写 `CC BY-SA 4.0` 或同等许可 |
| `portswigger` | PortSwigger Web Security Academy | 保留原站链接 |
| `bili` / `bilibili` | B 站 | 仅引用视频转写片段；不重托管原视频 |
| `zhihu` | 知乎 | 引用片段 + 原链 |
| `xhs` | 小红书 | 引用片段 + 原链 |
| `wechat_mp` / `wechat` / `weixin` | 微信公众号 | 引用片段 + 原链 |
| `cve` | CVE / CWE | 公共漏洞库 |
| `ctftime` | CTFtime | 公开赛事数据 |
| `github` | GitHub 开源项目 | 按 license（写入 `license`） |
| `csdn` | CSDN 博客 | 引用片段 + 原链 |
| `mitre` | MITRE ATT&CK / CWE | 公共知识库 |
| `securehub` | 平台自建知识库 | `rights_note` 写 `internal` |
| `manual` | 教师 / 助教手工录入 | `source_url` 允许为 `null`；`rights_note` 必填 |

> 后端 / 前端代码用开放 `str` 接收，校验时不限制集合；新平台无需改 schema，但**必须**在本表登记。

### 4.2 `collection_mode`（闭枚举）

| 值 | 含义 |
|---|---|
| `manual` | 手工录入 / 教师上传 |
| `api` | 平台开放 API |
| `scrapling` | Scrapling 风格爬取 |
| `mediacrawler` | MediaCrawler 风格采集 |
| `mindspider_reference` | MindSpider 参考实现采集 |

后端使用 Python `Enum`，前端使用 TypeScript `Literal union`。新增模式必须改 schema + 本表 + 测试。

### 4.3 `asset_type`（开放字符串，建议枚举）

| 值 | 字段语义 |
|---|---|
| `web_article` | 网页文章；常含 `chapter` / `author` / `published_at` |
| `video_transcript` | 视频转写片段；必含 `timestamp` |
| `page_image` | 截图 / 图片；常含 `page_no` 与 OCR 文本作为 `chunk_text` |
| `markdown` | Markdown 文档 |
| `pdf` | PDF 解析片段；必含 `page_no` |

历史 seed 数据中曾出现 `markdown_full` / `manual_import` 两值，过渡期允许，但新数据应使用上表 5 种之一。

## 5. asset_type 字段差异表

| asset_type | 期望非空字段 | 期望为 null 字段 |
|---|---|---|
| `web_article` | `chapter`, `author`, `published_at` | `page_no`, `timestamp` |
| `video_transcript` | `timestamp` | `page_no`, `chapter` |
| `page_image` | `page_no`（或缺省）；`chunk_text` 是 OCR 文本 | `chapter`, `timestamp` |
| `markdown` | `chapter`（一级标题） | `page_no`, `timestamp` |
| `pdf` | `page_no`, `chapter` | `timestamp` |

> 不强制：契约层只校验类型和必填集，期望字段缺失不报错，但 UI 渲染会按 §5 假定有/无。

## 6. Changelog

- **2026-06-16 v1 — frozen**：从 dev 上既有 14 字段扩展到 18 字段；将 `excerpt` 重命名为 `chunk_text`；新增 `score / title / collection_mode / license`；将 `collection_mode` 从 `metadata.collection_mode` 提到顶层；移除自由形态 `metadata: dict`；为 `source_url` 增加 "platform != manual 时必填" 校验。

## 7. SSE event 信封

事件名：`evidence`。`data` 字段：`EvidenceChunkDTO[]`。

```
event: evidence
data: [{...EvidenceChunkDTO}, ...]
```

完整描述见 `docs/api/course-contract.md §2 evidence`。

---

> 维护：本文件修改需 B + C 双 review，并跑通 `pnpm typecheck` + `uv run pytest backend/tests/schemas backend/tests/rag` 后方可合入 dev。
