# Agent-Run-2 交付报告

## 1. 本轮目标与 Agent-Run-1 前置状态

- 当前分支为 `dev`；Agent-Run-1 已先独立固化为 `f17cef49 feat(agent-run): add fixed workflow run api`。
- 本轮将同一固定五节点 `course_learning_minimal` 从 fixture 控制面扩展为受控 strict real 路径，不新增 agent、数据库迁移、Redis 或前端改动。
- 开工要求中的 `Prompt\Agent-Run-2.md` 在工作区及上级目录均未找到；实现以任务说明、既有 Agent-Run-1 报告和权威约束为准。

## 2. 实现摘要与文件清单

- `backend/app/runtime/run_registry.py` 改为有界 history、私有订阅 queue 和 fan-out；事件具备单调 `event_id`、TTL 清理和游标重放。
- `backend/app/streaming/agent_events.py` 在 SSE `id:` 与 payload 中输出同一 `event_id`。
- `backend/app/runtime/harness/live_adapters.py` 新增 strict RAG、DeepSeek、JSON 和 `agent_runs` 持久化适配器。
- `backend/app/runtime/workflows/course_learning_minimal.py` 保持固定节点顺序，分离 fixture 与 strict real 执行路径。
- `backend/app/services/agent_control_service.py` 启用 gated `mode=real, provider=deepseek`、并发限制和实际 model 标记；`backend/app/api/v1/endpoints/agent_control.py` 支持 `Last-Event-ID` / `after_event_id`。
- `backend/app/services/agent/agent_run_service.py` 支持调用方指定 child run ID，并在 strict 模式验证 user、agent、skill 的真实解析。
- `backend/app/core/config.py` 与 `backend/.env.example` 增加非密钥 real-mode、并发、token、history 和 TTL 配置说明。

## 3. strict RAG / DeepSeek / JSON 输出策略

- real 路径直接调用 `app.rag.retriever.retrieve()`；少于 3 条证据时 blocked 为 `INSUFFICIENT_EVIDENCE`，不会注入 fixture evidence。
- 仅接受 `get_llm_provider("deepseek")` 构造出的 `provider_name=deepseek`；开发环境的 fixture fallback 会被拒绝为 `PROVIDER_UNAVAILABLE`。
- DeepSeek 强制 JSON-only；无效 JSON 或 schema 不匹配为 `LLM_OUTPUT_INVALID`，无字段填充或 fixture 回退。
- Harness 将真实检索的 `evidence_chunk_ids` 覆盖模型自报值；real stream 逐 token 检查取消。

## 4. agent_runs 关联与 DB 证据

- 每个 strict child 预分配 UUID；Harness 使用该 UUID 调用 `ctx.log_run(...)`，SSE `trace.agent_run_id` 与持久化主键相同。
- 持久化前写入 `input_summary.workflow_run_id`；strict logger 解析并验证已 seed 的 user、agent、agent_skill，失败为 `AGENT_RUN_PERSIST_FAILED`，root run 不会成功。
- 自动化 SQLite seed 验证已确认调用方 run ID、非空 agent/skill ID、workflow root ID 与 evidence chain 能写入 `agent_runs`。
- 未新增 `workflow_runs` 表、Alembic migration 或 smoke 数据清理。

## 5. SSE fan-out / replay 与取消语义

- 支持两个并发订阅者接收同一 `progress / trace / done` 序列；已完成 run 仍可从 retained history 重放。
- `Last-Event-ID` 或 `after_event_id` 只重放严格更大的事件；两者同时给出时必须相同。
- history 默认上限为 2048，终态无订阅 run 在后续 registry cleanup 时按 3600 秒 TTL 惰性清理；单进程重启不恢复。
- cancel 是合作式：当前 node 标记 `cancelled`、未开始 node 标记 `skipped`，取消时刻后不转发 `token` 或 `artifact`；当前版本未持久化资源，正确地不发送 artifact。

## 6. 测试命令、结果与覆盖缺口

```powershell
cd backend
uv run pytest tests/api/test_agent_control.py tests/runtime/test_course_learning_minimal.py tests/test_api_smoke.py tests/runtime/test_skill_harness.py tests/streaming/test_sse_events.py -q
```

- 结果：`38 passed in 6.10s`。
- 新增覆盖：九 agent manifest、fixture 标签、SSE 双订阅/重放、`Last-Event-ID`、real 202 fake-provider 入口、strict evidence floor、provider/JSON 无 fallback、child UUID/DB logger 对齐，以及 streaming cancel 后无 token/artifact。
- CI 默认只使用 fixture / fake DeepSeek provider；没有将真实模型调用加入自动化测试。

## 7. live smoke（是否执行、次数、provider/model/mode/status）

- 实际 DeepSeek 调用次数：`0`。
- 安全预检：`provider=deepseek`、`model=deepseek-v4-pro`、`mode=real`、`status=preflight-db-unavailable`。
- server-side `AGENT_RUN_REAL_ENABLED=false`，且本地数据库预检不可用，未满足 real smoke 前置条件；因此没有创建真实 run、没有查询到真实 smoke 的 `agent_runs` 行，也没有伪造通过。
- 本地 DeepSeek 配置字段可用，但没有回显、记录或提交任何 secret。

## 8. 未完成风险、回滚与 Agent-Run-3 准入建议

- 风险：单进程 registry 无重启恢复；SSE history 有上限；远端 HTTP 已发起时只能停止消费和转发，不能强杀线程。
- 回滚：保持 `AGENT_RUN_REAL_ENABLED=false`，或回滚本轮 strict real commit；fixture API 保持可用且不触碰 Agent-Run-1 提交。
- Agent-Run-3 前先恢复本地 Postgres，确认 demo user、9 agents、agent_skills 和至少 3 条 `course_websec` ready chunks，再以显式 gate 执行最多一次 real smoke，并按 root `workflow_run_id` 核对 5 条 `agent_runs`。
