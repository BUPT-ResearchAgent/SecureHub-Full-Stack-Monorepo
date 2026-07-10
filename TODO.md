# SecureHub 多智能体完整架构 TODO

> 版本：v2.0
> 维护者：TPM
> 更新日期：2026-07-11
> 当前分支：`dev`
> 基线提交：`b8c9ec57`
> 适用范围：从已签收固定 Agent Run API 推进到完整、统一、可恢复、可运营的产品级 Agent Runtime
> 目标方案：`../Plan/2026-07-11_SecureHub_多智能体底层完整架构实施方案.md`

## 0. 当前基线

已完成，不重复建设：

- [x] 固定 9 Agent manifest 与固定五节点 `course_learning_minimal`。
- [x] 真 DeepSeek `deepseek-v4-pro` + 真 Qwen RAG + 严格 JSON + 严格 QualityCheck。
- [x] 5 条 child `agent_runs` 真 PostgreSQL 持久化与 evidence UUID 对齐。
- [x] SSE progress/evidence/token/trace/done、完整 replay 与第一条 token 后 cancel。
- [x] Success root：`e467671e-52a8-408a-b8f7-68087b7cd366`。
- [x] Cancel root：`54d66622-d672-4ced-99ce-92d379eb42a0`。
- [x] C 的 3555 Qwen ready chunks、Evidence v1.2、COS Provider 与 20 资产私有同步样本。
- [x] 完整底层目标方案已写入 `Plan/2026-07-11_SecureHub_多智能体底层完整架构实施方案.md`。

以上只证明固定 Agent Run 专项闭环，不代表五条产品 endpoint、前端、多实例恢复或完整架构已完成。

## 1. 当前代码审计结论

必须优先解决：

- [ ] `services/agent/__init__.py` 当前把 fixture 函数导出为产品 endpoint 所谓的 real service。
- [ ] `skill_execution_service.py` 存在，但没有成为产品层统一真实入口。
- [ ] `agents.base.BaseSkill` 与 `runtime.harness.types.BaseSkill` 双轨并存。
- [ ] `SkillContext` 与 `HarnessContext` 双轨并存，DB logger 和 event emitter 多套适配。
- [ ] `planned_skill.py`、`_skill_helper.py`、直接 `skill.run()` 与 `Harness.run()` 多条执行路径并存。
- [ ] `runtime/graphs/course_learning.py` 与 `runtime/workflows/course_learning_minimal.py` 两套 workflow 并存。
- [ ] Agent-Skill 目录存在三套口径：9 个 `agent.py` 注册 28 个生产绑定，Leader Prompt 记录 22，
      DB `CORE_SKILLS` 只 seed 14；`_examples/EchoSkill` 不属于生产目录。
- [ ] `RunRegistry` 仅进程内存，重启丢 root、event、cancel 与 replay。
- [ ] 产品 endpoint 自建 asyncio queue、随机 run ID 和 SSE 终态，未复用 Agent Run 控制面。
- [ ] 生成 endpoint 可发 `resource_id=None` 的 artifact，未满足真实落库后再发事件。
- [ ] 前端 `useWorkflowRun` 仍以定时 mock replay 为核心，真实 trace 会注入 mock evidence。
- [ ] Guardrails、部分 ORM/service 与旧 SSE 文件仍标 planned 或只具备占位行为。

## 2. 不可突破的边界

1. 固定 9 个业务 Agent，不新增、删除、重命名或动态创建第 10 个：`policy_interpreter`、
   `hot_analyst`、`job_analyst`、`competition_advisor`、`career_planner`、`topic_explorer`、
   `doc_archivist`、`task_orchestrator`、`outcome_evaluator`；稳定 ID 使用现有 `agent_id(name)` UUIDv5 规则。
2. Runtime/Harness/RAG/Worker/Storage/Context/Tools/Guardrails 都是横切基础设施。
3. 知识资产仍统一使用 `documents/document_assets/chunks/knowledge_nodes/knowledge_edges`。
4. 画像唯一源仍是 `user_profiles + user_capabilities`。
5. 生成式 Skill 在请求/路由校验后先建立 running `agent_runs`，再走 RAG、模型、QualityCheck、artifact，
   最后把 child/step 事务性收敛到终态；任何外部 I/O 前不得缺少 child 审计记录。
