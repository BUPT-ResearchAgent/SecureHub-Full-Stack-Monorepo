# Teacher API Contract（草案 · 4-B-2）

> 状态：**draft** — 由前端（成员 B）在 4-B-2 起草，后端实现由成员 A 在后续轮次完成。
> 当前所有教师端页面均以 mock 数据驱动（`frontend/src/lib/mock/teacher.mock.ts`），后端落地后通过 `withMockFallback` 自然切换。
> 与 `docs/api/course-contract.md` 的边界：本契约仅涵盖教师视角（含审核 / 生成 / 编排），不重写学生侧的课程 / 资源 / 画像端点。

## 0. 通用约定

- 所有路径前缀：`/api/v1/teacher`
- 所有响应：`application/json; charset=utf-8`
- 鉴权：`Authorization: Bearer <jwt>`，要求当前用户角色 ∈ `{course_teacher, research_mentor, career_mentor, hybrid}`
- 错误模型：复用 `docs/api/course-contract.md §0` 中的 `ApiError`
- 大文件上传：`multipart/form-data`
- 长任务（生成 / 上传 / 推荐）：返回 `task_id`，后续通过 SSE `/api/v1/agents/runs/{task_id}/stream` 订阅 7 类事件

## 1. 通用教师身份与名册

### 1.1 `GET /api/v1/teacher/me`
当前教师身份与权限。

请求：无 body。
响应：
```json
{
  "id": "teacher-wang",
  "name": "王老师",
  "role": "course_teacher",
  "department": "计算机学院 · 网络安全系",
  "title": "副教授 / 课程负责人",
  "courses": ["web-security-foundation", "crypto-foundation"],
  "classes": ["class-23-1", "class-23-2"],
  "permissions": [
    "course.manage", "material.upload", "quiz.generate",
    "quiz.moderate", "assignment.publish", "student.view",
    "notice.broadcast"
  ]
}
```
触发的 agent skill：无。Mock fallback：返回 `MOCK_TEACHERS[role]`。

---

### 1.2 `GET /api/v1/teacher/dashboard`
教师总览 KPI。

Query：`role_view?` —— 综合型教师可指定切换视角（`course | research | career | all`）。

响应：
```json
{
  "kpis": [
    {"label": "所教课程", "value": 2, "trend": "+0"},
    {"label": "学生总数", "value": 62, "trend": "+6 本周"},
    {"label": "24h 智能体调用", "value": 184, "trend": "+12%"}
  ],
  "todos": [
    {"icon": "quiz", "text": "12 道待审核题目", "target": "/teacher/quiz-bank?status=pending"}
  ],
  "capability_distribution": [
    {"dimension": "web_security", "avg": 0.61, "min": 0.21, "max": 0.92}
  ],
  "struggle_heat": [
    {"knowledge_point": "SQL 注入 · 盲注", "ratio": 0.62}
  ]
}
```
触发的 agent skill：`outcome_evaluator.AggregateCapability`（生成 capability_distribution）。

---

### 1.3 `GET /api/v1/teacher/students`
学生名册（按身份过滤）。

Query：`class_id? · keyword? · capability_below? · role_view?`

响应：
```json
{
  "items": [
    {
      "id": "stu-1000",
      "name": "李伟",
      "class_id": "class-23-1",
      "progress": 65,
      "agent_runs": 14,
      "career_direction": "甲方安全",
      "research_project_id": null,
      "consultation_id": "cs-1",
      "last_activity_at": "2026-06-14T20:00:00Z"
    }
  ],
  "total": 60
}
```

---

### 1.4 `GET /api/v1/teacher/students/{student_id}`
学生详情：能力雷达、最近活动、关联科研 / 咨询。

