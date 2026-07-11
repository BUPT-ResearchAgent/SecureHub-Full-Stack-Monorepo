<div align="center">

# SecureHub

**安枢智梯 | 面向网络安全人才培养的智能化产教研融合中枢**

[![CI](https://github.com/Nnutural/SecureHub-Full-Stack-Monorepo/actions/workflows/ci.yml/badge.svg?branch=dev)](https://github.com/Nnutural/SecureHub-Full-Stack-Monorepo/actions/workflows/ci.yml?query=branch%3Adev)

[快速开始](#快速开始) · [系统架构](#系统架构) · [开发验证](#开发验证) · [文档索引](#文档索引)

</div>

SecureHub 将网络安全学习、竞赛备赛、科研创新和就业发展组织为可追溯的智能化工作流。项目以“基于多智能体的个性化课程学习”为软件杯 A3 主线，同时提供政策、热点、岗位、竞赛、选题、写作和任务协同等中枢能力。

> [!IMPORTANT]
> SecureHub 当前处于真实联调校准期。固定五节点 Agent Run 已完成真 Provider、真 RAG、PostgreSQL `agent_runs`、SSE replay 和取消流程的专项验收；课程规划、资源生成、画像对话、智能辅导和评估五条产品主路径仍在进行端到端复跑与契约收敛。演示回放或前端 fallback 不等于全部在线能力已经验收。

## 产品预览

### 课程学习演示

<p align="center">
  <img src="./docs/assets/readme/demo-course-flow.gif" alt="SecureHub 课程学习与资源工作台演示" width="800" />
</p>

<p align="center"><sub>竞赛演示录制片段：学习路径、资源工作台与生成过程。GIF 不包含音频，完整视频不随仓库分发。</sub></p>

### 界面设计参考

<p align="center">
  <img src="./docs/assets/readme/workspace-overview.jpg" alt="SecureHub 总览工作台设计" width="49%" />
  <img src="./docs/assets/readme/topic-advisor.jpg" alt="SecureHub 智能问答与选题指导设计" width="49%" />
</p>

<p align="center"><sub>竞赛材料中的产品界面设计，用于说明信息密度、工作台和证据链交互方向。</sub></p>

## 核心能力

| 能力域 | 用户价值 | 工程保障 |
| --- | --- | --- |
| 个性化课程学习 | 通过对话画像、学习路径、资源工作台、辅导和测验构成学习闭环 | `user_profiles` 与 `user_capabilities` 作为跨模块唯一画像来源 |
| 多智能体协同 | 将政策、热点、岗位、竞赛、选题、文档、任务和评价能力组合为统一流程 | 固定 9 个产品智能体；运行时基础设施不计入智能体数量 |
| 证据驱动生成 | 课程文档、PPT、思维导图、练习题、实操和视频脚本等资源按证据链生成 | `validate → retrieve → evidence floor → generate → quality check → persist → log_run` |
| 可追踪流式体验 | 将长耗时生成转为可观察的进度、证据、内容、产物与执行轨迹 | SSE 统一使用 `progress`、`evidence`、`token`、`artifact`、`trace`、`done`、`error` 事件 |
| 产教研融合中枢 | 将学习主线延伸到科研选题、竞赛指导、岗位洞察和任务清单 | 学生端与教师端均有独立工作区和路由边界 |

### 固定的产品智能体

| 分组 | 智能体 |
| --- | --- |
| 信息与研判 | `policy_interpreter`、`hot_analyst`、`job_analyst`、`competition_advisor` |
| 规划与产出 | `career_planner`、`topic_explorer`、`doc_archivist`、`task_orchestrator`、`outcome_evaluator` |

`rag`、数据采集、运行时调度、安全护栏、Harness 和对象存储均为横切基础设施，不会被包装成额外的产品智能体。

## 系统架构

```mermaid
flowchart TB
    Browser["浏览器"] --> Frontend["React 18 · Vite 6 · TypeScript"]
    Frontend <-->|"REST / SSE"| API["FastAPI /api/v1"]

    subgraph Runtime["运行时与协作层"]
        Workflow["工作流编排与状态管理"]
        Agents["9 个固定产品智能体"]
        Evidence["RAG 检索 · Evidence Floor · QualityCheck"]
        Providers["Provider 抽象：讯飞星火 / DeepSeek"]
        Workflow --> Agents
        Workflow --> Evidence
        Workflow --> Providers
    end

    API --> Workflow
    Evidence --> Knowledge[("PostgreSQL 16 + pgvector")]
    Workflow --> Knowledge
    Workflow --> Audit[("agent_runs / 生成物元数据")]
    API --> Redis["Redis：事件扇出与缓存"]
    Workflow --> Storage["本地存储 / Tencent COS"]
```

运行时的关键原则是“先证据、后生成、可追溯”：生成式 Skill 只有在检索证据达到阈值后才可进入 Provider 调用；无证据时返回 `InsufficientEvidence`，而不是静默退化为无依据生成。每次执行都应沉淀 `agent_runs`、证据引用和产物元数据。

### 数据治理设计参考

<p align="center">
  <img src="./docs/assets/readme/data-governance-design.png" alt="合规策略驱动的多源异构信息获取与可信输出设计" width="100%" />
</p>

<p align="center"><sub>竞赛材料中的数据治理与可信输出设计参考。实际运行时边界以本 README 上述拓扑及仓库工程约束为准。</sub></p>

## 仓库结构

```text
.
├─ frontend/              # React + Vite 前端，学生端、教师端与演示体验
├─ backend/               # FastAPI、领域服务、RAG、运行时与数据库迁移
├─ docs/                  # API 契约、演示清单、架构与治理资料
│  └─ assets/readme/      # README 展示素材
├─ scripts/               # 本地开发、演示 smoke、资料处理辅助脚本
├─ docker-compose.yml     # PostgreSQL、Redis、前端和后端本地编排
├─ AGENTS.md              # 工程约束与当前阶段口径
└─ CLAUDE.md              # 项目上下文与架构规则
```

## 快速开始

### 前置条件

| 运行方式 | 需要的软件 |
| --- | --- |
| 推荐：完整本地栈 | Docker Desktop / Docker Compose v2 |
| 前端单独开发 | Node.js 22、Corepack、pnpm 9 |
| 后端单独开发 | Python 3.11+、`uv`、PostgreSQL 16、Redis 7 |

### 启动完整本地栈

```bash
git clone https://github.com/Nnutural/SecureHub-Full-Stack-Monorepo.git
cd SecureHub-Full-Stack-Monorepo
docker compose up --build
```

首次启动会下载基础镜像和依赖。服务就绪后：

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| OpenAPI | http://localhost:8000/docs |
| PostgreSQL（宿主机） | `127.0.0.1:15432` |
| Redis（宿主机） | `127.0.0.1:6379` |

停止并移除本地容器：

```bash
docker compose down
```

### PowerShell 手动开发

先启动基础服务：

```powershell
docker compose up -d postgres redis
```

在一个终端启动后端。Compose 将 PostgreSQL 映射到宿主机 `15432`，因此手动运行时必须覆盖默认数据库地址：

```powershell
cd backend
$env:DATABASE_URL = "postgresql+asyncpg://securehub:securehub@127.0.0.1:15432/securehub"
$env:REDIS_URL = "redis://127.0.0.1:6379/0"
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

在另一个终端启动前端：

```powershell
cd frontend
corepack enable
pnpm install --frozen-lockfile
pnpm dev
```

### 配置真实 Provider

后端通过环境变量读取配置；请在被忽略的 `backend/.env.local` 或部署环境中设置凭据，绝不提交密钥。活跃配置面以 [`backend/app/core/config.py`](./backend/app/core/config.py) 为准。

| 配置类别 | 关键变量 | 用途 |
| --- | --- | --- |
| 大模型 | `LLM_PROVIDER`、`XFYUN_*`、`DEEPSEEK_API_KEY` | 讯飞星火是 A3 演示要求；DeepSeek 用于开发与透明 fallback 策略 |
| 向量化 | `DASHSCOPE_API_KEY`、`DASHSCOPE_OPENAI_COMPATIBLE_BASE_URL` | Qwen `text-embedding-v4` 的真实检索配置 |
| 存储 | `STORAGE_PROVIDER`、`COS_*` | 本地存储或私有 Tencent COS |
| 运行时 | `MIN_EVIDENCE`、`AGENT_RUN_REAL_ENABLED` | 证据门槛与真实执行开关 |

> [!CAUTION]
> Live LLM 测试默认不进入 CI。没有经过批准的凭据与预算时，请使用 fixture / 演示路径，不要伪造“真实调用已通过”的结论。

## 开发验证

CI 使用 Node.js 22、pnpm 9、`uv`、PostgreSQL 和 Redis。提交前可运行与 CI 对齐的最小检查：

```powershell
# 前端
cd frontend
pnpm install --frozen-lockfile
pnpm typecheck
pnpm build

# 后端（需要可用的 PostgreSQL 与 Redis）
cd ..\backend
uv sync --frozen
uv run alembic upgrade head
uv run pytest -m "not llm_live" -q

# Compose 配置校验
cd ..
docker compose config
```

演示回归可使用：

```powershell
.\scripts\demo_smoke.ps1
```

该脚本会调用本地服务、写入临时运行数据，并依赖已准备好的数据库与课程 seed；它适合演示前的 smoke，而不是无状态的纯前端检查。

## 当前状态与边界

| 范围 | 当前结论 |
| --- | --- |
| 固定 Agent Run | 已完成真实闭环专项验收：固定五节点 workflow、真 RAG、真 Provider、`agent_runs`、SSE replay 和 token 后取消 |
| 五条产品主路径 | `courses/plan`、`courses/resources/generate`、`profile/chat`、`tutor/ask`、`assessment/run` 正在进行真实端到端联调和契约收敛 |
| 前端接入 | 已有 typed SSE、real-first API 与错误状态；部分场景仍提供显式 mock / 演示 fallback |
| COS | Provider 与私有同步链路已验证；不应将小批量同步样本表述为 GitHub 外数据已全量上云 |

这一区分是项目质量门槛的一部分：可播放的 UI、mock 回放和真实 Provider/RAG/数据库/SSE 的同窗验证是不同层次的证据。

## 文档索引

| 文档 | 说明 |
| --- | --- |
| [工程约束与阶段口径](./AGENTS.md) | 固定 9 Agent、证据门槛、数据边界和当前联调状态 |
| [项目上下文](./CLAUDE.md) | 技术栈、架构铁律和历史决策 |
| [课程主路径 API 契约](./docs/api/course-contract.md) | 课程、画像、RAG、资源生成、辅导与评估接口 |
| [证据契约](./docs/api/evidence-contract.md) | 证据字段、来源与可追溯性约束 |
| [演示 Checklist](./docs/demo/seven-minute-demo-checklist.md) | 7 分钟演示分镜、素材和验收门禁 |
| [CI 工作流](./.github/workflows/ci.yml) | 前端、后端、规则与 Compose 校验命令 |

## 开发与数据治理

- 不新增第 10 个产品智能体；RAG、采集、存储和安全护栏保持为基础设施。
- 新增生成能力必须经过检索、证据阈值、质量复核、产物持久化与 `agent_runs` 审计链。
- 外部资料需要保留来源、作者、时间、授权和权利说明；不绕过登录、验证码或反自动化机制。
- 不提交 `.env`、密钥、数据库文件、原始受版权保护资料或用户数据。

## 许可证

仓库当前未提供顶层 `LICENSE` 文件。在项目维护者明确授权前，请勿将其作为可再分发依赖或独立开源组件使用。
