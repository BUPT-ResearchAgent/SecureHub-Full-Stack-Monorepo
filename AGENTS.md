# AGENTS.md — SecureHub Codex 子智能体使用约定

> 权威文档：`CLAUDE.md` 是项目宪法，本文件不复述细节，仅约束 Codex 子智能体的使用边界。
> 文档冲突时以 `CLAUDE.md` 为准。
> 最后更新：2026-07-14（Runtime v1.1 Wave 0-6 与 A3-S5~S7 均已 `real-accepted`；S8 保持 `planned` + `external-gate-open` 并暂缓执行，当前优先赛前 PPT/试题/可视化/证据评分准备）。

---

## 0. 默认上下文读取策略（2026-07-12）

不要默认全量读取 Layer B 长规划文件或 Layer C Prompt / Workout。日常判断当前阶段、三人分工、进度、瓶颈、LLM / Embedding / COS / data-layer 决策时，先读：

```text
D:/Nnutural/Desktop/BUPT大全/BUPT竞赛/26软件杯/Plan/2026-07-10_SecureHub_权威规划凝练索引.md
D:/Nnutural/Desktop/BUPT大全/BUPT竞赛/26软件杯/Plan/2026-07-10_SecureHub_执行轨迹凝练索引.md
D:/Nnutural/Desktop/BUPT大全/BUPT竞赛/26软件杯/Plan/2026-07-11_SecureHub_多智能体底层完整架构实施方案.md
D:/Nnutural/Desktop/BUPT大全/BUPT竞赛/26软件杯/Plan/2026-07-13_SecureHub_A3产品化阶段2-8实施规划.md
Workout/Agent-Runtime-Wave-4-6.md
TODO.md
```

任务涉及 PPT、课程试题、资料可视化、案例/测试证据或竞赛评分时，再读：

```text
D:/Nnutural/Desktop/BUPT大全/BUPT竞赛/26软件杯/Plan/2026-07-14_SecureHub_赛前突击准备包规划.md
```

只有当任务需要追证具体决策、修改契约、验收某一轮交付或生成新执行提示词时，才按索引中的 `file_path:line_number` 回读源文件。

涉及旧 Agent Run API 的历史追证时，再额外读：

~~~text
D:/Nnutural/Desktop/BUPT大全/BUPT竞赛/26软件杯/Plan/2026-07-10_Agent_Run_API_真实闭环凝练索引.md
~~~

它替代 Agent-Run 原始 Plan / Prompt / Workout 的逐份阅读。当前 RuntimeEngine、HTTP/SSE 与五条产品路径以
`docs/api/workflow-run-contract.md`、Wave 4-6 报告和 v1.1 架构方案为准。

## 0.1 当前阶段口径（2026-07-14）

子智能体在审查、写码、起草报告时统一使用以下表述：

| 对象 | 正确口径 | 禁用口径 |
|---|---|---|
| Runtime v1.1 | Wave 0-6 代码、契约与本地验收完成；RuntimeEngine/StateMachine/SkillExecutor/PostgreSQL Event Store 是生产唯一权威。 | "还卡 Harness Wave 2"、"LangGraph 负责生产 checkpoint/resume" |
| 五条产品路径 | 五路径均以 `real / deepseek / deepseek-v4-pro` succeeded，17 条 `agent_runs`/Provider Call 与 SSE replay 对齐。 | "五条路径仍待真实联调"、"fixture replay 等于真实验收" |
| DeepSeek cancel | Root `2daf935b-e3b7-4dbe-af34-d792dffc66d3` 为 `cancelled`，21 条 live/replay SSE 一致，终态后无 token/artifact。 | "这是 Spark cancel"、"provider_switches=0 是 fallback" |
| Spark Gate | Spark bearer key 为空；Spark primary、首 token 后受控中断、DeepSeek replacement 与 Spark cancel 均未执行。 | "Spark 已通过"、"用无效 key 或 fixture 制造 fallback 成功" |
| COS / Storage | 2026-07-12 COS Runtime 已真实通过 upload/head/download/signed URL/delete；历史 451 仅为旧记录。GitHub 外 data 仍只确认 20 个既有同步样本，约 870 个对象未全量完成。 | "COS 仍被 451 阻塞"、"所有 data 已上传 COS"、"storage 是一个 agent" |
| A3-S5~S7 | S5 assessment/persona/path refresh、S6 current-root Evidence/Trace/Provider replay、S7 fund loader/DeepSeek Research 链均已 `real-accepted`；S7 入口为 `POST /api/v1/research/fund-recommendations`，以 CurrentUser 绑定画像归属。 | "S5-S7 仍只有工程验收"、"浏览器可传 user_id"、"Spark Gate 阻断 S5-S7" |
| 当前调度 | S8 保持 `planned` + `external-gate-open` 但暂缓执行；当前优先赛前 PPT/试题 Skill 评估、curated fallback、资料可视化和数据/案例/测试评分证据。 | "S8 已启动"、"S8 已取消"、"PPT 完成等于 Spark Gate 通过" |

