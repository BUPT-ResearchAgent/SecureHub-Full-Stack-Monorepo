---
name: securehub-contract-check
description: 用于 API / schema / SSE / RAG evidence / agent_runs / generated_resources / storage_objects 契约的专项检查指南。默认由 review_qa 执行。
---

# SecureHub Contract Check Skill

> 这是一份指令型 skill（instruction-only），不增加 agent 数量。
> 它告诉调度方在做"契约专项检查"时应该按什么清单调用 Codex 子智能体（默认 review_qa）。

---

## 1. 适用场景

- 跨成员（A / B / C）联调前的契约对齐自检
- DTO 字段冻结前的工作坊配套审查
- 真后端联调时发现字段不一致后的回溯检查
- 单纯查 contract，不涉及 PR Review 完整流程

---

## 2. 默认调度

```
[1] securehub_review_qa（只读）
     └─ 输出：契约一致性报告（按下述 6 类检查）
```

不调 planner / worker / docs_delivery。

---

## 3. 6 类必检契约

### 3.1 REST API path / method 一致性

对照 `docs/api/course-contract.md`、`docs/api/learning-contract.md`、`docs/api/teacher-contract.md`：

- 检查 backend/app/api/v1/endpoints/ 下每个 endpoint 与文档 path / method 是否 1:1
- 检查 frontend/src/lib/api.ts 与 features/*/api.ts 调用的 path / method 是否与契约 1:1
- 检查端点 query / body 参数是否齐全
- 检查 endpoint 文件顶部 # Status 注释是否存在

### 3.2 Request / Response schema 一致性

- 检查 backend/app/schemas/ 下 Pydantic 模型字段
- 检查 frontend/src/lib/api-types.ts（或 sse.types.ts）TypeScript interface
- 字段类型 1:1（int vs string vs UUID）
- 必填 / 可选 1:1
- 嵌套对象 1:1

### 3.3 SSE 7 事件契约

事件类型必须严格匹配：

```
progress / evidence / token / artifact / trace / done / error
```

每类事件检查：

- 事件名拼写
- payload 字段
- 触发时机
- 前端消费者是否齐全
- error.code 取值是否在约定枚举内（InsufficientEvidence / sse_reconnecting / BudgetExceeded / LLMProviderError / SkillTimeout / RateLimited / QualityCheckFailed / InternalError）

### 3.4 Evidence DTO 字段

参考 `Plan/SecureHub_三人工程化分工与真实LLM接入规划.md` §17.0 EvidenceDTO 工作坊：

必填集：
- `chunk_id` / `document_id` / `chunk_text` 或 `excerpt` / `score` 或 `reliability`

来源标识必填集：
- `platform` / `source_url`（manual 来源可空）/ `rights_note`

可选展示集：
- `title` / `author` / `published_at` / `fetched_at` / `collection_mode` / `asset_type` / `page_no` / `chapter` / `timestamp` / `license`

检查前后端字段名一致 + 是否所有字段都有对应的 mock / 真采集来源。

### 3.5 agent_runs 与 generated_resources 落库

每个生成式 skill 执行后，agent_runs 必须记录：

- `agent_name` / `skill_name` / `status` / `duration_ms` / `quality_score`
- 真 LLM 接入后：`provider` / `model` / `token_usage` / `cost_estimate`
- `evidence_chunk_ids[]`（非空）
- `parent_run_id`（若为子调用）

生成物必须写入 `generated_resources`：

- `resource_type` 枚举对齐 `docs/data-layer-v2-enums.md §8.1`
- 关联 `storage_objects.object_key`（大文件）
- `evidence_chunk_ids[]` 非空

### 3.6 9 业务智能体边界

检查：

- `backend/app/agents/` 下目录数 ≤ 9
- `agents` 表 seed 数据条数 ≤ 9
- 不出现：`crawler_agent` / `media_agent` / `spider_agent` / `pdf_agent` / `mineru_agent` / `harness_agent` / `storage_agent`
- 不出现：`backend/app/services/knowledge/*.py` 注册成 agent

---

## 4. review_qa 调用 prompt 模板

```text
请只读做 6 类契约专项检查：

1. REST API path/method 一致性（前后端 vs docs/api/*-contract.md）
2. Request/Response schema 一致性（Pydantic vs TS interface）
3. SSE 7 事件契约（progress/evidence/token/artifact/trace/done/error + error.code 枚举）
4. EvidenceDTO 字段（最小必填 / 来源标识 / 可选展示三层）
5. agent_runs + generated_resources 落库字段
6. 9 业务智能体边界（agents 目录数 / 不出现 crawler_agent 等）

输出格式：
[Pass] 类别 X：通过
[Warn] 类别 X：字段 Y 在 backend 有，frontend 缺（影响：...）
[Fail] 类别 X：endpoint Z 与契约不一致（具体：...）

最后给出：
- 总体决策：契约可用 / 需修复 / 需重新工作坊
- 推荐修复 owner（A / B / C）
- 推荐修复 PR 拆分建议

不修改任何代码。
```

---

## 5. 额度友好提示

- 契约检查是高 ROI 任务：1 次检查可避免后续多次联调失败
- review_qa 一次跑完 6 类即可，不要分 6 次跑
- 不要默认升级到 planner（契约不一致是 worker 的责任，不是架构问题）
- 大型契约工作坊（如 EvidenceDTO 工作坊）执行后必须跑本 skill 验收

---

## 6. 不允许的事

- 不允许在契约检查中修改代码（review_qa 只读）
- 不允许跳过 docs/api/*-contract.md 直接用代码作为契约权威（契约文档优先）
- 不允许把契约检查混进 PR Review（单独跑，避免 review 报告过载）

---

## 7. 引用

- 契约文档：`docs/api/course-contract.md` / `learning-contract.md` / `teacher-contract.md`
- EvidenceDTO 工作坊：`Plan/SecureHub_三人工程化分工与真实LLM接入规划.md` §17.0
- 数据层 enum：`docs/data-layer-v2-enums.md`
- review_qa 配置：`.codex/agents/securehub_review_qa.toml`
- 项目宪法：`CLAUDE.md`
