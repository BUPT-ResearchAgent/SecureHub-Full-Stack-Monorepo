# Subagent Task Plan Template

> 用法：在派发 Codex 子智能体执行任务前，填写以下字段，避免子智能体跨边界、超额度、漏验收。
> 这是「开发辅助 Codex 子智能体」的任务计划模板，**不是** SecureHub 产品运行时业务智能体的任务调度。

---

## Goal

一句话写清本任务想达到的可观察结果。
示例：让 `/course?view=chat` 在真后端不可达时静默降级到 mock，并保留 token 流式渲染。

## Context

- 触发原因：（用户反馈 / Bug / 新需求 / 演示前打磨）
- 上游依赖：（A 完成 X / C 提供 Y）
- 相关历史：（指向 Workout/N-X-Y.md 或 Plan/* 文档）

## Budget mode: low / normal / high

- **low**：只调用 1 个 worker（如 frontend_worker），不调 planner、不默认调 review_qa
- **normal**：1 个 worker + review_qa 收尾
- **high**：planner → worker(s) → review_qa（仅复杂垂直切片或架构变更使用）

## Constraints

- 不新增第 10 个 SecureHub 产品运行时业务智能体（铁律）
- 不修改 `backend/app/agents/` 业务智能体代码（除非父任务明确要求）
- 不引入新 npm / pip 依赖（除非父任务明确要求）
- 文件顶部 `# Status: real|mock|partial-real|planned` 注释保留
- 用户可见文案全中文
- 其他：（按本任务追加）

## Files likely involved

- 必改：`<path>` / `<path>`
- 可能改：`<path>`
- 只读引用：`<path>`

## Subagents to spawn

- `securehub_<agent_name>`（理由：……）

## Subagents NOT to spawn

- 明确写出不调用的 agent + 理由（避免主调度误派）。
  示例：不调用 `securehub_planner`，因为本任务范围在单页面前端修复，无架构边界变更。

## Contract impact

- API：（无 / 新增 / 修改 path / 修改 schema）
- SSE 事件：（无 / 新增事件 / 修改 payload）
- DB schema：（无 / 新增字段 / 改 enum）
- 上下游契约文档需同步更新：（无 / docs/api/*-contract.md / docs/data-layer-v2-enums.md）

## Tests to run

- `cd backend && uv run pytest -m "not llm_live"`
- `cd frontend && pnpm typecheck && pnpm build`
- 其他 smoke：（如有）

## Done when

- 可度量的验收点列出来：
  - [ ] `<endpoint>` 真后端可达时返回真实数据
  - [ ] `<endpoint>` 真后端不可达时自动降级 mock，console.warn 但不阻塞
  - [ ] `pnpm build` 最大 chunk gzip ≤ 300 kB
  - [ ] git log 本轮新 commit 全部落 dev

## Risks

- 风险 1：（描述 + 应对）
- 风险 2：（描述 + 应对）
- 已知阻塞：（如需要 A/C 配合的事项）

---

> 模板版本：v1.0
> 维护：本模板改动需要同时同步 `.codex/workflows/subagent-playbook.md`。