6. real 不能静默 fallback 到 fixture，失败必须保持真实失败。
7. artifact 仅在 `generated_resources/storage_objects` commit 成功后发出。
8. 对外 SSE 只使用 progress/evidence/token/artifact/trace/done/error。
9. 不保存 API Key、完整 prompt、reasoning 或不必要的用户原文。
10. schema、Harness 契约或铁律变更必须同步 `CLAUDE.md`、`.codex/AGENTS.md` 与 API 文档。

## 3. 完整架构完成定义（唯一权威清单）

全部满足后才可称完成：

- [ ] 9 个稳定 Agent 名称/UUID 与代码 manifest、DB `enabled=true` 集合完全一致；CI 和生产启动均 fail-fast。
- [ ] AR-00 冻结的完整 Agent-Skill catalog 与代码注册、DB seed、CLAUDE/AGENTS/Leader 文档一致；当前基线
      28 个生产绑定全部走唯一 canonical Harness。
- [ ] 五条产品 endpoint 与 Agent Run API 共用唯一 RuntimeEngine/StateMachine/RunStore/EventStore，
      LangGraph 不维护第二套状态或 checkpoint。
- [ ] 每次已接纳的真实 Skill 调用在外部 I/O 前创建 running child `agent_runs`，并在成功、失败、阻断、
      取消时 CAS 收敛；不存在 RAG/LLM/QualityCheck 失败却无 child 记录。
- [ ] Root/step/event/checkpoint/child agent_runs/artifact/evidence snapshot/provider-call journal 全部 durable，
      UUID、sequence、attempt、provider/model 一致可追溯。
- [ ] 服务重启、worker lease 过期、SSE 重连和重复请求具备可验证恢复语义；Provider unknown outcome 不会
      被自动重放或伪称 exactly-once。
- [ ] Last-Event-ID 可跨 API/worker 重启 replay；七类事件顺序稳定，terminal 后无 token/artifact，
      error/done/cancelled 互斥规则通过。
- [ ] `mode=fixture|real` 可审计隔离；fallback 只作为 real Provider Policy，root 请求值与每次实际
      provider/model 均真实可查，real 永不静默进入 fixture。
- [ ] QualityCheck 支持有界返工，accept=false 最终仍可 blocked，不默认接受或伪造 evidence。
- [ ] cancel/pause/resume/node retry/approval 具备确定性状态机、ownership 和权限控制。
- [ ] artifact 仅在 `generated_resources/storage_objects` commit 后发出，evidence snapshot 可在源 chunk 变化后审计。
- [ ] 五条产品路径在真 Provider + 真 RAG + 真 agent_runs + 真 artifact + 前端 SSE 下通过。
- [ ] 讯飞星火演示主链真实通过，DeepSeek 显式 fallback 身份、原因和成本透明。
- [ ] Token/cost/latency/error/rework/recovery/unknown-call 指标可查询。
- [ ] Auth/JWT、run ownership、SSE authorization、prompt injection、secret redaction、预算和审计门禁通过。
- [ ] 旧 BaseSkill/Context/workflow/SSE/内存生产 registry/隐式 mock 路径被删除。
- [ ] migration、部署、运维、API、CLAUDE/AGENTS、演示和故障恢复文档同步完成。

## 4. 工作包总览

