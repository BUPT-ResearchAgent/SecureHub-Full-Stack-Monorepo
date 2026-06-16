# AGENTS.md — SecureHub Codex 子智能体使用约定

> 权威文档：`CLAUDE.md` 是项目宪法，本文件不复述细节，仅约束 Codex 子智能体的使用边界。
> 文档冲突时以 `CLAUDE.md` 为准。

---

## 1. Codex 子智能体 ≠ SecureHub 产品运行时业务智能体

### 1.1 两者必须严格区分

| 维度 | Codex 子智能体（本文件约束的对象） | SecureHub 产品运行时业务智能体 |
|---|---|---|
| 用途 | 开发辅助、写码、文档、审查 | 产品功能（画像 / 资源生成 / 评估 / 辅导） |
| 注册位置 | `.codex/agents/*.toml` | `backend/app/agents/`、`agents` 表 |
| 调用方 | 开发者、Codex CLI、Claude Code | 9 智能体之间互调、LangGraph 编排 |
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
  - 这些都是 `services/`、`runtime/`、`knowledge/` 下的中间件，不进 `agents` 表

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

生成式 skill 必须经过 Harness 链路（不得裸调 LLM）：

```
validate → rag.retrieve → evidence_floor → llm → quality_check → generated_resources / storage_objects → agent_runs
```

证据不足时返回 `InsufficientEvidence`，不允许偷偷降级到 mock。

所有外部来源必须保留：`platform / source_url / author / published_at / fetched_at / license / rights_note`。

统一知识资产层：所有 domain 共用 `documents + document_assets + chunks + knowledge_nodes + knowledge_edges`，禁止建并列表（`course_chunks` / `policy_chunks` / `bilibili_chunks` 等）。

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

---

## 7. 本文件维护

- 维护者：`securehub_docs_delivery` 或项目负责人
- 与 `CLAUDE.md` 冲突时以 `CLAUDE.md` 为准
- 新增 Codex 子智能体时同步更新本文件 §2 表格
