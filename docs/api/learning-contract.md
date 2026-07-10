# Learning API Contract（草案 · 4-B-3）

> 状态：**draft** — 由前端（成员 B）在 4-B-3 起草，后端实现由成员 A 在后续轮次完成。
> 当前所有端点均以 mock 数据驱动（`frontend/src/lib/mock/*.mock.ts`），后端落地后通过 `withMockFallback` 自然切换。
> 与 `docs/api/course-contract.md` 的边界：本契约只覆盖 4-B-3 引入的**产品化能力**端点
> （画像挑战 / 资源变体 / 路径多候选 / 隐式评估 / 病灶分析 / 效果预测），不重写学生侧基础端点。

## 0. 通用约定

- 所有路径前缀：`/api/v1`
- 所有响应：`application/json; charset=utf-8`
- 鉴权：`Authorization: Bearer <jwt>`
- 错误模型：复用 `course-contract.md §0`
- 长任务（生成 / 重规划）：返回 `task_id`，订阅 `/api/v1/agents/runs/{task_id}/stream`

---

## 1. 画像产品化（5 端点）

### 1.1 `POST /api/v1/persona/challenge`
触发画像挑战。

Request：
```json
{
  "user_id": "uuid",
  "dimension": "weak_points",
  "claim_text": "我最容易混淆布尔盲注和时间盲注"
}
```

Response：
```json
{
  "question_id": "ch-sqli-1",
  "prompt": "在 SQL 注入中，union-based 和 boolean-based 适用场景有什么差别？",
  "expected_keywords": ["列数", "回显", "盲注"],
  "difficulty": "medium",
  "rationale": "验证学生是否真正区分回显型与盲注型注入。"
}
```

触发的 agent skill：`career_planner.GenerateChallenge`。Mock fallback：`personaChallengeBank` 查表。

### 1.2 `POST /api/v1/persona/challenge/{question_id}/evaluate`
评估挑战答案。

Request：`{"answer": "..."}`

Response：
```json
{
  "outcome": "accepted",
  "confidence_delta": 0.2,
  "matched_keywords": ["列数", "盲注"],
  "next_status": "verified"
}
```

触发的 agent skill：`outcome_evaluator.EvaluatePersonaClaim`。

### 1.3 `GET /api/v1/persona/narrative`
画像叙事段（80-120 字人物简介）。

Query：`user_id`

Response：
```json
{
  "text": "**小李同学**，安全初学者（25%），偏好 **案例驱动** 学习方式…",
  "highlights": ["小李同学", "案例驱动", "Web 安全基础"],
  "dimension_keys": ["base_knowledge", "preferred_modality", "target_direction"],
  "generated_at": "2026-06-15T20:00:00Z"
}
```

触发的 agent skill：`career_planner.GeneratePersonaNarrative`。

### 1.4 `GET /api/v1/persona/tree`
画像树（径向布局所需的节点和子节点）。

Query：`user_id`

Response：
```json
{
  "branches": [
    {
      "key": "base_knowledge",
      "label": "知识基础",
      "value": "了解 Python 与 HTTP 请求",
      "confidence": 0.78,
      "status": "verified",
      "evidence_message_ids": ["msg-001"],
      "children": [
        {"key": "base_knowledge.lang", "label": "语言基础", "confidence": 0.7, "status": "detected"}
      ]
    }
  ]
}
```

触发的 agent skill：`career_planner.AssemblePersonaTree`。

### 1.5 `POST /api/v1/persona/dimensions/custom`
教师注入自定义维度（B 端 → 共享给 A 端学生画像）。

Request：
```json
{
  "course_id": "uuid",
  "key": "research_interest",
  "label": "科研兴趣",
  "description": "判断学生是否对漏洞研究感兴趣",
  "challenges": [
    {"prompt": "你最有兴趣的研究方向？", "expected_keywords": ["有趣", "现象"]}
  ]
}
```

Response：`{"dimension_id": "uuid"}`

---

## 2. 资源生成产品化（4 端点）

### 2.1 `POST /api/v1/resources/variants`
生成三变体（深入版 / 浅显版 / 案例版）。

Request：
```json
{
  "course_id": "uuid",
  "user_id": "uuid",
  "kp_id": "uuid",
  "resource_type": "doc"
}
```

Response：
```json
{
  "variants": [
    {
      "id": "variant-doc-deep",
      "kind": "deep",
      "title": "《SQL 注入入门》· 深入版",
      "tagline": "原理 + 源码 + 案例",
      "estimate_minutes": 25,
      "highlights": ["SQL 解析视角", "SQLMap 源码"],
      "preferred_for": ["理论推演"],
      "evidence_chunk_ids": ["chunk-001"]
    }
  ]
}
```