| ID | Wave | 工作包 | Owner | 依赖 | 状态 |
|---|---|---|---|---|---|
| AR-00 | 0 | 契约冻结与架构回归门禁 | A + B + C | Agent Run 2.4 | 未开始 |
| AR-01a | 1 | Canonical 契约、Harness 与单 Skill 样板 | A | AR-00 | 未开始 |
| AR-01b | 2 | 28 个 Agent-Skill 绑定生产切换 | A + C | AR-01a / AR-02 / AR-03 / AR-04 | 未开始 |
| AR-02 | 1 | 显式 fixture/real 与 Provider Fallback Policy | A + C | AR-00 | 未开始 |
| AR-03 | 1 | RuntimeEngine、StateMachine、WorkflowRegistry | A | AR-01a | 未开始 |
| AR-04 | 2 | Durable Run/Step/Event/Checkpoint/Evidence/ProviderCall schema 与 Store | A + C | AR-00 | 未开始 |
| AR-05 | 2 | Worker、Lease、Heartbeat、Redis fan-out、Recovery | A + C | AR-03 / AR-04 | 未开始 |
| AR-06 | 3 | 五条产品 Workflow 与 Product Adapter | A + B | AR-01b / AR-05 | 未开始 |
| AR-07 | 3-4 | Artifact、Evidence snapshot、ContextBuilder、Memory | A + C | AR-01a / AR-04 | 未开始 |
| AR-08 | 4 | QualityCheck defect taxonomy 与有界返工 | A + C | AR-06 / AR-07 | 未开始 |
| AR-09 | 4-5 | ToolRegistry、Permission、Budget、Rate Limit | A + C | AR-01a / AR-04 | 未开始 |
| AR-10 | 3-5 | 前端 WorkflowRunClient 与真实状态控制 | B | AR-00（契约骨架）；AR-04 / AR-06（真实联调） | 未开始 |
| AR-11 | 4 | 讯飞星火演示主链与显式 DeepSeek fallback | A + B + C | AR-02 / AR-06 / AR-07 / AR-08 | 未开始 |
| AR-12 | 5 | Cancel/Pause/Resume/Retry/Approval | A + B | AR-05 / AR-09 / AR-10 | 未开始 |
| AR-13 | 5 | Observability、Evals、Audit、Security | A + B + C | AR-04 / AR-06 | 未开始 |
| AR-14 | 6 | 删除兼容路径与文档同步 | A + B + C | AR-01a/01b + AR-02 至 AR-13 | 未开始 |
| AR-15 | 6 | 全量真实 E2E、故障注入与最终签收 | A + B + C | AR-14 | 未开始 |

原 v1.0 工作包映射：

- `MA-P0-01` -> AR-06 + AR-10 + AR-15
- `MA-P0-02` -> AR-11
- `MA-P1-01` -> AR-08
- `MA-P1-02` -> AR-04 + AR-05
- `MA-P1-03` -> AR-07
- `MA-P1-04` -> AR-09 + AR-13
- `MA-P2-01` -> AR-12

当前唯一第一关口是 **AR-00**。它完成前不迁移生产调用链；完成后首先修复 AR-02 中 fixture/real 泄漏，
再进入 Runtime 和产品路径迁移。

## 5. Wave 0：契约冻结与回归门禁

### AR-00 契约冻结与架构测试

执行：

- [ ] 新建 `docs/api/agent-runtime-contract.md`。
- [ ] 冻结 root/node 状态机、七类 EventEnvelope、cursor、terminal 互斥规则。
- [ ] 冻结 `mode=fixture|real`、requested/actual provider-model、fallback policy 和统一 error taxonomy。
- [ ] 冻结 WorkflowDefinition/NodeDefinition/SkillDefinition 最小字段。
- [ ] 冻结上述 9 个 Agent 稳定名称/UUID，并增加代码 manifest ↔ DB enabled 集合的 CI/启动校验。
- [ ] 盘点 28 个 `agent.py` 生产绑定，解释并消除 Leader 22、DB seed 14 的差异，输出唯一版本化 catalog。
- [ ] 冻结 artifact 事务语义、idempotency key 与 retry attempt 语义。
- [ ] 冻结 Provider `completed/unknown/retry-approved` 语义，不假设 DeepSeek/讯飞支持幂等键。
- [ ] 冻结五条 endpoint 的 SSE/同步等待/202/断连/统一 root ID 兼容契约。
- [ ] 冻结 Auth/JWT、run ownership 与 SSE authorization 最小门禁。
- [ ] 新增 architecture tests：固定 9 Agent/稳定 ID、catalog 对齐、infra 非 Agent、real 不进 fixture。
- [ ] 新增 terminal invariant tests：error/done 不冲突，cancel 后无 token/artifact。
- [ ] 将 Agent Run 2.4 success/cancel/replay smoke 设为每波回归门禁。

验收：

- [ ] A/B/C 可只依赖契约并行开发，无需读取彼此内部实现。
- [ ] 所有新代码有唯一状态、事件和错误定义来源。

## 6. Wave 1：单一执行内核

### AR-01a Canonical 契约、Harness 与单 Skill 样板

执行：