响应：
```json
{
  "id": "stu-1000",
  "capability": {"web_security": 0.62, "crypto": 0.45, "system_security": 0.51,
                  "pentest": 0.48, "governance": 0.6, "ai_security": 0.4},
  "recent_runs": [
    {"agent_name": "career_planner", "skill_name": "BuildLearningPersona", "duration_ms": 1640, "quality_score": 0.87}
  ],
  "evidence_refs": ["chunk-001", "chunk-014"]
}
```
触发的 agent skill：`career_planner.RetrievePersona`。

---

### 1.5 `POST /api/v1/teacher/notices`
发布公告。

Request：
```json
{
  "title": "本周三 19:00 · OWASP Top 10 复盘班会",
  "target": {"type": "class", "id": "class-23-1"},
  "body": "...",
  "channels": ["dingtalk", "email"]
}
```

Response: `{"notice_id": "n-...", "delivered": 32}`

---

## 2. 课程教师能力（`course_teacher` / `hybrid`）

### 2.1 `GET /api/v1/teacher/courses`
我的课程。

响应：`{"items": [{"id": "...", "title": "...", "student_count": 32, "agent_calls": 184, "avg_progress": 0.6}]}`

### 2.2 `PUT /api/v1/teacher/courses/{course_id}`
修改课程信息（目录调整、knowledge_node 启停、能力维度权重）。

Request：
```json
{
  "title": "Web 安全基础（2026 春）",
  "summary": "...",
  "outline": [{"node_id": "kn-001", "order": 0}, {"node_id": "kn-002", "order": 1}]
}
```
触发的 agent skill：`task_orchestrator.RebuildLearningPath`（异步）。

### 2.3 `GET /api/v1/teacher/materials`
教材列表。Query：`course_id? · status?`

响应：
```json
{
  "items": [
    {"id": "mat-001", "title": "Web 安全基础（第 3 版）",
     "course_id": "web-security-foundation",
     "pages": 286, "chunks": 412, "status": "indexed",
     "uploaded_at": "..."}
  ]
}
```

### 2.4 `POST /api/v1/teacher/materials/upload`
上传教材（multipart/form-data，长任务）。

Request：
- `file`: PDF / Markdown / DOCX
- `course_id`: string

Response: `{"task_id": "...", "material_id_preview": "mat-..."}`

SSE 事件链（订阅 `/api/v1/agents/runs/{task_id}/stream`）：
1. `progress` — `doc_archivist.ParseDocument` 阶段（解析页数）
2. `progress` — `topic_explorer.ChunkAndIndex` 阶段（chunk 数）
3. `evidence` — chunk 写入完成
4. `trace` — agent_runs 落地（3 次）
5. `done` — `{material_id, pages, chunks, quality_score}`

### 2.5 `DELETE /api/v1/teacher/materials/{material_id}`
下架教材：`documents.status = archived` + 关联 `chunks.embedding_status = archived`。

### 2.6 `GET /api/v1/teacher/quiz-bank`
题库。Query：`status (pending | approved | rejected) · course_id? · knowledge_point?`

响应：`{"items": [{"id": "q-001", "type": "single", "difficulty": "easy", "question": "...", "options": [...], "answer": "B", "explanation": "...", "knowledge_point": "...", "quality_score": 0.88, "generated_by": "competition_advisor.GenerateQuiz", "status": "pending", "created_at": "..."}]}`

### 2.7 `POST /api/v1/teacher/quiz-bank/generate`
触发智能体生成题目（长任务）。

Request：
```json
{
  "course_id": "web-security-foundation",
  "knowledge_points": ["SQL 注入 · 盲注", "XSS"],
  "type": "mixed",         // single | multiple | short | code | mixed
  "difficulty": "medium",   // easy | medium | hard | extreme
  "count": 5
}
```
Response: `{"task_id": "...", "estimated_seconds": 22}`

