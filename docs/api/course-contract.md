# SecureHub API Contract v1（A3 main path）
> Frozen: 2026-06-09 — 任何字段变动必须双签（A + B 或 A + C）并在本文件顶部追加 changelog。

## 0. 公共约定
- 所有 ID 用 UUID（字符串）
- 所有时间字段 ISO 8601 UTC
- 错误统一 `{detail: str, code?: str}`
- 分页统一 `?page=1&page_size=20`，响应 `{items, total, page, page_size}`

## 1. REST endpoints
### 1.1 GET  /api/v1/courses
Status: partial-real
Owner: member-a
Request shape:
```json
{"page": 1, "page_size": 20}
```
Response shape:
```json
{
  "items": [
    {
      "id": "00000000-0000-0000-0000-000000000101",
      "code": "course_websec_intro",
      "title": "Web 安全基础",
      "description": "SQL 注入、XSS、CSRF 等 Web 安全入门课程",
      "progress": 0.35
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```
Error codes: 400 / 422 / 503
Notes: `code` 对演示数据固定为 `course_websec_intro`；列表默认只返回 enabled 课程。

### 1.2 POST /api/v1/courses/{cid}/plan
Status: planned
Owner: member-a
Request shape:
```json
{
  "user_id": "00000000-0000-0000-0000-000000000001",
  "target_node_id": "00000000-0000-0000-0000-000000000201",
  "options": {"depth": 3}
}
```
Response shape:
```json
{
  "course_id": "00000000-0000-0000-0000-000000000101",
  "path": [
    {
      "node_id": "00000000-0000-0000-0000-000000000201",
      "title": "SQL 注入基础",
      "status": "ready",
      "prerequisites": []
    }
  ]
}
```
Error codes: 400 / 404 / 422 / 503
Notes: 路径必须来自 `knowledge_nodes` / `knowledge_edges`，不能由 LLM 裸生成。

### 1.3 POST /api/v1/courses/{cid}/resources/generate?type=doc|ppt|mindmap|quiz|lab|video|readings   (SSE)
Status: planned
Owner: member-a
Request shape:
```json
{
  "type": "doc",
  "kp_id": "00000000-0000-0000-0000-000000000201",
  "user_id": "00000000-0000-0000-0000-000000000001",
  "options": {"tone": "case_driven"}
}
```
Response shape: SSE event stream，事件类型见 §2
Error codes: 400 / 404 / 422 / 502 / 503
Notes: `evidence_chunk_ids` 非空，否则返回 422 `InsufficientEvidence`；第一个 `token` 事件前必须先发送 `evidence`。

### 1.4 GET  /api/v1/agent-runs?workflow=&user_id=&limit=
Status: partial-real
Owner: member-a
Request shape:
```json
{"workflow": "course_learning", "user_id": "00000000-0000-0000-0000-000000000001", "limit": 20}
```
Response shape:
```json
{
  "items": [
    {
      "id": "00000000-0000-0000-0000-000000000301",
      "workflow_name": "course_learning",
      "agent_name": "doc_archivist",
      "skill_name": "GenerateCourseDoc",
      "status": "success",
      "duration_ms": 2134,
      "quality_score": 0.86,
      "created_at": "2026-06-09T00:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```
Error codes: 400 / 422 / 503
Notes: `workflow` 可为空；默认按 `created_at DESC` 返回最近记录。

### 1.5 GET  /api/v1/agent-runs/{run_id}
Status: partial-real
Owner: member-a
Request shape:
```json
{"run_id": "00000000-0000-0000-0000-000000000301"}
```
Response shape:
```json
{
  "id": "00000000-0000-0000-0000-000000000301",
  "workflow_name": "course_learning",
  "agent_name": "doc_archivist",
  "skill_name": "GenerateCourseDoc",
  "status": "success",
  "duration_ms": 2134,
  "quality_score": 0.86,
  "created_at": "2026-06-09T00:00:00Z",
  "input_summary": {"query": "SQL 注入基础"},
  "output_summary": {"resource_id": "00000000-0000-0000-0000-000000000401"},
  "evidence_chunk_ids": ["00000000-0000-0000-0000-000000000501"],
  "parent_run_id": null,
  "token_usage": {"input": 320, "output": 680}
}
```
Error codes: 400 / 404 / 422 / 503
Notes: 前端 Agent Trace 只依赖本接口和 SSE `trace`，不直接读数据库。