- [ ] 选定 `agents.base.BaseAgent/BaseSkill` 为唯一 Agent/Skill 基类。
- [ ] 新建唯一 `SkillDefinition`，覆盖 schema/tools/domains/evidence/guardrails/quality/artifact/timeout/retry/fallback/risk。
- [ ] 将 `HarnessContext` 收敛为 `ExecutionContext`，明确 immutable identity 与 injected services。
- [ ] 将 `Harness` 拆分为 executor、context builder、hooks、adapters、errors。
- [ ] 在 AR-01a 提供最小 ContextBuilder、ToolDispatcher、ALLOW/DENY policy 和 root/node budget contract；
      AR-07/AR-09 只增强策略，不重建执行入口。
- [ ] 迁移一个垂直样板 Skill 并验证 real/fixture/error/cancel/persistence。
- [ ] 定义可注入 RunRecorder/EvidenceSnapshotStore/ProviderCallStore 接口；样板阶段使用测试或现有兼容 adapter，
      不宣称已完成 durable 生产切换。

验收：

- [ ] 样板 Skill 通过 fixture/real/error/cancel 契约测试，RuntimeEngine 可只依赖接口推进。
- [ ] AR-04 可与本工作包并行实现 Store，不需要读取 Harness 内部实现。

### AR-02 显式执行模式与 Provider Fallback Policy

执行：

- [ ] fixture adapter 只能由 `mode=fixture` 显式选择。
- [ ] real RAG 空/错不返回 fixture evidence。
- [ ] real LLM 错/超时不返回 fixture output。
- [ ] real schema 失败不填默认业务字段。
- [ ] real QualityCheck 异常不默认接受。
- [ ] real agent_runs/artifact 失败不报告成功。
- [ ] fallback 仅允许 real provider -> real provider，记录 source/target/reason/cost。
- [ ] A3 演示 provider policy：xfyun primary，deepseek explicit fallback。
- [ ] fallback 后 root 仍为 `mode=real`；root 记录 requested policy，provider-call/child/artifact 记录 actual provider/model。

验收：

- [ ] 用故障注入证明 real 不会进入 fixture 模块。
- [ ] root、child、trace、artifact 的 requested/actual provider-model 关系完整且不冒充同一 Provider。

### AR-03 RuntimeEngine、StateMachine、WorkflowRegistry

执行：

- [ ] 新建确定性 root/node 状态机和 CAS 终态写入。
- [ ] 新建版本化 WorkflowDefinition/Registry/validator。
- [ ] 明确 RuntimeEngine/StateMachine 是唯一生命周期权威；LangGraph 只计算图拓扑/条件边，
      使用同一 CheckpointStore，不启用第二套持久状态。
- [ ] 支持 sequential、parallel fan-out、conditional edge、rework、interrupt。
- [ ] 合并 `graphs/course_learning.py` 与 `workflows/course_learning_minimal.py`。
- [ ] 保留 `course_learning_minimal` v1 契约作为回归 workflow。
- [ ] 将 Agent Run API 改为 RuntimeEngine 的薄控制面。

验收：

- [ ] 同一 workflow definition 可在 fixture/DeepSeek/讯飞下运行。
- [ ] 非法状态转移、未知 Agent/Skill、workflow version 漂移均 fail-fast。

## 7. Wave 2：Durable Control Plane

### AR-04 Run/Step/Event/Checkpoint/Evidence/ProviderCall schema 与 Store

执行：

- [ ] 设计并评审 `workflow_runs`。
- [ ] 设计并评审 `workflow_step_attempts`。
- [ ] 设计并评审 `workflow_events`，唯一 `(workflow_run_id, sequence)`。
- [ ] 设计并评审 `workflow_checkpoints`。
- [ ] 设计并评审 `workflow_evidence_snapshots`，包含 chunk/document version、digest、citation/source/rights snapshot。
- [ ] 设计并评审 `workflow_provider_calls`，包含 attempt、request digest、provider request ID、
      started/completed/unknown、response ref 与 usage。