SSE 事件链：
1. `progress` — `rag.retrieve` 检索切片
2. `evidence` — evidence_floor 通过（≥3 切片）
3. `progress` — `competition_advisor.GenerateQuiz` LLM 生成
4. `progress` — `outcome_evaluator.QualityCheck` 评分
5. `artifact` — 写入 `quiz_items`（status=pending）
6. `trace` — agent_runs 落地（3 次）
7. `done` — `{quiz_ids: ["q-..."], avg_quality_score: 0.83}`

### 2.8 `POST /api/v1/teacher/quiz-bank/{quiz_id}/approve`
教师批准。响应：`{"status": "approved"}`

### 2.9 `POST /api/v1/teacher/quiz-bank/{quiz_id}/reject`
教师退回。Request：`{"reason": "..."}`

### 2.10 `PUT /api/v1/teacher/quiz-bank/{quiz_id}`
编辑题目。

Request：`{question?, options?, answer?, explanation?, knowledge_point?, difficulty?}`

### 2.11 `GET /api/v1/teacher/assignments`
作业列表。Query：`status (draft | active | closed)?`

响应：`{"items": [{"id": "as-001", "title": "...", "status": "active", "due_at": "...", "submitted_count": 24, "graded_count": 20, "average_score": 78.4}]}`

### 2.12 `POST /api/v1/teacher/assignments`
发布作业。

Request：
```json
{
  "title": "第 4 周综合训练",
  "description": "...（markdown）",
  "course_id": "web-security-foundation",
  "class_id": "class-23-1",
  "quiz_ids": ["q-005", "q-007"],
  "due_at": "2026-06-25T16:00:00Z",
  "allow_late": false,
  "auto_grade": true,
  "publish": true
}
```
Response: `{"assignment_id": "as-...", "delivered_to": 32}`

### 2.13 `GET /api/v1/teacher/assignments/{assignment_id}`
作业详情（含学生提交列表 + AI 批改建议）。

响应：
```json
{
  "id": "as-...",
  "status": "active",
  "submissions": [
    {"student_id": "stu-1000", "submitted_at": "...", "ai_score": 82, "teacher_score": null,
     "ai_suggest": "代码题接近 0 分，建议复核"}
  ],
  "auto_grade_summary": {"accepted": 17, "need_review": 3}
}
```

---

## 3. 科研导师能力（`research_mentor` / `hybrid`）

### 3.1 `GET /api/v1/teacher/research/projects`
项目列表。

响应：`{"items": [{"id": "rp-001", "name": "...", "student_id": "stu-1000", "stage": "experiment", "progress": 0.62, "literature_count": 36, "topic_candidates": [...]}]}`

### 3.2 `POST /api/v1/teacher/research/topics/generate`
触发选题候选生成（长任务）。

Request：`{"project_id": "rp-001", "count": 4, "preferences": "..."}`
Response: `{"task_id": "..."}`

SSE 事件链：
1. `progress` — 加载学生 persona
2. `evidence` — `rag.retrieve(domain=research)` 命中文献
3. `progress` — `topic_explorer.GenerateTopic`
4. `artifact` — 候选选题列表写入 `generated_resources (type=topic)`
5. `trace` — 落 agent_runs
6. `done` — `{topic_ids: [...], titles: [...]}`

---

## 4. 就业导师能力（`career_mentor` / `hybrid`）

### 4.1 `GET /api/v1/teacher/career/conversations`
咨询会话列表。Query：`status?`

响应：`{"items": [{"id": "cs-1", "student_id": "stu-1000", "topic": "求职方向", "status": "in_progress", "readiness": 0.62, "last_message_at": "..."}]}`

### 4.2 `POST /api/v1/teacher/career/insights`
发布行业洞察。

Request：`{"title": "...", "body_md": "...", "tags": ["甲方安全", "金融"]}`
Response: `{"insight_id": "in-...", "publish_at": "..."}`

### 4.3 `POST /api/v1/teacher/career/jobs/recommend`
触发岗位推荐（长任务）。

Request：`{"student_id": "stu-1000", "consultation_id": "cs-1", "count": 5}`
Response: `{"task_id": "..."}`