触发的 agent skill：`doc_archivist.GenerateResourceVariants`。

### 2.2 `POST /api/v1/resources/iterate`
学生触发资源迭代。

Request：
```json
{
  "resource_id": "uuid",
  "prompt": "请加深，从攻击者视角讲",
  "user_id": "uuid"
}
```

Response：`{"task_id": "...", "expected_seconds": 8}`

SSE 事件链：复用 `course-contract §2`；新增 `artifact` payload 中的 `version: 2` 字段。

### 2.3 `GET /api/v1/resources/{resource_id}/replay`
资源溯源回放（7 步时间轴）。

Response：
```json
{
  "resource_id": "uuid",
  "resource_type": "doc",
  "started_at": "...",
  "finished_at": "...",
  "total_duration_ms": 6800,
  "steps": [
    {"id": "s1", "offset_ms": 0, "stage": "request", "agent": "career_planner", "skill": "RouteRequest", "summary": "...", "outcome": "success"},
    {"id": "s2", "offset_ms": 1200, "stage": "rag", "agent": "doc_archivist", "skill": "RetrieveChunks", "evidence_count": 3, "outcome": "success"}
  ]
}
```

触发的 agent skill：无（从 `agent_runs` 聚合）。

### 2.4 `GET /api/v1/resources/{resource_id}/debate`
智能体辩论历史（与 replay 配套）。

Response：
```json
{
  "topic": "DOC 资源质量复核",
  "version_from": "v1",
  "version_to": "v2",
  "exchanges": [
    {"id": "d1", "speaker_agent": "outcome_evaluator", "side": "challenger", "message": "...", "emitted_at": 0}
  ],
  "resolution": "质量分由 0.72 提升至 0.87",
  "diff": [{"type": "add", "text": "..."}]
}
```

---

## 3. 学习路径产品化（4 端点）

### 3.1 `GET /api/v1/learning/paths`
多候选学习路径。

Query：`course_id · user_id`

Response：
```json
{
  "candidates": [
    {
      "id": "path-sprint",
      "strategy": "sprint",
      "label": "快速通关",
      "description": "21 天每天 1 节点",
      "total_days": 21,
      "daily": "每天 1 节点 · 40-60 分钟",
      "highlights": ["21 天闭环"],
      "nodes": [
        {
          "id": "uuid",
          "label": "SQL 注入基础",
          "knowledge_point_id": "uuid",
          "status": "active",
          "difficulty": "easy",
          "prerequisite_mastery": 0.95,
          "importance": 0.9,
          "estimate_minutes": 40,
          "mentor_agent": "doc_archivist",
          "mentor_reason": "概念问题找文档解读员"
        }
      ],
      "edges": [{"id": "uuid", "source": "uuid", "target": "uuid"}]
    }
  ]
}
```

触发的 agent skill：`task_orchestrator.GenerateCandidatePaths`。

### 3.2 `POST /api/v1/learning/paths/{path_id}/select`
学生选定路径。

Request：`{"user_id": "uuid"}`

Response：`{"applied": true}`

### 3.3 `POST /api/v1/learning/paths/replan`
触发动态路径重规划（节点完成事件后由系统主动调用，也支持学生手动触发）。

Request：
```json
{
  "user_id": "uuid",
  "course_id": "uuid",
  "trigger": "over_perform | struggling | manual"
}
```

Response：
```json
{
  "replan_event": {
    "id": "uuid",
    "reason": "over_perform",
    "summary": "SQL 注入评估 92% · 耗时 58%",
    "added_node_ids": ["uuid"],
    "removed_node_ids": ["uuid"],
    "message": "AI 把后续节点加深，加入二阶注入与 WAF 绕过"
  }
}
```

触发的 agent skill：`task_orchestrator.ReplanPath`。

### 3.4 `GET /api/v1/learning/push-schedule`
资源推送时间轴。

Query：`user_id`

Response：
```json
{
  "slots": [
    {
      "id": "slot-1",
      "scheduled_at": "...",
      "bucket": "today",
      "bucket_label": "今晚 21:00",
      "resource_type": "doc",
      "title": "《SQL 注入基础》案例版",
      "agent": "doc_archivist",
      "rationale": "与你今天评估的 web_security 维度相关",
      "duration_minutes": 18,
      "status": "scheduled"
    }
  ]
}
```

`PATCH /api/v1/learning/push-schedule/{slot_id}` 用于学生调整 / 拒绝。

---

## 4. 学习效果评估产品化（4 端点）

### 4.1 `GET /api/v1/assessment/implicit`
隐式评估（基于行为信号）。

Query：`user_id · course_id`