- [ ] 预建 `workflow_approvals` 或明确 Wave 5 additive migration。
- [ ] 为 `agent_runs` 增加 `workflow_run_id/step_attempt_id/attempt/provider/model`。
- [ ] 为 `generated_resources` 增加 root/step/version 关联。
- [ ] 实现 RunStore/EventStore/CheckpointStore repository 接口与 PostgreSQL 实现。
- [ ] Start 支持 `Idempotency-Key`，重复请求返回同一 root。
- [ ] terminal root + terminal event 保证事务一致。
- [ ] `workflow_runs.id` 成为 Agent Run API 与产品 adapter 共用的唯一外部 root ID。
- [ ] RunStore/status/SSE 强制 user ownership；未授权查询不泄露 run 是否存在。
- [ ] 同步 `CLAUDE.md`、`.codex/AGENTS.md`、ORM、migration 与 API 文档。

验收：

- [ ] 服务重启后 status 与完整 event replay 可用。
- [ ] root、step、child、artifact UUID 通过 FK 和测试对齐。
- [ ] migration upgrade/downgrade 仅在一次性测试库 round-trip；生产回滚通过 feature flag/向前兼容代码，
      有数据的新表/列不直接 drop。

### AR-01b 28 个 Agent-Skill 绑定生产切换

执行：

- [ ] 将 AR-01a 的 RunRecorder/EvidenceSnapshotStore/ProviderCallStore 绑定到 AR-04 PostgreSQL 实现。
- [ ] 机械迁移其余 27 个已注册生产 Agent-Skill 绑定（排除 `_examples/EchoSkill`）。
- [ ] 所有 workflow/registry 只经 RuntimeEngine/SkillExecutor 调用 Skill；产品 endpoint 切换由 AR-06 完成。
- [ ] 删除 Skill 内重复 `ctx.log_run()`，由 Harness 保证一次且仅一次 child persistence。
- [ ] 输入/路由校验通过后，在任何 RAG/LLM 前事务性创建 step attempt + running child；
      finally/CAS 收敛 succeeded/failed/blocked/cancelled。
- [ ] real 调用写 evidence snapshot 与 provider-call journal，artifact/terminal event 遵守事务边界。
- [ ] 同步 `CLAUDE.md`、`.codex/AGENTS.md` 的 Harness 生命周期与 Skill 骨架，避免继续要求 Skill 自行末尾落库。

验收：

- [ ] AR-00 catalog 中全部 28 个生产绑定执行入口唯一。
- [ ] 每个真实 Skill 都能定位 root/step/agent_run/provider-call/actual provider-model/evidence snapshot。
- [ ] RAG、schema、QualityCheck、persistence、cancel 任一失败均留下唯一 terminal child 记录。

### AR-05 Worker、Lease、Redis 与 Recovery

执行：

- [ ] API 创建 root 后只提交事务和通知，不用 `asyncio.create_task` 承载 durable 业务。
- [ ] 独立 worker 原子 claim queued root。
- [ ] 增加 lease owner、lease expiry、heartbeat 和并发限制。
- [ ] Redis 用于任务通知、实时 event fan-out、cancel signal 和短期 cache。
- [ ] PostgreSQL 仍是状态与事件审计源。
- [ ] worker crash 后从 checkpoint 恢复；不能恢复时明确 failed，不假成功。
- [ ] 慢 SSE consumer 从 DB 补 event gap，不阻塞 worker。
- [ ] artifact persist、capability update 使用项目侧 idempotency key；Provider call 使用 journal，
      仅在上游官方支持且已验证时使用其幂等键。
- [ ] 崩溃后 `completed` call 复用落盘响应；`unknown` call 默认 waiting_approval/blocked，不自动重复计费。

验收：

- [ ] kill/restart API 不丢 completed run/replay。
- [ ] kill/restart worker 可恢复或明确终止，不重复 child/artifact。
- [ ] 两 worker 竞争同 root 只有一个执行者。

## 8. Wave 3：产品 Workflow 与前端真实接入

### AR-06 五条产品 Workflow 与 Adapter

执行：

- [ ] `profile_build_v1` -> `/profile/chat`。
- [ ] `course_plan_v1` -> `/courses/{id}/plan`。
- [ ] `resource_generate_v1` -> `/courses/{id}/resources/generate`。
- [ ] `tutor_routing_v1` -> `/tutor/ask`。
- [ ] `assessment_update_v1` -> `/assessment/run`。
- [ ] 实现 `course_learning_full_v1` 完整 A3 组合 workflow。
- [ ] 产品 endpoint 只做 DTO/auth/workflow input mapping。
- [ ] SSE endpoint 提交 root 后立即返回，断连不取消；同步 DTO endpoint 到时限后返回
      `202 + Location + run_id`，不得把 queued/running 映射为 success。