SSE 事件链：
1. `progress` — `job_analyst.SkillGapAnalysis`
2. `evidence` — `rag.retrieve(domain=jobs)`
3. `progress` — `job_analyst.RecommendJobs`
4. `artifact` — 推荐结果写入 `generated_resources (type=job_recommendation)`
5. `done` — `{recommendations: [{title, city, salary, match_score}]}`

---

## 5. 数据落地约束（与 CLAUDE.md §8 数据层 v2 对齐）

- 教材上传：写入 `documents` + `document_assets` + 异步切 `chunks`
- 题目生成：写入 `quiz_items`，`status` 初始为 `pending`
- 题目审核：仅更新 `status` + `reviewed_by` + `reviewed_at`，不会移动数据
- 作业发布：写入 `learning_tasks`（P1 表），关联 `quiz_items`，按学生展开 `quiz_attempts` 占位
- 选题发布：写入 `generated_resources (type=topic)`，关联 `chunks` 通过 `evidence_chunk_ids[]`
- 推荐岗位：写入 `generated_resources (type=job_recommendation)`
- 公告：写入 `agent_messages`（P1 表），channel = `notice`
- 所有触发智能体的端点均通过 `agent_runs` 落地，且必须经过 `outcome_evaluator.quality_check`（CLAUDE.md §2.6）

## 6. 与现有契约的对照

| 端点 | 与 `course-contract` 的差异 |
|---|---|
| GET /teacher/dashboard | KPI 维度不同（学生侧关心进度，教师侧关心审核 / 批改） |
| POST /teacher/quiz-bank/generate | 学生侧学习时 `generated_resources` 是私有产物；教师生成的题目落 `quiz_items` 进入题库审核流 |
| POST /teacher/assignments | 学生侧 `learning_tasks` 由 task_orchestrator 自动生成；教师手动布置时 `source = teacher` |
| POST /teacher/career/jobs/recommend | 与学生侧的"求职准备度" SSE 共用 job_analyst，但教师端关心多学生横向比较 |
| 上传教材 | 学生侧无此能力；teacher 端是唯一入口 |

## 7. 状态约定

| 端点 | 实现状态 |
|---|---|
| §1 通用 5 个 | planned |
| §2 课程教师 13 个 | planned（mock 已具备） |
| §3 科研导师 2 个 | planned |
| §4 就业导师 3 个 | planned |
| 合计 23 个 | 全部 planned，无 real |

后端实现优先级建议（由成员 A 评估后排期）：
1. P0：§1.1 / §1.2 / §2.6 / §2.11 —— 演示能跑通"我是谁 + 总览 + 题库 + 作业"
2. P1：§2.4 / §2.7 / §2.12 —— 教材上传 + 题目生成 + 作业布置的智能体链路
3. P2：§3.x / §4.x —— 科研 / 就业导师能力

---

## 8. 4-B-3 产品化升级新增端点

> 由 4-B-3 引入。所有端点状态 = `planned`，mock fallback 在 `frontend/src/lib/mock/persona.mock.ts`、`resource-production.mock.ts`、`assessment-product.mock.ts`、`learning-path.mock.ts`。

### 8.1 `GET /api/v1/teacher/class/clusters`
班级画像聚类（气泡图数据）。

Query：`class_id? · course_id?`

Response：
```json
{
  "clusters": [
    {
      "id": "cluster-case-driven",
      "label": "案例驱动型",
      "student_count": 18,
      "axis_x": 0.55,
      "axis_y": 0.72,
      "dominant_dimension": "cognitive_style",
      "student_ids": ["stu-1000"],
      "color": "#2563eb"
    }
  ]
}
```

触发的 agent skill：`career_planner.ClusterPersonas`。

### 8.2 `POST /api/v1/teacher/persona/dimensions`
教师自定义画像维度。

