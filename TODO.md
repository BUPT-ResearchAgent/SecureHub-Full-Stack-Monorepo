# SecureHub 工程化 TODO

> 版本：v1.0  
> 维护者：TPM  
> 更新日期：2026-07-10  
> 当前分支：dev  
> 适用范围：多智能体协同从“固定 Agent Run API 已闭环”推进到“产品主路径可演示、可运营、可恢复”  
> 权威入口：Plan\2026-07-10_Agent_Run_API_真实闭环凝练索引.md

## 0. 当前基线

已完成，不重复建设：

- 固定 9 agent 的 Agent Run API 已在真 DeepSeek、真 RAG、真 PostgreSQL agent_runs 下完成
  start / SSE observe and replay / persistence / token 后 cancel 闭环。
- 真实 success root：e467671e-52a8-408a-b8f7-68087b7cd366。
- 真实 cancel root：54d66622-d672-4ced-99ce-92d379eb42a0。
- QualityCheck 保持严格，真实通过来自完整 artifact 输入，不是放宽质量闸。
- C 的知识数据、Qwen embedding、evidence contract 与 COS 小批量私有同步底座已完成。

本 TODO 不代表整个 SecureHub 已完成。当前主问题是五条产品 endpoint 的真实联调与多智能体运行时
产品化，而不是新增第 10 个 agent。

## 1. 完成定义

阶段完成必须同时满足：

1. 五条产品主路径在真 Provider、真 RAG、真 agent_runs、前端 SSE 下可复现。
2. A3 演示主模型为讯飞星火；DeepSeek 仅作为开发联调和故障 fallback。
3. QualityCheck 可触发有界返工，而不是只做最终阻断。
4. workflow root、事件、上下文、生成物具备可恢复、可审计、可观测的持久化能力。
5. 不违反固定 9 agents、统一知识资产层、画像唯一源、RAG-before-LLM、agent_runs 落库等铁律。

## 2. 优先级总览

| ID | 优先级 | 工作包 | 负责人 | 依赖 | 完成状态 |
|---|---|---|---|---|---|
| MA-P0-01 | P0 | 五条产品主路径真实联调 | A + B，C 验收 | 已签收 Agent Run API | 未开始 |
| MA-P0-02 | P0 | 讯飞星火演示主链路 | A + B | Provider 家族、真实 RAG | 未开始 |
| MA-P1-01 | P1 | QualityCheck 有界返工图 | A | P0-01 真实输出契约 | 未开始 |
| MA-P1-02 | P1 | Durable workflow run 与恢复 | A | P0-01 运行语义冻结 | 未开始 |
| MA-P1-03 | P1 | 协作 artifact / context 持久化 | A + C | MA-P1-02 | 未开始 |
| MA-P1-04 | P1 | 运行可观测性与成本治理 | A + B + C | MA-P1-02 / 03 | 未开始 |
| MA-P2-01 | P2 | 用户介入、暂停、恢复、节点重跑 | A + B | MA-P1-02 | 未开始 |

## 3. P0：产品主路径真实联调

### MA-P0-01 五条产品主路径真实联调

**目标**：将已验证的 Agent Run 能力接入产品 API 和前端，而不是只保留一个固定 smoke workflow。

范围：

- courses/plan
- courses/resources/generate
- profile/chat
- tutor/ask
- assessment/run

执行清单：

- [ ] 冻结每条路径的 request、response、SSE event、错误码、evidence 与 agent_runs 契约。
- [ ] 将每条路径映射到既有 9 agent 的 skill / Harness / RAG，不新建业务 agent。
- [ ] 后端使用真实 Provider、真实 RAG、真实 agent_runs；fixture 仅保留显式开发模式。
- [ ] B 以 real-first DTO 接入，消除将 fallback 误当完成的状态。
- [ ] C 为每条路径提供 evidence、seed、契约和 demo smoke 验收支持。
- [ ] 为每条路径记录可追溯 run ID、provider/model、evidence IDs、child runs 与 SSE 终态。

验收：