- [ ] 旧 Agent Run 与新 WorkflowRun 共用同一 root UUID，重复 start 依靠 Idempotency-Key 返回同一 root。
- [ ] 删除产品 endpoint 自建 queue、随机不可查 run ID、直接 Skill import。
- [ ] `services/agent/__init__.py` 不再把 fixture 导出为 real service。
- [ ] 每条路径写真 agent_runs；生成路径写真 artifact；评估路径写画像/能力。

验收：

- [ ] 每条路径有真实 root ID、child IDs、evidence IDs、provider/model 和终态。
- [ ] blocked/failed/cancelled 不会被 endpoint 或前端改写为 success。

### AR-10 前端 WorkflowRunClient

执行：

- [ ] 新建 start/status/events/cancel/pause/resume/retry typed client。
- [ ] 支持 Last-Event-ID 持久 cursor 与重连 replay。
- [ ] reducer 覆盖 queued/running/reworking/pausing/paused/waiting_approval/cancelling/cancelled/
      succeeded/failed/blocked。
- [ ] node reducer 覆盖 pending/ready/running/succeeded/failed/blocked/cancelled/skipped。
- [ ] 七类事件更新 EvidenceDrawer、Token、Artifact、AgentTrace 与终态。
- [ ] real trace 禁止注入 mock evidence/output。
- [ ] PresenterMode 与 real 模式显式分离并显示标签。
- [ ] 页面刷新后按 root ID 恢复当前任务。
- [ ] 最长错误码、provider/model、状态文本在移动/桌面均不溢出。

验收：

- [ ] 五条产品路径真实 UI 可复现。
- [ ] 网络断开重连不重复 token/artifact，不丢终态。

## 9. Wave 4：Artifact、Context 与质量协作

### AR-07 Artifact、Evidence、ContextBuilder、Memory

执行：

- [ ] 定义 ArtifactRef 与 schema version。
- [ ] 小型结构写 `generated_resources.content`，大文件写 `storage_objects.object_key`。
- [ ] artifact commit 后才 append `artifact` event。
- [ ] Evidence snapshot 固定当次引用，保留 chunk/document/source/rights linkage。
- [ ] snapshot 写入不可变版本/内容摘要；源 chunk 后续更新或删除时仍可重建当次引用语义。
- [ ] ContextBuilder 实现 select/rank/deduplicate/truncate/summarize/redact/budget。
- [ ] 节点只接收所需 artifact projection，不共享完整历史。
- [ ] user_profiles/capabilities、knowledge、artifact 分别承担长期记忆，不存 reasoning。
- [ ] resource_versions 支持返工和 node retry 的历史版本。

验收：

- [ ] 新会话可从 root ID 恢复 artifact/evidence/quality 展示。
- [ ] artifact 失败只发 error，不发空 artifact/done success。

### AR-08 QualityCheck 有界返工

执行：

- [ ] defect 闭枚举：evidence_missing/fact_conflict/schema_invalid/instructional_mismatch/citation_mismatch/safety_violation。
- [ ] defect -> producer node 确定性路由表。
- [ ] root/node 最大返工次数、token/cost/time budget。
- [ ] 每次返工新建 step attempt、agent_run 与 resource version。
- [ ] trace 记录 defect、前后 quality、evidence 变化与终止原因。
- [ ] 重复 defect/no-progress 进入 blocked。
- [ ] 安全违规不自动返工为更易通过的内容。

验收：

- [ ] 可修复缺陷真实返工后成功或明确 blocked。
- [ ] accept=false 从不被默认改为 true。

### AR-11 讯飞星火演示主链

执行：

- [ ] 讯飞 structured output、stream、usage、timeout、finish reason 适配统一契约。
- [ ] 五条产品路径至少选择演示主线做真讯飞验收。
- [ ] 同输入验证 Evidence/Quality/artifact/agent_runs。
- [ ] DeepSeek fallback 显示实际切换，不冒充讯飞。
- [ ] health、限流、预算与错误 UI 完整。
- [ ] live smoke 不打印 Key、完整 prompt、reasoning 或完整模型文本。