正式生命周期为 `planned -> in_progress -> code_complete -> engineering-accepted -> real-accepted`。`external-gate-open` 仅是正交 Gate 标记；“暂缓”只是资源调度，不新增状态。S8 的 Spark Gate 仍真实开放但当前不排期。DeepSeek/Skill 产物未达质量线时可使用显式 `pre-generated/curated` 内容，禁止冒充 live 或 fixture。COS Runtime gate 与 GitHub 外 data 全量同步仍是两个范围。

当前验收快照：migration head `20260712_1040`，全量回归 `230 passed, 3 skipped`，最终证据提交 `89a6e0e1`。详细 root/SSE/Provider/COS 证据以 `Workout/Agent-Runtime-Wave-4-6.md` 为准。

---

## 1. Codex 子智能体 ≠ SecureHub 产品运行时业务智能体

### 1.1 两者必须严格区分

| 维度 | Codex 子智能体（本文件约束的对象） | SecureHub 产品运行时业务智能体 |
|---|---|---|
| 用途 | 开发辅助、写码、文档、审查 | 产品功能（画像 / 资源生成 / 评估 / 辅导） |
| 注册位置 | `.codex/agents/*.toml` | `backend/app/agents/`、`agents` 表 |
| 调用方 | 开发者、Codex CLI、Claude Code | Product Adapter → WorkflowApplicationService → RuntimeEngine → SkillExecutor；LangGraph 仅可作 topology adapter |
| 是否可新增 | 可（如有真实开发场景需要） | **绝对不可**（固定 9 个） |

### 1.2 9 个产品运行时业务智能体固定不变

```
policy_interpreter / hot_analyst / job_analyst / competition_advisor / career_planner /
topic_explorer / doc_archivist / task_orchestrator / outcome_evaluator
```

绝对不允许：
- 在 `backend/app/agents/` 下新建第 10 个 agent 目录
- 在 `agents` 表插入第 10 行
- 把横切基础设施注册成业务智能体：
  - 禁止：`crawler_agent` / `media_agent` / `spider_agent` / `pdf_agent` / `mineru_agent` / `harness_agent` / `storage_agent`
  - 这些都是 `services/`、`runtime/`、`knowledge/` 下的中间件，不进 `agents` 表；Tencent COS 也只是 `services/storage` provider

---

## 2. Codex 子智能体清单（5 个）

存放位置：`.codex/agents/`

| 名称 | 模式 | 模型 | 推理强度 | 调用时机 |
|---|---|---|---|---|
| `securehub_planner` | read-only | gpt-5.5 | xhigh | 复杂垂直切片、架构 / DB / Harness / RAG 边界判断 |
| `securehub_backend_rag_worker` | workspace-write | gpt-5.5 | xhigh | 后端 / RAG / Data / Harness 实现 |
| `securehub_frontend_worker` | workspace-write | gpt-5.5 | high | 前端实现、UI 修复、API 对接 |
| `securehub_review_qa` | read-only | gpt-5.4 | xhigh | 契约 / 测试 / SSE / 回归审查 |
| `securehub_docs_delivery` | workspace-write | gpt-5.4 | xhigh | 文档、AGENTS.md、交付材料 |