- [ ] 每条路径有一次可复现的真 Provider + 真 RAG + 真 PostgreSQL agent_runs + 前端 SSE 成功证据。
- [ ] 全部路径的 error / blocked / cancelled 不会被前端显示为 success。
- [ ] SSE 事件只使用 progress / evidence / token / artifact / trace / done / error。
- [ ] 每条生成式 skill 先检索后调用模型，evidence 不足返回 InsufficientEvidence。

回滚：

- 以 feature flag 或 endpoint 级 provider mode 回退到显式 fixture；不修改真实数据和 agent 注册表。
- 按路径独立回滚，不回滚已签收 Agent Run API。

### MA-P0-02 讯飞星火演示主链路

**目标**：满足 A3 的星火主选模型要求，同时保留 DeepSeek 开发联调价值。

执行清单：

- [ ] 明确演示 workflow / endpoint 的 provider=xfyun 选择、health、限流、错误码和降级策略。
- [ ] 在同一输入下验证星火的 JSON / streaming / evidence / QualityCheck 兼容性。
- [ ] DeepSeek 只能作为星火不可用时的显式 fallback；UI、SSE、报告必须显示实际 provider/model。
- [ ] 演示脚本记录星火真调用证据，不泄露 Key、prompt 或完整用户数据。

验收：

- [ ] A3 演示路径实际显示 xfyun / spark 模型标识。
- [ ] 失败时 fallback 语义透明，不能把 DeepSeek 标成星火。
- [ ] 质量闸、evidence chain、agent_runs 在星火路径仍然成立。

## 4. P1：协同质量与运行时产品化

### MA-P1-01 QualityCheck 有界返工图

**目标**：从“质量闸阻断”升级为“可控协作修复”，不新增 agent。

执行清单：

- [ ] 为 QualityCheck 定义 defects 分类：evidence、事实、结构、教学相关性、安全。
- [ ] 在既有 workflow 中添加条件边：仅将可修复 defect 路由回对应既有 skill。
- [ ] 设置每个 root 的最大返工次数、token 预算、超时与最终 blocked 语义。
- [ ] 在 trace 中记录返工原因、父子 run 关系、前后质量分和 evidence 变化。

验收：

- [ ] 可修复 defect 触发一次或有限次数的真实返工，最终成功或明确 blocked。
- [ ] 不可修复 defect 不会无限循环、不会掩盖失败。
- [ ] 不改变 QualityCheck.accept=false 的保守终态语义。

### MA-P1-02 Durable workflow run 与恢复

**目标**：解决单进程内存 RunRegistry 无重启恢复的限制。

执行清单：

- [ ] 设计 workflow root 的持久化模型、状态机、幂等键、TTL、权限边界与迁移方案。
- [ ] 持久化 root 状态、节点状态、SSE cursor、cancel 状态、retry / rework 次数。
- [ ] 明确 Redis 的职责：缓存 / pubsub / event fan-out，不取代 PostgreSQL 的审计源。
- [ ] 定义进程重启、重复请求、重复 cancel、worker 超时、部分持久化失败的恢复策略。

验收：

- [ ] 服务重启后可查询已完成 / 已取消 root 的状态与历史事件。
- [ ] 重复 start 与 cancel 具备幂等行为。
- [ ] 多实例场景不会产生重复 child agent_runs 或乱序终态。

架构取舍：

- 成本是 schema、迁移、运维和回滚复杂度上升。
- 收益是长任务、多实例、演示稳定性和审计能力；在 P0 产品路径稳定后实施。

### MA-P1-03 协作 artifact 与 context 持久化

**目标**：让 agent 间交接不只存在内存和 SSE 中。

执行清单：

- [ ] 将可展示生成物写入 generated_resources，并通过 storage_objects 管理大文件。
- [ ] 定义 root / child 的 context snapshot、artifact version、evidence snapshot 和引用关系。
- [ ] 设计敏感信息最小化：不持久化 API key、完整 prompt、reasoning 或不必要的用户原文。
- [ ] 前端可从 run ID 回溯学习路径、课程文档、题目、证据和质量结论。

验收：