验收：

- [ ] A3 演示可证明实际 xfyun/spark 调用。
- [ ] 讯飞失败时 fallback 或 failed 语义透明。

## 10. Wave 5：Tool、控制、可运营与安全

### AR-09 ToolRegistry、Permission、Budget（高级治理）

执行：

- [ ] 在 AR-01a 最小 Tool/Policy/Budget 契约上扩展 ToolDefinition 的 risk/timeout/retry/idempotency/permission。
- [ ] ToolRegistry/Dispatcher 禁止 Skill 直接构造外部客户端。
- [ ] `ALLOW/ASK/DENY` PolicyEngine。
- [ ] root/node/provider call 多级 token/cost/time/concurrency budget。
- [ ] retry 只针对声明为安全/幂等的错误和操作。
- [ ] provider/RAG/storage 熔断与健康状态。
- [ ] 生产 Agent 默认无任意 Shell/文件系统/浏览器权限。

验收：

- [ ] 权限、预算和 timeout 由确定性逻辑执行，不交给 LLM 决定。
- [ ] 超预算/拒绝/熔断都有稳定错误码和审计记录。

### AR-12 Cancel/Pause/Resume/Retry/Approval

执行：

- [ ] cancel 持久化 + Redis signal + provider cooperative abort。
- [ ] pause 仅在安全 checkpoint 生效。
- [ ] resume 校验 workflow version、owner、budget、checkpoint。
- [ ] node retry 新建 attempt，不覆盖历史。
- [ ] 高风险、成本超阈值、多次质量拒绝进入 approval。
- [ ] 前端提供明确控制状态与失败反馈。

验收：

- [ ] control 请求幂等且需要 ownership/permission。
- [ ] cancel cursor 后无 token/artifact；pause 后无新副作用；resume 不重复已完成节点。

### AR-13 Observability、Evals、Audit、Security

执行：

- [ ] 复用 AR-00/AR-04 已落地的 Auth/ownership/SSE authorization，不把基础鉴权推迟到本工作包。

- [ ] 关联 request/root/step/agent_run/resource/evidence IDs。
- [ ] 指标：success、blocked/failed taxonomy、rework、recovery、token/cost、provider latency、RAG、quality、cancel。
- [ ] 结构化日志 redaction，不记录 Key/prompt/reasoning/敏感原文。
- [ ] Auth/JWT、run ownership、SSE authorization。
- [ ] 用户输入与 retrieved content prompt injection guardrail。
- [ ] 私有 artifact signed URL 与访问审计。
- [ ] Provider/Skill/Workflow/Multi-Agent/Product E2E 分层 eval。
- [ ] CI 默认 fixture/fake provider；真实 DeepSeek/讯飞只走手动 live gate。

验收：

- [ ] 任一错误 root 可定位阶段、错误码、provider、child、evidence、quality 与恢复结果。
- [ ] 安全测试确认无 Secret、reasoning 或跨用户数据泄露。

## 11. Wave 6：清理与最终签收

### AR-14 删除兼容路径与同步文档

执行：

- [ ] 删除 `runtime.harness.types.BaseSkill`。
- [ ] 删除旧 `SkillContext` 独立实现和双 logger。
- [ ] 删除 `planned_skill.py` 执行兼容层。
- [ ] 删除 endpoint 直接 `skill.run()` 与自建 SSE queue。
- [ ] 删除生产用内存 RunRegistry，仅保留测试实现。
- [ ] 合并/删除多套 SSE serializer。
- [ ] 删除产品层隐式 fixture import。
- [ ] 删除前端 real trace 的 mock replay/evidence 注入。
- [ ] 清理 `[planned]` 状态漂移和重复 ORM compatibility 文件。
- [ ] 同步 CLAUDE/AGENTS/API/demo/deploy/operations 文档。

验收：

- [ ] `rg` 与 architecture tests 证明旧路径无生产调用点。
- [ ] fixture 只能通过显式配置进入。

### AR-15 最终真实验收

必须通过：

