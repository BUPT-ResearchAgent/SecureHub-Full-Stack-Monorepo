# Agent-Run-1 交付报告

## 1. 本轮目标

完成固定多智能体协作 Run API 最小闭环：后端可启动、查询、订阅 SSE 和合作式取消 `course_learning_minimal`，且不动态管理 SecureHub 固定的 9 个业务智能体。

## 2. 实现摘要

- 新增进程内 `RunRegistry`，为每个 active run 保存状态、取消 token、SSE event queue 和 child trace；未新增 `workflow_runs` 表或数据库迁移。
- 新增 `course_learning_minimal` 固定顺序工作流：`career_planner.BuildLearningPersona` → `task_orchestrator.GenerateLearningPath` → `doc_archivist.GenerateCourseDoc` → `competition_advisor.GenerateQuiz` → `outcome_evaluator.QualityCheck`。
- 工作流复用已有 Harness，通过注入 fixture evidence/LLM 完成 evidence floor、质量检查、progress/evidence/trace 事件与 child-run 日志钩子。
- Fixture child trace 标记 `persistence=registry`，不会伪装为已持久化的 `agent_runs`。真实 mode 显式返回 `PROVIDER_UNAVAILABLE`，不会静默退回 fixture。
- 已安全检查本地 LLM 配置存在且字段有效；本轮未调用 DeepSeek health check 或真实模型，未输出或写入任何 Key。

## 3. API 清单

- `GET /api/v1/agents/manifest`：固定 9-agent manifest。
- `POST /api/v1/workflow-runs`：以 `202 Accepted` 创建 `course_learning_minimal` fixture run。
- `GET /api/v1/workflow-runs/{run_id}`：返回根状态和 5 个 child node 的 trace。
- `GET /api/v1/workflow-runs/{run_id}/events`：返回可回放 `text/event-stream`。
- `POST /api/v1/workflow-runs/{run_id}/cancel`：设置合作式 cancellation token。

完整请求、响应、状态机和 7 类 SSE 契约见 `docs/api/agent-run-contract.md`。

## 4. 多 agent workflow 链路

```text
course_learning_minimal
  -> career_planner.BuildLearningPersona
  -> task_orchestrator.GenerateLearningPath
  -> doc_archivist.GenerateCourseDoc
  -> competition_advisor.GenerateQuiz
  -> outcome_evaluator.QualityCheck
```

- 每次 fixture workflow 产生 5 条可追踪 child records，覆盖 5 个不同 agent。
- 每个 child record 含 `agent_name`、`skill_name`、状态、Harness `agent_run_id`、evidence count 和 quality score。
- 真实 mode 尚未启用；启用前必须让每个真实 skill 先持久化 `agent_runs`，并将 `workflow_run_id` 写入稳定 summary 字段。

## 5. SSE 与 cancel 说明

- 事件名固定为 `progress / evidence / token / artifact / trace / done / error`，不引入新事件类型。
- Fixture workflow 实际输出 `progress`、`evidence`、`trace`、`done`；它不把 canned content 伪装为 real token 或 artifact。
- `cancel` 立即转为 `cancelling`，节点边界检查 token；当前运行节点可标 `cancelled`，未执行节点标 `skipped`，最终 SSE `done.status=cancelled`。
- 不 kill 进程、不使用破坏性线程终止。取消后 fixture 不继续生成 `token` 或 `artifact`。

## 6. 测试命令与结果

在 `backend` 目录执行：

```powershell
uv run pytest tests/api/test_agent_control.py tests/runtime/test_course_learning_minimal.py
```

结果：`6 passed in 0.82s`。

补充回归：

```powershell
uv run pytest tests/test_api_smoke.py tests/runtime/test_skill_harness.py tests/streaming/test_sse_events.py
```

结果：`21 passed in 4.43s`。

## 7. 未完成 / 风险

- RunRegistry 仅进程内保存；服务重启后 active run、历史和 SSE replay 不可恢复。
- Agent-Run-1 只启用显式 fixture 模式，因此 child trace 是开发/测试级等价可追踪记录，不是 `agent_runs` 真落库验收。
- 真实 DeepSeek Harness、真实 RAG evidence、token 流、generated_resources/storage_objects、真实 child `agent_runs` 持久化仍需独立 live smoke 与联调；不应把本轮标为 real E2E。
- SSE 当前使用单进程 buffered event queue，尚未实现 Redis pub/sub、跨进程订阅或断线游标恢复。

## 8. 下一步建议

1. Agent-Run-2：在不改变 API 契约的前提下接真实 Harness/DeepSeek，强制 RAG evidence floor、真实 `agent_runs` 和 provider/model/token usage。
2. Agent-Run-3：将 doc / quiz 扩展为可控 fan-out，并为资源落库后补齐 `artifact` 事件。
3. Agent-Run-4：由 B 接入 AgentTracePanel、run status 和取消按钮。
4. Agent-Run-5：评估 `workflow_runs` 表、Redis、历史分页与重启恢复的真实需求。