- [ ] 一个 completed root 可在新会话中恢复展示其 artifact、evidence 与质量结论。
- [ ] artifact 持久化失败时不发 artifact success SSE，不伪装为完成。

### MA-P1-04 运行可观测性与成本治理

**目标**：让多智能体系统可运营，而不是仅能成功一次。

执行清单：

- [ ] 建立 workflow / child 维度的延迟、成功率、blocked/failed 分类、token、成本、provider、模型、evidence 数、质量分指标。
- [ ] 建立统一错误 taxonomy：provider、RAG、schema、quality、persistence、cancel、timeout。
- [ ] 建立请求级预算、并发、限流、熔断和人工审计记录。
- [ ] 记录结构化摘要，不记录 Key、完整 prompt、reasoning 或敏感原文。

验收：

- [ ] 可按 workflow、agent、skill、provider、model 查询故障与成本趋势。
- [ ] 可定位一次错误 root 的阶段、错误码、evidence / quality 结果和相关 child runs。
- [ ] 告警不会泄露敏感内容。

## 5. P2：用户介入控制

### MA-P2-01 暂停、恢复、节点重跑

前置条件：MA-P1-02 已完成并稳定。

执行清单：

- [ ] 支持 root 级 pause / resume，且保证 cursor、context、artifact、token budget 一致。
- [ ] 仅允许在明确依赖边界内节点重跑；不重复写入 agent_runs / generated_resources。
- [ ] 提供人工审批点：高风险输出、成本超阈值、质量多次拒绝。
- [ ] 前端明确显示 queued / running / paused / reworking / blocked / cancelled / succeeded。

验收：

- [ ] 暂停/恢复不会造成重复模型调用或重复落库。
- [ ] 节点重跑仍满足 RAG、QualityCheck、agent_runs、evidence chain 铁律。

## 6. 工程治理要求

每个工作包必须具备：

1. 一个可回滚的设计说明或执行 Prompt。
2. 明确 owner、依赖、API/Schema 影响、数据迁移与回滚策略。
3. 真实路径的可追溯 run ID、provider/model、SSE 与数据库证据。
4. 对 fixture / real / fallback 的显式标签。
5. 不新增产品业务 agent；新能力优先落到既有 skill、workflow 条件边或横切基础设施。
6. 若修改铁律、schema、Harness contract 或差异说明，同步更新 CLAUDE.md 与 .codex\AGENTS.md。

## 7. 推荐执行顺序

~~~text
P0-01 五条产品主路径真实联调
        |
P0-02 星火演示主链路
        |
P1-01 QualityCheck 有界返工
        |
P1-02 Durable workflow run
        |
P1-03 artifact/context 持久化 ---- P1-04 可观测性与成本治理
        |
P2-01 用户介入控制
~~~

不建议先做 P2。没有 durable root 状态就做暂停、恢复、重跑，会把复杂度提前引入且难以可靠验收。

## 8. 主要风险

| 风险 | 预防策略 |
|---|---|
| 将 Agent Run API 成功误报为整个产品完成 | 五条 endpoint 分别保留真链路证据和验收门槛 |
| 为提升成功率放宽质量闸 | 只允许有界返工；accept=false 保持 blocked 语义 |
| 多模型输出契约漂移 | provider/model 显式标识；每个模型走同一结构化输出与 evidence 契约 |
| 多实例 / 重启产生重复副作用 | root 幂等键、child 幂等约束、事务和状态机 |
| 成本失控或无限返工 | root / node 级 token、次数、超时、并发预算 |
| 生成物和上下文失联 | artifact / context / evidence snapshot 持久化与版本关联 |

## 9. 最小阅读集

日常只读：

1. CLAUDE.md
2. .codex\AGENTS.md
3. Plan\2026-07-10_SecureHub_权威规划凝练索引.md
4. Plan\2026-07-10_SecureHub_执行轨迹凝练索引.md
5. 本文件

涉及 Agent Run 已签收能力时，额外读：
Plan\2026-07-10_Agent_Run_API_真实闭环凝练索引.md。

需要改具体契约或实现时，再按凝练索引中的 source:line 回读原文，不默认展开历史 Prompt / Workout。


