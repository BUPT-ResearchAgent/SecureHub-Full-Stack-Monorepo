# Agent-Run-2.2 真实 E2E 终验报告

## 1. 环境与临时配置边界

- 日期：2026-07-10；分支：`dev`。
- Docker 仅启动 `postgres` 和 `redis`，两者均为 `healthy`；没有启动 compose backend/frontend。
- `Settings().DATABASE_URL` 的非敏感语义为 `localhost:15432/securehub`，与本轮 Compose PostgreSQL 对齐。
- 本地 `backend/.env.local` 未修改、未提交、未回显；DeepSeek/Qwen 配置只由本地后端进程继承。
- 后端进程只临时设置了 `AGENT_RUN_REAL_ENABLED=true`、`AGENT_RUN_REAL_MAX_CONCURRENCY=1`、`AGENT_RUN_REAL_MAX_TOKENS=512`，进程结束后失效。
- 保留了既有 `.codegraph/` 和治理文档改动；未启动前端、未执行 destructive cleanup。

## 2. PostgreSQL / seed / Qwen RAG preflight（count/profile/IDs）

- `uv run alembic upgrade head`：成功。
- `uv run python -m app.db.seeds.seed_demo`：幂等成功；输出 `agents=9`、`skills=14`、`user_capabilities=9`、`courses=1`、`nodes=17`、`edges=39`、`documents=17`、`chunks=68`、`quiz_items=5`。
- `AgentRunService.ensure_real_workflow_prerequisites()`：`ok`；demo user UUID 为 `f18f600f-d7a7-574d-a236-9fe69ebc37d7`；五节点固定顺序解析成功。
- 当前 `course_websec` 中符合 `embedding_status=ready` 且 profile 为 `qwen-openai-compatible:text-embedding-v4:1024:dense:v1` 的 chunks：`3549`。
- 本轮未运行 embedding batch、未 reset 向量、未重爬数据；报告不把本地 68 条 seed 或 3549 条 ready 记录表述为 3555 chunks 全量重建。
- 真实 `retrieve("SQL 注入", domain="course_websec", top_k=3)` 返回 3 条：
  `16794e9b-8186-5971-8531-9724ed042054`、
  `3f10d9b5-ffb3-52fd-b3ce-1c05d28793fb`、
  `121aa385-6e3b-5846-bf2a-4e6446ff0a7f`。
- 首次 live RAG 发现一个真实数据投影缺口：`mineru` chunk `6d630440-4a96-5bcf-b057-82497adf05fb` 的 chunk metadata 没有 URL，但对应 `documents.url=local://crypto-basics.pdf`。strict adapter 已补 document-level source 回填，并在仍缺源地址时显式失败。

## 3. HTTP success smoke（root run ID、provider/model、SSE event counts）

后端 health 返回 HTTP 200，manifest 返回 9；fixture 路由也验证为
`fixture/fixture/fixture-canned`，没有标成 real。

实际 success 请求均为 `mode=real`、`provider=deepseek`、
`model=deepseek-v4-pro`，但两次都没有成功：

| root run ID | 结果 | SSE 安全摘要 | agent_runs |
|---|---|---|---:|
| `c21d1143-9911-4950-a041-2b2625629af0` | `failed / LLM_OUTPUT_INVALID` | `progress=3, evidence=1, token=0, trace=0, done=0, error=1` | 1 failed |
| `98b085ce-29d2-48ce-9891-fb0869b53c87` | `failed / LLM_OUTPUT_INVALID` | `progress=3, evidence=1, token=0, trace=0, done=0, error=1` | 1 failed |

两次 DeepSeek HTTP 请求均返回 HTTP 200，但 strict JSON 解析仍失败；第二次
使用了 DeepSeek JSON object response format，仍未形成可验收的 JSON 输出。由于
成功预算已用尽，没有继续尝试，也没有把失败改写为 fixture/blocked success。

## 4. HTTP cancel smoke（root run ID、cancel cursor、终态）

- root run ID：`f5767221-94d8-4d6c-b036-8a45b4b0652e`。
- 真实请求在首节点 evidence DTO 投影阶段失败，终态读取为
  `failed / WORKFLOW_FAILED`；没有观察到 token，因此没有发送 `POST /cancel`，
  `cancel_cursor=null`。
- 该请求没有 DeepSeek child 调用，按停止条件不重试 cancel；不能宣称
  `cancelled` 或“取消点后无 token/artifact”已通过。

## 5. PostgreSQL agent_runs 对齐证据（仅 UUID/count/状态，不含生成内容）

- cancel root `f576...`：`0` 条 `agent_runs`。
- 首次 success root `c21...`：`1` 条，child UUID
  `f221d9c0-9a53-4a32-821d-cee6f7be1838`，状态 `failed`，evidence count `0`。
- success retry root `98...`：`1` 条，child UUID
  `fa7bb6ef-cbe7-4867-b5ef-809b9bbe15f7`，状态 `failed`，evidence count `0`。
- 因此没有形成任一 root 的 5 条成功 `agent_runs`，也没有可提交的 API
  child UUID / SSE trace UUID / evidence ID 三方成功对齐证据。

## 6. 自动化测试与静态检查结果

- 用户指定原始命令：`42 passed, 1 failed`。唯一失败是既有
  `tests/test_api_smoke.py::test_rag_search_returns_fixture`：在本轮已恢复的真实
  PostgreSQL/Qwen ready 数据存在时，fixture embedding 仍召回真实 rows，返回
  `fallback=false`，旧断言要求 `fallback=true`。未修改该既有测试或扩大本轮边界。
- Agent-Run 核心 + smoke 无网络测试：`38 passed`。
- Evidence contract / retriever profile 回归：`10 passed`。
- smoke 工具单测最终：`7 passed`。
- `uv run python -m compileall -q scripts\smoke_agent_run_real.py`：通过。
- `git diff --check`：通过（仅报告已有治理文档换行提示，无 diff error）。
- `ruff` 未安装；未新增依赖。

## 7. DeepSeek 调用预算（planned/actual workflow 和 child 调用数）

- planned：1 次 cancel workflow（最多 1 child）+ 1 次 success workflow（最多 5 child）+ 仅允许 1 次 success retry（最多 5 child）。
- actual real workflow requests：3 次，达到本轮上限。
- actual DeepSeek child calls：首次 success 1 次；success retry 1 次；cancel 在 RAG DTO 阶段失败、0 次；合计 2 次已开始调用。
- 未调用单独 `health_check()`，未打印 Key、Authorization header、prompt、token 或模型输出。

## 8. 回滚、已知限制与最终验收结论

- 本轮真实 `agent_runs` 未删除，失败 rows 作为诊断证据保留；不执行 `down -v`、不删除 `pgdata`。
- 当前已知限制继续保留：单进程 registry、无重启恢复、无 `workflow_runs` 表、artifact 尚未接入 `generated_resources`。
- 本轮新增 smoke 工具、无网络测试、strict evidence source 回填、DeepSeek JSON response-format 接线和文档；没有前端扩展、没有新增 agent、没有 schema/migration 改动。
- **最终结论：Agent-Run-2.2 真实 E2E 终验未通过，不能签收为真实闭环完成。** 已通过的范围仅为 PostgreSQL/seed/Qwen RAG preflight、真实 HTTP start、真实 evidence 事件到达，以及 fake/SQLite 自动化回归；success 的真实 token/trace/done、5 条成功 `agent_runs`、DB/API/SSE evidence 对齐和 token 后 cancel 均未满足。