### 1.6 POST /api/v1/profile/chat                                                                    (SSE)
Status: planned
Owner: member-a
Request shape:
```json
{
  "user_id": "00000000-0000-0000-0000-000000000001",
  "message": "我学过一点 Python，想入门 Web 安全",
  "history": []
}
```
Response shape: SSE event stream，事件类型见 §2
Error codes: 400 / 422 / 502 / 503
Notes: 画像构建完成后必须能更新 `ProfileDTO.dimensions` 和 `CapabilityDTO[]`。

### 1.7 GET  /api/v1/profile/me
Status: partial-real
Owner: member-a
Request shape:
```json
{"user_id": "00000000-0000-0000-0000-000000000001"}
```
Response shape:
```json
{
  "user_id": "00000000-0000-0000-0000-000000000001",
  "dimensions": {
    "knowledge_base": "beginner",
    "learning_goal": "web_security",
    "style": "case_driven",
    "prior_courses": [],
    "language": "zh",
    "cognitive_load": "medium"
  },
  "capabilities": [
    {"dimension": "web_security", "score": 0.35, "confidence": 0.6, "evidence_count": 0}
  ],
  "updated_at": "2026-06-09T00:00:00Z"
}
```
Error codes: 400 / 401 / 404 / 422 / 503
Notes: `dimensions` 至少 6 维；前端雷达图使用 `capabilities`。

### 1.8 PUT  /api/v1/profile/me
Status: partial-real
Owner: member-a
Request shape:
```json
{
  "dimensions": {
    "knowledge_base": "beginner",
    "learning_goal": "web_security",
    "style": "case_driven",
    "prior_courses": [],
    "language": "zh",
    "cognitive_load": "medium"
  }
}
```
Response shape:
```json
{
  "user_id": "00000000-0000-0000-0000-000000000001",
  "dimensions": {
    "knowledge_base": "beginner",
    "learning_goal": "web_security",
    "style": "case_driven",
    "prior_courses": [],
    "language": "zh",
    "cognitive_load": "medium"
  },
  "capabilities": [],
  "updated_at": "2026-06-09T00:00:00Z"
}
```
Error codes: 400 / 401 / 422 / 503
Notes: 本接口只改画像维度；能力分数由 assessment / learning event 流程更新。

### 1.9 POST /api/v1/rag/search
Status: partial-real
Owner: member-c
Request shape:
```json
{
  "domain": "course_websec",
  "query": "SQL 注入的基本原理",
  "top_k": 5,
  "filters": {"platform": "owasp", "asset_type": "web_article"}
}
```
Response shape:
```json
{
  "chunks": [
    {
      "chunk_id": "00000000-0000-0000-0000-000000000501",
      "document_id": "00000000-0000-0000-0000-000000000601",
      "source_url": "https://owasp.org/www-community/attacks/SQL_Injection",
      "platform": "owasp",
      "author": "OWASP",
      "published_at": null,
      "fetched_at": "2026-06-09T00:00:00Z",
      "rights_note": "CC BY-SA 4.0",
      "asset_type": "web_article",
      "excerpt": "SQL injection occurs when untrusted input is included in a query.",
      "page_no": null,
      "chapter": "SQL 注入基础",
      "timestamp": null,
      "reliability": 0.9
    }
  ],
  "total": 1
}
```
Error codes: 400 / 422 / 503
Notes: `top_k` 默认 5，上限 50；`domain` 必须过滤，禁止跨 domain 裸搜。

### 1.10 POST /api/v1/tutor/ask                                                                       (P1, SSE)
Status: planned
Owner: member-a
Request shape:
```json
{
  "user_id": "00000000-0000-0000-0000-000000000001",
  "course_id": "00000000-0000-0000-0000-000000000101",
  "question": "联合查询注入为什么要先判断列数？",
  "context": {"kp_id": "00000000-0000-0000-0000-000000000201"}
}
```
Response shape: SSE event stream，事件类型见 §2
Error codes: 400 / 404 / 422 / 502 / 503
Notes: career_planner 只做路由，不新增 tutor agent；答案仍需 `evidence`。

### 1.11 POST /api/v1/assessment/run                                                                 (P1)
Status: planned
Owner: member-a
Request shape:
```json
{
  "user_id": "00000000-0000-0000-0000-000000000001",
  "course_id": "00000000-0000-0000-0000-000000000101",
  "answers": [{"quiz_item_id": "00000000-0000-0000-0000-000000000701", "answer": "A"}]
}
```
Response shape:
```json
{
  "score": 0.8,
  "feedback": "SQL 注入基础掌握较好，建议继续练习参数化查询。",
  "updated_capabilities": [
    {"dimension": "web_security", "score": 0.42, "confidence": 0.65, "evidence_count": 1}
  ]
}
```
Error codes: 400 / 404 / 422 / 503
Notes: 必须写 `learning_events`，再由 outcome_evaluator 更新 `user_capabilities`。

