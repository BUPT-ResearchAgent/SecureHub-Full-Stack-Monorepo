---
name: securehub-pr-review
description: 用于 SecureHub PR Review 的 Codex 子智能体调度指南。默认只用 review_qa；涉及架构 / DB / Harness / RAG 时追加 planner。
---

# SecureHub PR Review Skill

> 这是一份指令型 skill（instruction-only），不增加 agent 数量。
> 它告诉调度方在做"PR 审查"时应该按什么模式调用 Codex 子智能体。

---

## 1. 适用场景

- 团队成员提交 PR 后的自动化 / 半自动化 review
- 合并前的契约 / 测试 / 回归风险检查
- Pre-merge 健康检查

---

## 2. 默认调度

```
[1] securehub_review_qa（只读）
     └─ 输出：Blocker / Major / Minor / Tests to run / Docs to update / Decision
```

**默认只调用 review_qa**。不默认调 planner / worker / docs_delivery。

---

## 3. 升级调度（按需）

当 PR 涉及以下任一情况时，追加 `securehub_planner`：

- 9 业务智能体边界变化（新增 skill / 改 agent_name / 改调用图）
- DB schema 变更（migrations / models 改动）
- Harness 契约变化（SkillContract 字段 / 执行链阶段）
- RAG 检索策略变化（reranker / evidence_floor / domain 过滤）
- 横切基础设施改造（rag / guardrails / storage / harness / router）
- API 契约破坏性变更（删除字段 / 改字段类型 / 改 endpoint path）

升级后调度：

```
[1] securehub_review_qa（只读，常规审查）
[2] securehub_planner（只读，架构级复核）
```

两者并行运行，最终由人工合并意见。

---

## 4. review_qa 调用 prompt 模板

```text
请只读审查当前分支相对 dev 的改动，输出标准 PR Review 报告：

Blocker（合并阻塞）：
- 列出必须修复才能合并的问题

Major（合并前应修）：
- 列出强烈建议修复的问题

Minor（合并后可改）：
- 列出可选优化项

契约一致性检查：
- API path / method / request / response schema
- SSE 7 事件 progress/evidence/token/artifact/trace/done/error
- 前端是否通过 VITE_API_BASE_URL + lib/api.ts
- 后端新增文件是否有 # Status 注释
- 生成式 skill 是否绑定 evidence_chunk_ids + agent_runs
- 是否违反 9 业务智能体固定规则
- 是否裸调 LLM 绕开 RAG / Harness

Tests to run:
- 列出建议执行的测试命令

Docs to update:
- 列出建议同步更新的文档

Decision: merge / continue / hold
- 给出明确决策

不修改任何代码。
```

## 5. planner 追加调用 prompt 模板（仅升级时）

```text
本 PR 涉及 [架构 / DB / Harness / RAG] 级变更。
请从架构师角度只读复核：
- 改动是否破坏 9 业务智能体边界
- 是否破坏统一知识资产层
- 是否影响 evidence_floor / quality_check 三道闸
- 是否需要同步更新 CLAUDE.md / .codex/AGENTS.md
- 是否需要分多个 PR
- 是否影响下游 worker 的开发计划

输出：架构级风险清单 + 是否建议合并 / 拆 PR / 回退。
不修改任何代码。
```

---

## 6. 额度友好提示

- 单纯文档 PR（README / 注释 / changelog）**不需要**本 skill；直接人工 review
- 单元测试 PR 也通常不需要 planner
- 频繁触发 review_qa 比偶尔触发 planner+review_qa 便宜
- 不要把 review_qa 当作"找 bug agent"——它是契约审查，找 bug 是开发自己的责任

---

## 7. 不允许的事

- 不允许在 review 阶段让 review_qa 进入 write 模式（它是只读的）
- 不允许默认调用 worker（worker 是开发派的，不是 review 派的）
- 不允许跳过 review_qa 直接合并到 dev（破坏分支保护策略）

---

## 8. 引用

- 调度细则：`.codex/workflows/subagent-playbook.md` Workflow 4
- review_qa 配置：`.codex/agents/securehub_review_qa.toml`
- 项目宪法：`CLAUDE.md`