- [ ] 9 Agent 与 AR-00 版本化 Agent-Skill catalog（当前 28 个生产绑定）和 DB alignment。
- [ ] 五条产品路径 DeepSeek real E2E。
- [ ] A3 演示主线讯飞 real E2E。
- [ ] course_learning_full 并行资源 + QualityCheck + 有界返工。
- [ ] PostgreSQL root/step/event/checkpoint/agent_runs/artifact/evidence snapshot/provider-call UUID 与 attempt 对齐。
- [ ] 完整 Last-Event-ID replay，跨 API/worker 重启 replay。
- [ ] cancel-after-first-token、pause/resume、node retry、approval。
- [ ] 两 worker 互斥与 lease recovery。
- [ ] 网络/provider/RAG/schema/quality/persistence/COS 故障注入。
- [ ] 前端刷新/断线/重连/错误态/移动端布局。
- [ ] token/cost/latency/error/rework/recovery 查询。
- [ ] disposable DB migration round-trip、生产备份/向前兼容代码回切与非破坏回滚演练。
- [ ] 默认 CI 全绿，live smoke 手动记录 root IDs 与调用次数。

交付报告必须记录：

- 最终 commit/PR/branch。
- DeepSeek 与讯飞真实 root IDs。
- SSE 各事件计数与 replay 结果。
- root/step/agent_runs/artifact/evidence 对齐结论。
- restart/recovery/control/fault-injection 结果。
- 实际模型调用次数与成本摘要，不记录敏感内容。

## 12. 依赖与并行执行图

```text
AR-00 -> AR-01a, AR-02, AR-04, AR-10(contract scaffold)
AR-01a -> AR-03
AR-03 + AR-04 -> AR-05
AR-01a + AR-02 + AR-03 + AR-04 -> AR-01b
AR-01b + AR-05 -> AR-06
AR-01a + AR-04 -> AR-07
AR-06 + AR-07 -> AR-08
AR-01a + AR-04 -> AR-09
AR-04 + AR-06 -> AR-10(real integration)
AR-02 + AR-06 + AR-07 + AR-08 -> AR-11
AR-05 + AR-09 + AR-10 -> AR-12
AR-04 + AR-06 -> AR-13
AR-01a/01b + AR-02..13 -> AR-14 -> AR-15
```

并行原则：

- A 主关键路径：AR-01a/01b/02/03/05/06/08/09/11/12。
- B 在 AR-00 后先做 AR-10 契约骨架；只有 AR-04/06 完成后才接真实 Store/API，并参与 AR-06/11/12/13。
- C 在 AR-00 后先做 AR-04；AR-01b 等 AR-01a+02+03+04，AR-07 等 AR-01a+04，
  AR-13 等 AR-04+06，同时负责每波验收，不扩采集主线。
- 高风险 schema/API/CLAUDE/AGENTS 文件需要对应 owner 双签。

## 13. 每个工作包的统一交付要求

1. 一个设计说明或执行 Prompt，列明 owner、依赖、边界、迁移和回滚。
2. 单一可回滚主题，不把全架构塞进一个 PR。
3. 单测、契约测试、集成测试与对应 smoke。
4. fixture/real mode、Provider fallback policy/实际切换与失败语义显式可查。
5. 真实路径提供可追溯 root ID、provider/model、SSE 与数据库证据。
6. 不伪造 evidence/artifact，不跳过 QualityCheck/agent_runs。
7. 修改 schema/契约/铁律时同步宪法与 API 文档。
8. 交付后更新本 TODO 的状态、证据链接与 commit。

## 14. 推荐开工顺序

下一轮只开 AR-00，并为 AR-01a/AR-04/AR-10 建立并行准备，不直接同时修改全部生产路径：

1. 冻结 Agent Runtime Contract。
2. 建架构不变量测试与 Agent Run 2.4 回归门禁。
3. 选 `GenerateCourseDoc` 做 canonical Skill 垂直样板。
4. 评审 durable schema migration。
5. B 按冻结 Event/State contract 起草 WorkflowRunClient。

AR-00 验收后，A 并行开 AR-01a/02，C 开 AR-04，B 只实现 AR-10 的冻结契约骨架；AR-01a 契约
稳定后 A 可开 AR-03，无需等待 AR-04。28 个绑定的 AR-01b 生产切换必须等待 AR-01a/02/03/04
全部完成；真实前端联调必须等待 AR-04/06。
