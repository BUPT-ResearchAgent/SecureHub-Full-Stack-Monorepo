---
name: securehub-vertical-slice
description: 用于 A3 课程学习垂直切片开发的 Codex 子智能体调度指南。仅在复杂垂直切片才调用 planner，默认 worker + review_qa 即可。
---

# SecureHub Vertical Slice Skill

> 这是一份指令型 skill（instruction-only），不增加 agent 数量。
> 它告诉调度方在做"A3 课程学习垂直切片"时应该按什么顺序、什么模式调用 Codex 子智能体。

---

## 1. 适用场景

满足以下任一条件即视为"垂直切片"：

- 一次性涉及 backend service + frontend page + DTO/schema 改动
- 涉及新增 SSE 事件 / 新 endpoint / 新 mock 数据
- 涉及 9 业务智能体中某个 skill 的新增或修改
- 涉及 generated_resources / storage_objects / agent_runs 表的写入路径

不满足以上场景的小修复（单文件单点改动）**不要使用本 skill**，直接派单个 worker 即可。

---

## 2. 标准调度顺序

```
[1] securehub_planner（只读）
     └─ 输出：任务边界 / 文件候选 / API/DB/RAG/Harness/前端影响 / Done when / 建议 worker

[2a] securehub_backend_rag_worker（write）  ─┐
                                              ├─ 并行（不改同一文件）
[2b] securehub_frontend_worker（write）     ─┘

[3] securehub_review_qa（只读）
     └─ 输出：Blocker / Major / Minor / Tests to run / Docs to update / 合并决策
```

**不默认启动** `securehub_docs_delivery`。仅当本次切片明确需要更新交付文档（README / docs/api/*-contract.md changelog）时才追加。

---

## 3. 子智能体调用模板

### 调用 planner 的 prompt

```text
请只读分析以下垂直切片任务，输出 backend / frontend / DTO / SSE / RAG / Harness 影响清单 + Done when + 建议调用哪些 worker。
不要修改任何代码。

任务描述：<填写>

约束：
- 不新增第 10 个 SecureHub 产品运行时业务智能体
- 不修改 backend/app/agents/ 以外的 agent 注册逻辑
- 9 业务智能体清单固定
```

### 调用 worker（并行）的 prompt

```text
按 planner 输出的边界实现 backend / frontend 部分。

backend_rag_worker 负责：
  <填写文件清单>

frontend_worker 负责：
  <填写文件清单>

约束：
- 两个 worker 不得修改同一文件范围
- backend 不动 frontend，frontend 不动 backend
- 生成式 skill 必须走 Harness，不裸调 LLM
- 新增 endpoint / schema 文件顶部 # Status 注释
- 用户可见文案中文
```

### 调用 review_qa 的 prompt

```text
请只读审查上述 worker 改动，输出：
- Blocker / Major / Minor
- API path / method / request / response schema 一致性
- SSE 7 事件 progress/evidence/token/artifact/trace/done/error 是否覆盖
- 前端是否通过 VITE_API_BASE_URL + lib/api.ts 调用
- 后端新增文件是否有 Status 标注
- 生成式 skill 是否绑定 evidence_chunk_ids + agent_runs
- 是否违反 9 业务智能体固定规则
- 建议 Tests to run / Docs to update
- 最终 Decision: merge / continue / hold
```

---

## 4. 额度友好提示

- 单 worker 任务（如只改 frontend）**不要**用本 skill；直接派 `securehub_frontend_worker`。
- 涉及架构 / DB schema / Harness 变化时**必须**先 planner 再 worker，避免 worker 走偏后大量返工。
- review_qa 是只读，可在 worker 完成后单独触发，**不要**在 worker 进行中并发触发。
- `max_depth = 1`：worker 内部不再 spawn 新 agent。

---

## 5. 不允许的事

- 不要在切片开发中新增第 10 个 SecureHub 产品运行时业务智能体（铁律）
- 不要让 worker 同时改 `backend/app/db/models/` 和业务代码（schema 变更走单独 PR）
- 不要默认派 docs_delivery；保留它仅在文档专项任务

---

## 6. 引用

- 调度细则：`.codex/workflows/subagent-playbook.md` Workflow 3
- 任务计划模板：`.codex/templates/subagent-task-plan.md`
- 项目宪法：`CLAUDE.md`