## 2. SSE 事件契约（7 种，frozen）
### progress
Event name: `progress`
JSON shape:
```json
{"node_name": "validate", "agent_id": "doc_archivist", "skill_id": "GenerateCourseDoc", "percentage": 10, "status": "running"}
```
触发时机: Harness 阶段切换或工作流节点开始 / 完成 / 失败。
例子: `progress(validate)` → `progress(retrieve)` → `progress(compose)`。

### evidence
Event name: `evidence`
JSON shape:
```json
[
  {
    "chunk_id": "00000000-0000-0000-0000-000000000501",
    "document_id": "00000000-0000-0000-0000-000000000601",
    "source_url": "https://owasp.org/www-community/attacks/SQL_Injection",
    "platform": "owasp",
    "author": "OWASP",
    "published_at": null,
    "fetched_at": "2026-06-09T00:00:00Z",
    "rights_note": "CC BY-SA 4.0",
    "asset_type": "web_article",
    "excerpt": "SQL injection occurs when untrusted input is included in a query.",
    "page_no": null,
    "chapter": "SQL 注入基础",
    "timestamp": null,
    "reliability": 0.9
  }
]
```
触发时机: RAG 检索完成且 evidence_floor 通过后，在任何 `token` 前发送。
例子: 前端收到后刷新 EvidenceDrawer / CitationPanel。

### token
Event name: `token`
JSON shape:
```json
{"content": "SQL 注入的核心风险是", "index": 1}
```
触发时机: LLM 流式生成文本时。
例子: 前端增量渲染讲解文档正文。

### artifact
Event name: `artifact`
JSON shape:
```json
{"resource_id": "00000000-0000-0000-0000-000000000401", "resource_type": "doc", "object_key": "local/course/doc.md", "title": "SQL 注入基础讲解"}
```
触发时机: `generated_resources` 或 `storage_objects` 写入成功后。
例子: ResourceWorkspace 根据 `resource_id` 刷新资源卡片。

### trace
Event name: `trace`
JSON shape:
```json
{"run_id": "00000000-0000-0000-0000-000000000301", "parent_run_id": null, "agent_name": "doc_archivist", "skill_name": "GenerateCourseDoc", "status": "success", "duration_ms": 2134, "quality_score": 0.86}
```
触发时机: `agent_runs` 创建 / 成功 / 失败状态变化时。
例子: AgentTracePanel 高亮当前 agent 与 skill。

### done
Event name: `done`
JSON shape:
```json
{"run_id": "00000000-0000-0000-0000-000000000301", "final_output_ref": "generated_resources/00000000-0000-0000-0000-000000000401", "quality_score": 0.86}
```
触发时机: 工作流正常结束。
例子: 前端关闭加载态并显示最终资源。

### error
Event name: `error`
JSON shape:
```json
{"code": "InsufficientEvidence", "message": "至少需要 3 条证据才能生成。", "recoverable": true}
```
触发时机: 任何阶段失败且需要通知前端。
例子: RAG 召回不足时不调用 LLM，直接提示用户稍后重试或切换知识点。

## 3. 通用 DTO（与 backend/app/schemas/*.py B7 必须 1:1 对齐）
- EvidenceChunkDTO: 字段包含 `chunk_id`, `document_id`, `source_url`, `platform`, `author`, `published_at`, `fetched_at`, `rights_note`, `asset_type`, `excerpt`, `page_no`, `chapter`, `timestamp`, `reliability`；B7 中必填字段集合为 `chunk_id`, `document_id`, `excerpt`，其余字段可为 `null`。
- LearningPathNodeDTO: `node_id`, `title`, `status`, `prerequisites`
- LearningPathDTO: `course_id`, `path`
- GeneratedResourceDTO: `id`, `resource_type`, `title`, `content`, `object_key`, `evidence_chunk_ids`, `quality_score`, `status`
- AgentRunDTO: `id`, `workflow_name`, `agent_name`, `skill_name`, `status`, `duration_ms`, `quality_score`, `created_at`
- AgentRunDetailDTO: AgentRunDTO + `input_summary`, `output_summary`, `evidence_chunk_ids`, `parent_run_id`, `token_usage`
- ProfileDTO: `user_id`, `dimensions`, `capabilities`, `updated_at`（`dimensions` 对应 JSONB；`capabilities` 为 CapabilityDTO 数组）
- CapabilityDTO: `dimension`, `score`, `confidence`, `evidence_count`

## 4. Changelog
- 2026-06-09 初稿冻结