Request：
```json
{
  "course_id": "uuid",
  "key": "research_interest",
  "label": "科研兴趣",
  "description": "...",
  "challenges": [
    {"prompt": "...", "expected_keywords": ["..."]}
  ]
}
```

Response：`{"dimension_id": "uuid"}`

### 8.3 `POST /api/v1/teacher/courses/{course_id}/seed-prompt`
课程级资源生成偏好（种子提示）。

Request：
```json
{
  "body": "## 本课程生成偏好\n- 风格：侧重红队思维\n...",
  "tone_tags": ["红队思维", "案例驱动"]
}
```

Response：`{"updated_at": "..."}`

数据落地：写 `courses.metadata.seed_prompt`（jsonb）。

### 8.4 `POST /api/v1/teacher/resources/{resource_id}/approve`
教师批准学生生成的优质资源。

Request：`{}`

Response：`{"status": "approved", "approver": "teacher-wang", "approved_at": "..."}`

数据落地：在 `generated_resources.metadata.approval` 写入；学生侧资源工作台顶部展示"教师推荐"badge。

### 8.5 `POST /api/v1/teacher/students/{student_id}/path/insert`
路径介入：为学生在路径中插入必修节点。

Request：
```json
{
  "node_label": "周五前完成 XX 实验",
  "reason": "班级统一作业 | 临考冲刺 | 导师重点关注 | 基础查漏",
  "due_at": "2026-06-21T15:59:00Z"
}
```

Response：`{"insertion_id": "uuid", "delivered": true}`

触发的 agent skill：`task_orchestrator.InsertTeacherNode`；学生侧 toast 通知。

### 8.6 `GET /api/v1/teacher/class/health`
班级学习健康度。

Query：`class_id?`

Response：
```json
{
  "overall": 82,
  "classification": "healthy | attention | risk",
  "metrics": [
    {"key": "activity", "label": "活跃度", "score": 86}
  ],
  "trend": [{"recorded_at": "...", "score": 78}]
}
```

触发的 agent skill：`outcome_evaluator.ComputeClassHealth`。

### 8.7 `GET /api/v1/teacher/students/at-risk`
高风险学生预警。

Query：`class_id? · level?`

Response：
```json
{
  "items": [
    {
      "student_id": "stu-1018",
      "student_name": "李伟",
      "level": "high",
      "signals": [
        {"kind": "declining", "label": "评估连续下滑", "detail": "72 → 65 → 54"}
      ],
      "last_activity_at": "...",
      "suggested_action": "约 15 分钟一对一沟通"
    }
  ]
}
```

触发的 agent skill：`outcome_evaluator.IdentifyAtRiskStudents`。

### 8.8 `POST /api/v1/teacher/students/{student_id}/comment`
教师评语注入学生画像。

Request：
```json
{
  "body": "学习态度很好，建议在密码学上深入。",
  "dimension_tags": ["学习态度", "建议加深"],
  "visible_to_student": true
}
```

Response：`{"comment_id": "uuid", "persisted_dimension": "teacher_assessment"}`

数据落地：写 `user_profiles.teacher_assessment` JSONB 子字段；触发 `career_planner.RefreshPersona`。

---

## 9. 4-B-3 新增端点状态汇总

| 端点 | 实现状态 |
|---|---|
| §8.1 ~ §8.8 | 全部 planned，mock 已具备 |

后端实现优先级建议（由成员 A 评估）：
1. P0：§8.3 / §8.6 / §8.7 / §8.8 —— 教师"操控权 + 监督权"的关键
2. P1：§8.1 / §8.5 / §8.4
3. P2：§8.2

---

> 维护：本文件改动需要同时同步 `frontend/src/lib/mock/teacher.mock.ts` / `persona.mock.ts` / `resource-production.mock.ts` / `assessment-product.mock.ts` / `learning-path.mock.ts` 与 `frontend/src/app/features/teacher/`。