Response：
```json
{
  "total_score": 0.78,
  "diff_from_explicit": 0.06,
  "signals": [
    {
      "kind": "question_depth",
      "label": "提问深度",
      "description": "...",
      "score": 0.84,
      "weight": 0.25,
      "evidence_labels": ["提问 ..."]
    }
  ]
}
```

触发的 agent skill：`outcome_evaluator.ComputeImplicitScore`。

### 4.2 `GET /api/v1/capability/timeline`
能力演变史。

Query：`user_id · dimension?`

Response：
```json
{
  "user_id": "uuid",
  "dimensions": ["web_security", "crypto"],
  "points": [
    {
      "recorded_at": "...",
      "dimensions": {"web_security": 0.62, "crypto": 0.31},
      "highlight_events": [
        {"title": "完成 SQL 注入实操", "description": "+8%", "dimension": "web_security", "delta": 0.08}
      ]
    }
  ]
}
```

触发的 agent skill：`outcome_evaluator.AssembleTimeline`。

### 4.3 `POST /api/v1/assessment/diagnose`
错题病灶分析。

Request：
```json
{
  "user_id": "uuid",
  "assessment_id": "uuid"
}
```

Response：
```json
{
  "generated_at": "...",
  "meta": {"incorrect_count": 5, "covered_dimensions": ["web_security"]},
  "root_causes": [
    {
      "id": "rc-1",
      "topic": "二阶注入概念混淆",
      "affected_item_ids": ["q-003", "q-007"],
      "evidence_snippet": "...",
      "suggested_resource": {"type": "doc", "title": "二阶注入篇", "agent": "doc_archivist"},
      "exercise_title": "二阶注入专项 5 题",
      "exercise_count": 5
    }
  ]
}
```

触发的 agent skill：`outcome_evaluator.RootCauseAnalysis`。

### 4.4 `GET /api/v1/assessment/forecast`
学习效果预测。

Query：`user_id · dimension · target_mastery?`

Response：
```json
{
  "dimension": "web_security",
  "dimension_label": "Web 安全主线",
  "target_mastery": 0.9,
  "expected_days": 12,
  "confidence_low_days": 9,
  "confidence_high_days": 15,
  "acceleration": {"extra_minutes_per_day": 30, "shaved_days": 3},
  "historical": [{"recorded_at": "...", "expected": 0.71}],
  "forecast": [{"recorded_at": "...", "expected": 0.78, "lower": 0.74, "upper": 0.83}]
}
```

触发的 agent skill：`career_planner.ForecastMastery`。

### 4.5 `GET /api/v1/peer/compare`
同伴对比。

Query：`user_id · course_id`

Response：
```json
{
  "overall_percentile": 0.7,
  "summary": "整体安全意识在班级前 30%",
  "dimensions": [
    {"dimension": "xss_defense", "label": "XSS 防护", "self_score": 0.78, "class_median": 0.62, "better_than_ratio": 0.8}
  ]
}
```

触发的 agent skill：`outcome_evaluator.AggregatePeer`。

---

## 5. 状态约定

| 端点组 | 实现状态 |
|---|---|
| §1 画像 5 个 | planned |
| §2 资源 4 个 | planned |
| §3 路径 4 个 | planned |
| §4 评估 5 个 | planned |
| 合计 18 个 | 全部 planned，无 real |

后端实现优先级（由成员 A 评估排期）：
1. P0：1.1 / 1.2 / 2.1 / 3.1 / 4.1 / 4.4 —— 演示主线必需
2. P1：1.3 / 1.4 / 2.2 / 2.3 / 3.3 / 3.4 / 4.2 / 4.3 / 4.5
3. P2：1.5 / 2.4

---

## 6. 数据落地约束（与 CLAUDE.md §8 数据层 v2 对齐）

- 画像挑战记录写 `agent_runs`（`skill_name=EvaluatePersonaClaim`）+ `user_capabilities.confidence` 字段更新
- 资源变体写 `generated_resources`（每个 variant 一条），共享 `evidence_chunk_ids[]`
- 资源迭代写 `resource_versions`（P1 表），关联 `generated_resources.id`
- 路径重规划事件写 `learning_paths.replan_events`（P1 表 jsonb 字段）
- 隐式评估信号写 `learning_events`（type=implicit_signal）
- 能力时间轴查询从 `user_capabilities` + `learning_events` 聚合
- 病灶分析写 `agent_runs`（`outcome_evaluator.RootCauseAnalysis`），结果存 `generated_resources (type=diagnosis_report)`
- 教师评语写 `user_profiles.teacher_assessment` JSONB 子字段
- 教师种子提示写 `courses.metadata.seed_prompt`

---

> 维护：本文件改动需要同时同步 `frontend/src/lib/mock/*-product.mock.ts` 与 `frontend/src/app/features/`。
