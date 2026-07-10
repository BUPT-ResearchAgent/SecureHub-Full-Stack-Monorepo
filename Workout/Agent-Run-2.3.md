# Agent-Run-2.3 严格 Real 路径修复与最终 E2E 报告

## 1. 授权、预算与环境边界

- 日期：2026-07-10；分支：`dev`；既有 `.codegraph/`、`.codex/AGENTS.md`、`AGENTS.md`、`CLAUDE.md` 改动均保留，未混入本轮提交。
- 仅启动 Docker Compose `postgres` 与 `redis`，两者均为 `healthy`；没有启动 compose backend/frontend。
- 使用当前命令进程临时设置宿主机 PostgreSQL `127.0.0.1:15432`、`AGENT_RUN_REAL_ENABLED=true`、`AGENT_RUN_REAL_MAX_CONCURRENCY=1`。backend 初次 smoke 使用 `AGENT_RUN_REAL_MAX_TOKENS=2048`，因真实 `finish_reason=length` 后重启为允许上限 `4096`；未修改 `.env.local`。
- 未调用通用 `health_check()`，未输出 Key、Authorization header、prompt、reasoning、完整 token 或模型输出；真实 `agent_runs` 未删除。

## 2. provenance audit（before/after count、ID、来源字段）

- `uv run alembic upgrade head` 成功。
- `uv run python -m app.db.seeds.seed_demo` 幂等成功；本次 delta 为 `agents=9`、`skills=14`、`user_capabilities=9`，课程、节点、文档和 chunk 的 delta 均为 `0`，没有 reset、全量重嵌入或重爬数据。
- Qwen profile：`qwen-openai-compatible:text-embedding-v4:1024:dense:v1`；`course_websec` 中 `embedding_status=ready`、profile 一致的 ready chunks 为 `3549`。这只是当前本地 ready count，不代表 3555 chunks 全量重建。
- 只读 `retrieve("SQL 注入", domain="course_websec", top_k=8)` 返回 8 条，`missing_count=0`。selected chunk IDs：`65646552-b885-5b43-86dc-a4cc31eca72f`、`97b949fd-c2fa-5f8e-8513-fa015f1e75e2`、`16794e9b-8186-5971-8531-9724ed042054`、`9316e8fb-df5e-526f-a52b-00143aadd8f3`、`3f10d9b5-ffb3-52fd-b3ce-1c05d28793fb`、`bbb4bac8-9556-59fa-b209-115da2233ae5`、`762c3334-25ab-528a-b2cd-200dfebc7af3`、`121aa385-6e3b-5846-bf2a-4e6446ff0a7f`。这些命中的 source 均来自 `chunk_metadata.source_url`，platform 为 `owasp`。
- retry workflow 的 DB evidence union 共 9 个 ID，非 manual source 缺失为 `0`：7 条来自 `chunk_metadata.source_url`，2 条 `mineru` 来自 canonical `document.url`（包括 `6d630440-4a96-5bcf-b057-82497adf05fb`）。没有伪造 URL、fixture evidence 或手工标记绕过 strict 校验。
- `AgentRunService.ensure_real_workflow_prerequisites()` 成功解析 demo user 与固定五节点 workflow；manifest/API 预检返回恰好 9 agents。

## 3. DeepSeek 协议诊断（安全结构摘要）

- 唯一协议诊断实际发送 1 次流式请求，`max_tokens=128`，`provider=deepseek`、`model=deepseek-v4-pro`。
- 结果：`chunk_count=3`、`finish_reason=stop`、`final_content_length=2`、`has_final_content=true`、`parse_category=json_object`。未输出 content 本身或 reasoning。

## 4. 代码修复与严格性说明

- `DeepSeekProvider` 现在只聚合 OpenAI-compatible `message.content` / `delta.content`，忽略 `reasoning_content`；流式完成 chunk 会传递 `finish_reason`，畸形 SSE JSON 显式成为 provider error，不再静默跳过。
- `StrictLiveAdapters` 对 no-final-content、invalid JSON、non-object JSON 只记录安全诊断字段：phase、finish reason、content length、final-content presence、parse category；不接受 Markdown 剥离、任意对象截取、默认填充或 fixture fallback。
- Harness schema hint 改为递归、确定性、合法的 compact JSON schema，移除对 JSON 字符串的 `[:2000]` 截断；`evidence_chunk_ids` 仍由服务端注入。
- fixture RAG API 测试显式注入隔离 retriever，真实 PostgreSQL/Qwen ready rows 不会改变 fixture 分支，且断言 `fallback=true`、不标记 `real`。
- provenance audit 与失败时返回 root ID 的 smoke 工具均为窄范围、安全输出；无数据库 schema/migration、agent manifest、frontend 或 data 资产改动。

## 5. 无网络回归与 fixture 隔离结果

- 主回归命令：`55 passed`。
- RAG/hallucination/provider 集合：`17 passed`。
- `uv run python -m compileall -q app scripts`：通过。
- `git diff --check`：通过；ruff 未安装，未新增依赖。
- fake provider 回归继续覆盖 evidence floor、strict JSON 失败、QualityCheck 拒绝、5 条 persistence、取消后 token/artifact 泄漏；`QualityCheck.accept=false` 仍保持 `blocked/QUALITY_REJECTED`。

