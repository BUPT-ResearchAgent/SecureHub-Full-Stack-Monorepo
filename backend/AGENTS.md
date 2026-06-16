# backend/AGENTS.md — SecureHub 后端局部规则

> 父文档：仓库根 `AGENTS.md`；项目宪法：`CLAUDE.md`。
> 本文件只描述后端目录内的局部约束，不复述全局铁律。

---

## 1. 技术栈

| 层 | 选择 |
|---|---|
| Web 框架 | FastAPI |
| 语言 | Python 3.11+ |
| 包管理 | uv（不要用 pip / poetry） |
| 模型层 | Pydantic v2 |
| ORM | SQLAlchemy 2.0 async |
| 迁移 | Alembic |
| DB | PostgreSQL 16 + pgvector |
| 缓存 / Pub-Sub | Redis 7 |
| LLM | 讯飞星火（A3 主选）/ DeepSeek（联调主选）/ Qwen（备） |
| 编排 | LangGraph + 自研 Harness |
| 流式 | SSE（7 事件协议：progress / evidence / token / artifact / trace / done / error） |

---

## 2. 目录边界

| 目录 | 用途 | 谁修改 |
|---|---|---|
| `app/api/v1/endpoints/` | HTTP endpoint 薄适配 | B（应用集成）+ A（service 层依赖时） |
| `app/services/` | 业务编排 | A（agent / resources）+ C（knowledge） |
| `app/repositories/` | 持久化适配 | A 主写 |
| `app/agents/` | 9 业务智能体 + skill | **A 唯一** |
| `app/runtime/` | Harness / graphs / guardrails / router | **A 唯一** |
| `app/rag/` | 检索 / 切片 / 证据 / reranker | **A 唯一** |
| `app/llm/` | Provider 客户端 + Router | **A 唯一** |
| `app/knowledge/loaders/` | 各 domain 离线 loader | **C 唯一** |
| `app/db/models/` | ORM 模型 | A + C 协商，单 PR |
| `app/db/migrations/` | Alembic 迁移 | A + C 协商，单 PR |
| `app/db/seeds/` | seed 数据 | **C 唯一** |
| `app/schemas/` | Pydantic DTO | B 主写、A + C review |
| `app/streaming/` | SSE 事件定义 + 包装 | A 主写 |

---

## 3. 必须遵守

### 3.1 文件顶部 Status 注释（强制）

每个新增 endpoint / service / repository / agents 下文件，顶部必须写：

```python
# Status: real         # 完全真实实现
# Status: partial-real # 部分真实 + 部分 mock
# Status: mock         # 全部 mock
# Status: planned      # 仅占位
```

### 3.2 生成式 skill 必须走 Harness（强制）

```
SkillContract.input_schema
  → rag.retrieve(domain, query, top_k)
  → evidence_floor 检查（< 3 chunks 抛 InsufficientEvidence）
  → compose prompt
  → llm_provider.generate() / stream_generate()
  → parse output
  → outcome_evaluator.quality_check
  → 写入 generated_resources + storage_objects
  → ctx.log_run(agent_runs)
```

不允许：
- 跳过 `rag.retrieve` 直接调 LLM
- 跳过 `quality_check` 直接返回给用户
- 跳过 `log_run` 写 `agent_runs`
- 把生成物写回 `documents` 表

### 3.3 不新增业务智能体（强制）

9 个业务智能体固定。新能力作为现有 agent 的新 skill 实现：

```
backend/app/agents/<existing_agent_name>/skills/<new_skill>.py
```

绝不创建：`backend/app/agents/<new_agent>/`。

### 3.4 不新增 per-domain chunk 表（强制）

所有 domain（`course_websec` / `policy` / `fund` / `job` / `competition` 等）共用：

- `documents`
- `document_assets`
- `chunks`
- `knowledge_nodes`
- `knowledge_edges`

按 `domain` 字段过滤。禁止建 `course_chunks` / `policy_chunks` / `bilibili_documents` 等并列表。

### 3.5 采集合规（强制）

任何采集适配器必须保留：

```
platform / source_url / author / published_at / fetched_at / license / rights_note
```

禁止：绕登录 / 绕验证码 / 绕 Cloudflare / 反爬规避 / 代理池 / 高并发抓取 / 批量重托管版权内容。

---

## 4. 推荐验证命令

```bash
# 类型 + 单元 + smoke（默认 CI 跑这个）
uv run pytest -m "not llm_live"

# 加跑真 LLM 测试（手动触发，消耗额度）
export ENABLE_LLM_LIVE_TESTS=true
export LLM_PROVIDER=deepseek
export DEEPSEEK_API_KEY=***
uv run pytest -m llm_live

# 本地 dev server
./start.sh
# 或
uv run uvicorn app.main:app --reload

# 应用迁移
uv run alembic upgrade head
```

---

## 5. Codex 子智能体建议

修改本目录代码时优先：

- 主写：`securehub_backend_rag_worker`
- 收尾审查：`securehub_review_qa`
- 复杂变更前置规划：`securehub_planner`

不要默认调 `securehub_frontend_worker`，除非任务明确涉及前后端联调字段。

---

## 6. 引用

- 项目宪法：`CLAUDE.md`
- 后端架构：`docs/backend-overview.md`
- Harness 迁移审计：`docs/governance/harness-migration-audit.md`
- 数据层 v2 enum：`docs/data-layer-v2-enums.md`
- LLM 接入策略：`Plan/SecureHub_三人工程化分工与真实LLM接入规划.md` §7
