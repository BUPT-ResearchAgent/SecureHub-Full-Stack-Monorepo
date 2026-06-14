# SecureHub Demo Storyboard v0 — "大二学生学 SQL 注入"
> Frozen: 2026-06-09。三人开发期间所有功能必须围绕本故事线。

## 0. 演示总目标
用演示账号 `demo_student_zhang` 跑通 A3 主线：对话式画像 → 个性化学习路径 → SQL 注入资源生成 → 智能辅导 → 学习评估与画像回流。所有生成内容必须带 evidence，所有 agent 调用必须进入 `agent_runs`。

## 1. 用户画像（演示账号 demo_student_zhang）
6 维 `dimensions` JSONB 示例：
```json
{
  "knowledge_base": "beginner",
  "learning_goal": "web_security",
  "style": "case_driven",
  "prior_courses": [],
  "language": "zh",
  "cognitive_load": "medium"
}
```

6 个 `user_capabilities` 行示例：
```json
[
  {"dimension": "web_security", "score": 0.35, "confidence": 0.60, "evidence_count": 0},
  {"dimension": "crypto", "score": 0.20, "confidence": 0.45, "evidence_count": 0},
  {"dimension": "reverse", "score": 0.18, "confidence": 0.40, "evidence_count": 0},
  {"dimension": "forensics", "score": 0.25, "confidence": 0.50, "evidence_count": 0},
  {"dimension": "mobile", "score": 0.15, "confidence": 0.35, "evidence_count": 0},
  {"dimension": "cloud_sec", "score": 0.22, "confidence": 0.42, "evidence_count": 0}
]
```

## 2. 故事 5 幕 + 时间轴（与 A3 §7.4 演示视频分镜对齐）
### 第一幕：画像构建
- 时长：0:00–0:45
- 前端 URL：`/course`
- 触发动作：学生输入“我学过一点 Python，想入门 Web 安全”
- 期望后端 endpoint：`POST /api/v1/profile/chat`
- 期望 SSE 事件顺序：`progress(validate)` → `token*` → `trace` → `done`
- 期望落库记录：`agent_runs` 记录 `career_planner.BuildLearningPersona`

### 第二幕：SQL 注入学习路径
- 时长：0:45–1:30
- 前端 URL：`/course`
- 触发动作：点击“生成学习路径”
- 期望后端 endpoint：`POST /api/v1/courses/{cid}/plan`
- 期望 SSE 事件顺序：非 SSE；页面随后查询 `GET /api/v1/agent-runs?workflow=course_learning&user_id=&limit=`
- 期望落库记录：`agent_runs` 记录 `task_orchestrator.GenerateLearningPath`

### 第三幕：生成 5+ 类资源
- 时长：1:30–4:30
- 前端 URL：`/course`
- 触发动作：依次生成 `doc` / `ppt` / `mindmap` / `quiz` / `lab` / `video`
- 期望后端 endpoint：`POST /api/v1/courses/{cid}/resources/generate?type=doc|ppt|mindmap|quiz|lab|video|readings`
- 期望 SSE 事件顺序：`progress(validate)` → `progress(retrieve)` → `evidence` → `progress(compose)` → `token*` → `progress(quality_check)` → `artifact` → `trace` → `done`
- 期望落库记录：每类资源各 1 条 `agent_runs`；成功生成的资源进入 `generated_resources`

### 第四幕：智能辅导
- 时长：4:30–5:30
- 前端 URL：`/course` 或 `/chat`
- 触发动作：学生追问“联合查询注入为什么要先判断列数？”
- 期望后端 endpoint：`POST /api/v1/tutor/ask`
- 期望 SSE 事件顺序：`progress` → `evidence` → `token*` → `trace` → `done`
- 期望落库记录：`agent_runs` 记录 `career_planner` 路由与被命中的回答 skill

### 第五幕：评估与画像回流
- 时长：5:30–6:30
- 前端 URL：`/course` → `/profile`
- 触发动作：提交 SQL 注入小测
- 期望后端 endpoint：`POST /api/v1/assessment/run`，随后 `GET /api/v1/profile/me`
- 期望 SSE 事件顺序：非 SSE
- 期望落库记录：`learning_events` 写入评估结果；`user_capabilities.web_security` 分数上升；`agent_runs` 记录 `outcome_evaluator.RunAssessment`

## 3. 验收阈值（不达标即不算本幕跑通）
- 评估 `quality_score` ≥ 0.7
- 每次生成 `evidence_chunk_ids` ≥ 3（rule §2.6）
- `agent_runs` 必有记录
- SSE 至少出现 `progress` / `evidence` / `done` 三种事件

## 4. 故事所需 seed 数据清单
- 1 user：`USER_DEMO_ID = "00000000-0000-0000-0000-000000000001"`，演示名 `demo_student_zhang`
- 1 course：`code = "course_websec_intro"`，`title = "Web 安全基础"`，`domain = "course_websec"`
- 3 knowledge_nodes：`SQL 注入基础` / `XSS 基础` / `CSRF 基础`
- 3 knowledge_edges：`SQL→XSS related_to` / `SQL→CSRF related_to` / `XSS→CSRF related_to`
- 1 document：`OWASP SQL Injection 摘要`，`platform = "owasp"`，`rights_note = "CC BY-SA 4.0"`
- 10 chunks：挂在 OWASP document 下，前 3 个 metadata 带 `kp_ids=[SQL_node_id]`
- 9 agents：固定 9 角色，不新增第 10 个
- 9 agent_skills：每个 agent 1 个核心占位 skill，`prompt_template = "[seeded placeholder]"`
- 1 user_profile：6 维 `dimensions`
- 6 user_capabilities：`web_security` / `crypto` / `reverse` / `forensics` / `mobile` / `cloud_sec`

## 5. 演示失败兜底方案
- 讯飞限流：成员 A 负责切到 `LLM_FALLBACK_CHAIN=deepseek,qwen,mock`；演示现场保留 mock 模式，但必须标注为 dev fallback。
- RAG 召回不足：成员 C 负责补 SQL 注入 chunks 或降低演示 query 的歧义；系统不得裸调 LLM，必须返回 `InsufficientEvidence`。
- 前端白屏：成员 B 负责保留本地 mock contract 渲染路径；若 SSE 中断，页面显示最近一次 `agent_runs` 与 `generated_resources` 快照。