## 6. HTTP success smoke（root ID、provider/model、事件计数、replay、5 child）

### 首次 success

- root：`8f23e1ac-7e1e-47b6-b6fb-47afd54cd9a3`。
- HTTP start 身份正确：`mode=real`、`provider=deepseek`、`model=deepseek-v4-pro`。
- root 终态：`failed / LLM_OUTPUT_INVALID`。安全诊断为 `finish_reason=length`、final content 存在、长度 `789`、`parse_category=invalid_json`。这是本轮 backend 临时 token 上限不足的可验证失败，未做宽松解析。
- PostgreSQL：同 root 仅有 1 条 failed child，未形成 5 条成功 child；未进入 success replay 验收。

### 唯一 success retry

- root：`ea621ea3-b961-4f0d-88b9-4af77f38bf60`；使用临时 `AGENT_RUN_REAL_MAX_TOKENS=4096`。
- HTTP/SSE 安全事件计数：`progress=12`、`evidence=2`、`token=2030`、`trace=3`、`error=1`；terminal error code 为 `QUALITY_REJECTED`，没有 `done/succeeded`。
- status API：`mode=real`、`provider=deepseek`、`model=deepseek-v4-pro`、root `blocked`；5 个 child 均为 `succeeded / persistence=agent_runs`。
- 因 root 被严格质量闸拒绝，smoke 没有把它当 success，也没有执行 success replay 通过判定。事件历史在高 token stream 下还触及现有 bounded registry replay 窗口，需后续单独评估，不在本轮预算内修复或重跑。

## 7. HTTP token 后 cancel smoke（root ID、cancel cursor、终态）

- 本轮没有执行 cancel smoke。按照规定，success 必须完整通过后才可运行 cancel；唯一 success retry 以 `QUALITY_REJECTED` 终止后，立即停止，未发送任何 cancel 请求。
- 因此本轮没有合法的 `cancel_cursor`，也不能宣称真实 token 后 `cancelled` 或取消点后无 token/artifact。Agent-Run-2.2 的历史 cancel root `f5767221-94d8-4d6c-b036-8a45b4b0652e` 未重跑。

## 8. PostgreSQL agent_runs 对齐（UUID/count/状态/evidence IDs）

- retry root `ea621ea3-b961-4f0d-88b9-4af77f38bf60`：按 `input_summary.workflow_run_id` 查到恰好 5 条，外键 `user_id/agent_id/skill_id` 全部非空，状态全部 `success`。
- child UUID：`eb0ea9fe-52fe-4c6c-8101-0261a2e61fa7`、`3b55d60d-24aa-49ad-99e2-8662de53e789`、`fddd77a2-9152-4370-b1fd-347ab165cf73`、`b99a9770-04cf-49bb-90e5-74cda3d0b972`、`1270805f-4c41-43bf-a8e4-8c74b9184bad`。
- DB evidence union count 为 `9`，全部来自真实 retrieve 且 provenance audit 无缺失；但由于 root 未 succeeded、SSE 终端为 quality error，本条只能作为 persistence 证据，不能升级为完整 success API/SSE/DB 三方签收。
- 首次失败 root `8f23e1ac-7e1e-47b6-b6fb-47afd54cd9a3`：1 条 failed child；历史 2.2 roots 保留原记录，未删除。

## 9. 调用预算实际消耗、回滚与已知限制

- planned：1 次协议诊断、1 次 success workflow、仅因可验证实现/配置问题允许 1 次 success retry、success 后 1 次 cancel workflow。
- actual：协议诊断 `1` 次；real workflow root `2` 个；DeepSeek child 调用 `1 + 5 = 6` 次；cancel root `0`、cancel child `0`。达到 success retry 后的停止条件，不再循环调用。
- 本轮自己启动的 backend 已停止；临时 real 环境变量随进程退出失效。PostgreSQL/Redis 未执行 destructive cleanup，pgdata 与真实 `agent_runs` 保留。
- 已知限制继续保留：单进程 registry、无重启恢复、无 `workflow_runs` 表、artifact 尚未接入 `generated_resources`。本次还观察到高 token stream 会占用 bounded event history，但没有在已用完 live retry 预算后继续修改和重跑。

## 10. 最终验收结论

**未签收。**

本轮通过了无网络严格性修复、PostgreSQL/seed/Qwen provenance preflight、唯一协议诊断，以及 retry 的 5 条真实 `agent_runs` 外键/evidence 持久化；但没有通过完成定义中的 root `succeeded`、完整 success SSE `progress/evidence/token/trace/done`、success replay 和 token 后 cancel。因此不能称为“Agent Run API 多智能体真实闭环完成”。后续需要新的明确授权与新的 DeepSeek 预算，优先处理真实 QualityCheck 被拒绝的业务原因及 bounded SSE replay 窗口，再重新执行 success 后才可执行 cancel。