详细调用策略见 `.codex/workflows/subagent-playbook.md`。

---

## 3. 必须遵守的工程规则

新增任何后端 endpoint / service / repository 文件，顶部必须有：

```python
# Status: real    # 完全真实实现
# Status: partial-real    # 部分真实 + 部分 mock
# Status: mock    # 全部 mock
# Status: planned    # 仅占位
```

生成式 Skill 必须经过唯一 SkillExecutor，禁止裸调 LLM 或 direct `skill.run()`：

```
validate → guardrail → real RAG → evidence floor/snapshot → ContextBuilder
→ Provider Call Journal/Provider → strict parse → Candidate Output
→ 显式 `outcome_evaluator.QualityCheck` Workflow Node
→ bounded rework 或 Artifact Saga/Workflow Action
```

每个被接受的 Skill 调用必须经 AgentRunRecorder 持久化 `agent_runs`。证据不足时返回 `InsufficientEvidence`，real 不允许降级到 fixture。

所有外部来源必须保留：`platform / source_url / author / published_at / fetched_at / license / rights_note`。

统一知识资产层：所有 domain 共用 `documents + document_assets + chunks + knowledge_nodes + knowledge_edges`，禁止建并列表（`course_chunks` / `policy_chunks` / `bilibili_chunks` 等）。

对象存储规则：`runtime/` 用于应用运行时产物，`tmp/` 用于 smoke / 临时上传，`private/team-sync/` 用于团队私有同步。禁止上传 `.env*`、`SecretKey.csv`、`account.csv`、`.codegraph/**`、sqlite/db、raw MediaCrawler 数据；教材 PDF / `full.md` 只能在项目负责人明确确认后单独私有同步。

---

## 4. 额度友好策略

Codex 子智能体可能消耗高额度。本项目默认按"最小调用集"派发：

| 场景 | 默认 agent 集 |
|---|---|
| 小型前端修复 | `frontend_worker` only |
| 小型后端修复 | `backend_rag_worker` only |
| PR 审查 | `review_qa` only |
| 复杂垂直切片 | `planner` → `backend_rag_worker` + `frontend_worker` → `review_qa` |
| 交付文档 | `docs_delivery` only |

**绝不默认全量启动 5 个 agent**。

并发约束：

- `max_threads = 4`
- `max_depth = 1`
- read-heavy 任务可并行；write-heavy 不要并行改同一文件范围

---

## 5. 常用命令

### 前端

```bash
cd frontend
npm install
npm run dev        # 默认 5173
npm run build
```

### 后端

```bash
cd backend
uv sync
./start.sh          # 或：uv run uvicorn app.main:app --reload
uv run pytest       # 跳过 live LLM 测试：uv run pytest -m "not llm_live"
```

### 基础设施

```bash
docker compose up   # 启动 PostgreSQL / Redis / 其他依赖
```

---

## 6. 跨层修改 SOP

涉及以下修改时，必须同步更新 `CLAUDE.md` 与 `.codex/AGENTS.md`：

- 8 条铁律的字面修改
- 数据层 schema 变更
- 横切基础设施边界变化（rag / harness / guardrails / storage）
- 9 个业务智能体的 skill 增删
- COS 前缀策略 / GitHub 外 data 同步口径 / 上传门禁规则变化
- Runtime Wave、真实 Provider/RAG/COS Gate 或主要瓶颈变化时，还必须同步项目根
  `Plan/Leader-Prompt.md`、本文件、`TODO.md` 与对应 `Workout` 交付报告

---

## 7. 本文件维护

- 维护者：`securehub_docs_delivery` 或项目负责人
- 与 `CLAUDE.md` 冲突时以 `CLAUDE.md` 为准
- 新增 Codex 子智能体时同步更新本文件 §2 表格
