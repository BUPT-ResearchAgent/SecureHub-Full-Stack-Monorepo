# Agent-Run-2.1 交付报告

## 1. P1 质量闸门反例与修复

- 反例使用 fake DeepSeek 让第五个 `QualityCheck` 输出 `accept=false`。修复前根 workflow 错误地进入 `succeeded`，反例测试已确认该失败状态。
- 修复后根 workflow 进入 `blocked`，返回 `error.code=QUALITY_REJECTED` 并发送 terminal `error`；不会发送 `done.status=succeeded`。
- `QualityCheck` child 已正确执行时仍保留其 success trace 和 `agent_runs` 语义。其业务拒绝不被伪装成 provider、RAG、JSON 或持久化异常。

## 2. real preflight 行为与错误码

- `AgentRunService.ensure_real_workflow_prerequisites(...)` 统一验证 user UUID、users 行和五个固定 agent/skill seed 对。
- `mode=real, provider=deepseek` 在构造 provider 与创建 run 前执行 preflight。
- 非 UUID user 返回 `422 INVALID_USER_ID`；数据库不可用、用户缺失或 agent skill seed 缺失返回 `503 REAL_PREREQUISITES_UNAVAILABLE`。
- fake provider 计数测试证明上述失败路径均为 0 次 provider 调用且不创建 run；完整 seeded SQLite 允许请求进入既有启动路径。

## 3. 完整 SQLite persistence 集成证据

- 集成测试使用 fake strict DeepSeek、fake strict RAG、seeded SQLite 和实际 `persist_strict_agent_run`，通过 monkeypatch 将生产 sessionmaker 定向到测试数据库。
- 完成后准确查询到 5 条 `agent_runs`：child UUID 与 SSE trace 一致，所有 `input_summary.workflow_run_id` 等于 root UUID，user/agent/skill 外键均非空，evidence IDs 与 strict retriever 测试 UUID 一致。
- persistence adapter 抛错时根状态为 `failed`、code 为 `AGENT_RUN_PERSIST_FAILED`，不会生成 success done。

## 4. 测试命令与结果

```powershell
cd backend
uv run pytest tests/api/test_agent_control.py tests/runtime/test_course_learning_minimal.py tests/test_api_smoke.py tests/runtime/test_skill_harness.py tests/streaming/test_sse_events.py -q
uv run ruff check app/runtime/harness/live_adapters.py app/runtime/workflows/course_learning_minimal.py app/services/agent_control_service.py app/services/agent/agent_run_service.py tests/api/test_agent_control.py tests/runtime/test_course_learning_minimal.py
```

- pytest 结果：`43 passed in 6.90s`。
- ruff 结果：未执行，当前 uv 环境无法启动 `ruff`（`program not found`）；未新增依赖，改以 Python 编译和 `git diff --check` 补充验证。
- 本轮自动化测试继续使用 fixture / fake provider；不包含真实 DeepSeek 调用。

## 5. DeepSeek / DB live smoke 状态（本轮应为 0 次）

- 实际 DeepSeek 调用次数：`0`。
- 未改动 `.env.local`，未回显或记录任何 secret。
- 本轮只验证 fake provider 与 SQLite；没有发起 real DB/DeepSeek live smoke。

## 6. 回滚与 Agent-Run-3 准入结论

- 回滚本轮单一 fix commit 即可恢复 Agent-Run-2 行为；保持 `AGENT_RUN_REAL_ENABLED=false` 不变。
- Agent-Run-3 前置：质量拒绝、real preflight、五条真实 `agent_runs` SQLite 集成均需保持绿灯；恢复本地 Postgres 与真实 evidence 后再评估一次受控 live smoke。
