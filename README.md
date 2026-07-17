<p align="center">
  <img
    src="./design/brand/exports/readme-banner.png"
    alt="安枢智梯 SecureHub：面向网络安全人才培养的开源智能学习与科研平台"
    width="100%"
  />
</p>

<div align="center">

[![CI](https://github.com/BUPT-ResearchAgent/SecureHub-Full-Stack-Monorepo/actions/workflows/ci.yml/badge.svg?branch=dev)](https://github.com/BUPT-ResearchAgent/SecureHub-Full-Stack-Monorepo/actions/workflows/ci.yml?query=branch%3Adev)
[![Frontend](https://img.shields.io/badge/frontend-React%2018-149eca?logo=react&logoColor=white)](./frontend)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688?logo=fastapi&logoColor=white)](./backend)
[![Data](https://img.shields.io/badge/data-PostgreSQL%2016%20%2B%20pgvector-4169E1?logo=postgresql&logoColor=white)](./docker-compose.yml)
[![Stage](https://img.shields.io/badge/stage-integration%20validation-EAB308)](#当前状态与路线图)

[核心能力](#核心能力) · [概览](#概览) · [体验](#体验) · [产品模块](#产品模块) · [系统架构](#系统架构) · [快速开始](#快速开始) · [接口与事件](#接口与事件) · [开发验证](#开发验证) · [文档索引](#文档索引)

</div>

SecureHub 将网络安全学习、竞赛备赛、科研创新和就业发展组织为可追溯的智能化工作流。项目以“基于多智能体的个性化课程学习”为软件杯 A3 主线，同时提供政策、热点、岗位、竞赛、选题、写作和任务协同等中枢能力。

## 核心能力

<table>
  <tr>
    <td align="center" width="33%">
      <img src="./design/brand/icons/knowledge-base.svg" alt="" width="32" />
      <br />
      <strong>知识组织</strong>
      <br />
      <sub>统一组织课程、文档、证据与领域知识资产</sub>
    </td>
    <td align="center" width="33%">
      <img src="./design/brand/icons/learning-path.svg" alt="" width="32" />
      <br />
      <strong>学习路径</strong>
      <br />
      <sub>基于画像、知识节点与能力反馈规划个性化进阶路径</sub>
    </td>
    <td align="center" width="33%">
      <img src="./design/brand/icons/security-lab.svg" alt="" width="32" />
      <br />
      <strong>安全实验</strong>
      <br />
      <sub>连接教程、工具、题目、竞赛与受控实战环境</sub>
    </td>
  </tr>
  <tr>
    <td align="center" width="33%">
      <img src="./design/brand/icons/agent-collaboration.svg" alt="" width="32" />
      <br />
      <strong>智能体协作</strong>
      <br />
      <sub>由固定产品智能体协同完成分析、规划与成果生成</sub>
    </td>
    <td align="center" width="33%">
      <img src="./design/brand/icons/research.svg" alt="" width="32" />
      <br />
      <strong>科研创新</strong>
      <br />
      <sub>支持科研机会发现、选题推演、写作与成果沉淀</sub>
    </td>
    <td align="center" width="33%">
      <img src="./design/brand/icons/talent-development.svg" alt="" width="32" />
      <br />
      <strong>人才培养</strong>
      <br />
      <sub>贯通学习、竞赛、科研与就业的能力成长闭环</sub>
    </td>
  </tr>
</table>

## 概览

| 维度 | SecureHub 的做法 |
| --- | --- |
| 产品定位 | 将“学习 - 竞赛 - 科研 - 就业”从分散的信息流收敛为面向网络安全人才培养的统一工作台 |
| 学习主线 | 对话画像、个性化学习路径、资源工作台、智能辅导、测验和能力回流 |
| 协作模型 | 9 个固定产品智能体按职责协作；RAG、Harness、存储、采集和安全护栏保持为横切基础设施 |
| 可信生成 | 证据先行、来源可查、质量复核、产物持久化与 `agent_runs` 审计串联为一条链路 |
| 交互形态 | React 单页应用通过 REST 与 7 类 SSE 事件呈现实时进度、证据、内容、产物和运行轨迹 |
| 工程基座 | FastAPI、PostgreSQL 16 + pgvector、Redis、Qwen 向量化、Provider 抽象及本地/Tencent COS 存储 |

### 面向谁

| 角色 | 典型任务 | 主要入口 |
| --- | --- | --- |
| 学生 | 构建学习画像、学习 Web 安全、生成课程资源、做题复盘、形成作品与求职行动 | `/course`、`/practice`、`/research`、`/careers` |
| 教师与导师 | 查看班级能力画像、维护课程与教材、管理题库/作业、开展科研或职业指导 | `/teacher/*` |
| 项目协作者 | 维护证据契约、调试工作流、审查运行记录、验证演示闭环与工程门禁 | `/workspace`、`/showcase`、`/docs` |

> [!IMPORTANT]
> **项目状态需要按证据分层理解。** 固定五节点 Agent Run 已完成真 Provider、真 RAG、PostgreSQL `agent_runs`、SSE replay 和取消流程的专项验收；课程规划、资源生成、画像对话、智能辅导和评估五条产品主路径仍在进行端到端复跑与契约收敛。可播放的 UI、mock 回放和真实 Provider/RAG/数据库/SSE 的同窗验证不是同一种证据。

## 体验

### 课程学习演示

<p align="center">
  <img src="./docs/assets/readme/demo-course-flow.gif" alt="SecureHub 课程学习、学习路径和资源工作台演示" width="800" />
</p>

<p align="center"><sub>竞赛演示录制片段：从学习路径进入资源工作台与生成过程。GIF 不包含音频，完整视频不随仓库分发。</sub></p>

### 产品界面设计参考

<p align="center">
  <img src="./docs/assets/readme/workspace-overview.jpg" alt="SecureHub 总览工作台设计" width="32%" />
  <img src="./docs/assets/readme/topic-advisor.jpg" alt="SecureHub 智能问答与选题指导设计" width="32%" />
  <img src="./docs/assets/readme/task-board.jpg" alt="SecureHub 任务看板设计" width="32%" />
</p>

<p align="center"><sub>竞赛材料中的产品界面设计参考：总览、智能问答/选题指导与跨模块任务协同。</sub></p>

### 一条完整的学习闭环

```mermaid
flowchart LR
    Persona["对话画像\n6+ 维特征"] --> Path["个性化\n学习路径"]
    Path --> Workbench["资源工作台\n文档/PPT/导图/题目/实操/视频"]
    Workbench --> Tutor["智能辅导\n证据可见"]
    Tutor --> Assess["测验与\n能力评估"]
    Assess --> Capability["能力回流\n画像更新"]
    Capability --> Path
```

这是一条产品目标闭环，而不是把大模型输出直接展示给用户：路径应基于知识节点与前置关系，资源生成需要证据门槛，评估结果再回流到 `user_capabilities` 与 `user_profiles`。

## 产品模块

### 学生端模块地图

| 模块 | 路由 | 面向的工作 | 代表能力 |
| --- | --- | --- | --- |
| 总览 | `/workspace` | 聚合课程、任务、生成物、运行轨迹与能力变化 | 今日课程、智能体活动、能力画像、节奏管理 |
| 实战进阶 | `/practice` | 将课程学习延伸到教程、工具、竞赛和靶场 | 教程中心、工具库、CTF/竞赛信息、实战案例 |
| 课程学习 | `/course` | A3 主工作流 | 课程入口、路径、资源工作台、辅导、效果评估 |
| 科研创新 | `/research` | 发现和比较科研机会 | 基金、动态、专利、实验室、热点与对比 |
| 选题写作 | `/writing` | 将研究想法组织为可交付物 | 选题推演、卡池、创意画布、计划书、PPT 大纲、引用 |
| 智能问答 | `/chat` | 按场景获得结构化建议 | 选题、科研、竞赛、政策、热点、写作、路径咨询 |
| 交流论坛 | `/forum` | 交流经验、组队与资源协作 | 安全话题、项目组队、问答互助、活动公告 |
| 就业招聘 | `/careers` | 用岗位需求反推能力建设 | 岗位分析、技能差距、简历、面试、企业画像、发展方向 |
| 计划任务 | `/tasks` | 把跨模块行动统一落到可执行计划 | 看板、时间线、清单、里程碑、日历和团队分工 |
| 个人中心 | `/profile` | 管理画像、资源历史和成果资产 | 画像、资源库、文档/演示/代码资产、提交清单与账户合规 |

### 教师与导师端

教师端路由按 `course_teacher`、`research_mentor`、`career_mentor` 和 `hybrid` 角色过滤可见模块，覆盖课程、教材、题库、作业、学生、科研、职业咨询和通知等工作面。当前教师端以产品体验与契约对齐为主，页面中的 mock / partial-real 状态仍需在真实后端联调中逐项收敛。

| 工作域 | 主要路由 | 意图 |
| --- | --- | --- |
| 教学运营 | `/teacher`、`/teacher/courses`、`/teacher/students` | 查看班级雷达、维护课程、观察学生进度 |
| 教材与测评 | `/teacher/materials`、`/teacher/quiz-bank`、`/teacher/assignments` | 教材入库、题库审核、作业发布与反馈 |
| 指导服务 | `/teacher/research`、`/teacher/career-mentoring` | 发布科研方向、开展职业与项目指导 |
| 组织管理 | `/teacher/notices`、`/teacher/profile` | 通知公告与教师偏好管理 |

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
    Workflow --> Audit[("agent_runs / 运行与审计记录")]
    Workflow --> Artifacts[("generated_resources / storage_objects")]
    API --> Redis["Redis：事件扇出与缓存"]
    Workflow --> Storage["本地存储 / Tencent COS"]
```

### 架构边界

| 层 | 责任 | 不能做什么 |
| --- | --- | --- |
| 产品智能体 | 政策、热点、岗位、竞赛、规划、选题、文档、任务、评价等显式业务角色 | 不新增第 10 个智能体，也不把基础设施包装为 Agent |
| Runtime / Harness | 统一输入校验、执行、状态、事件、审计和失败语义 | 不允许产品 endpoint 直接绕过运行时裸调 Skill |
| RAG 与证据 | 领域检索、证据阈值、来源投影和引用链 | 证据不足时不允许降级为无依据 LLM 输出 |
| 数据与画像 | 统一知识资产层、用户画像与能力维度 | 不为单一 domain 新建并列的 `*_chunks` / `*_documents` 表 |
| 存储与产物 | 文件对象、生成资源、校验和、访问抽象 | 未完成元数据持久化的 artifact 不应被当作成功结果广播 |

### 9 个固定产品智能体

| 分组 | 智能体 |
| --- | --- |
| 信息与研判 | `policy_interpreter`、`hot_analyst`、`job_analyst`、`competition_advisor` |
| 规划与产出 | `career_planner`、`topic_explorer`、`doc_archivist`、`task_orchestrator`、`outcome_evaluator` |

`rag`、数据采集、运行时调度、安全护栏、Harness 和对象存储是横切基础设施，而不是产品智能体。该边界会直接影响 A3 演示叙事、数据模型、CI 规则和后续扩展方式。

### 已接纳真实执行的目标契约

```mermaid
sequenceDiagram
    participant User as 用户
    participant FE as React 前端
    participant API as FastAPI
    participant Runtime as Runtime / Harness
    participant RAG as RAG
    participant LLM as Provider
    participant QC as QualityCheck
    participant DB as PostgreSQL / Storage

    User->>FE: 发起路径、资源或辅导请求
    FE->>API: REST 或 SSE 请求
    API->>Runtime: 创建可追溯运行记录
    Runtime->>RAG: 检索领域证据
    alt 证据不足
        RAG-->>Runtime: InsufficientEvidence
        Runtime-->>FE: error 事件，不调用 Provider
    else 证据满足阈值
        RAG-->>Runtime: EvidenceRefs
        Runtime-->>FE: evidence / progress
        Runtime->>LLM: 带证据的结构化生成
        LLM-->>Runtime: token / candidate output
        Runtime->>QC: 质量复核
        QC-->>Runtime: accept 或 defect
        Runtime->>DB: 持久化运行、证据与产物
        Runtime-->>FE: artifact / trace / done
    end
```

这张图描述的是可被接纳为真实执行的统一契约；实际产品路径仍要以真 Provider、真 RAG、真实 `agent_runs`、产物提交和前端 SSE 的联调结果为准。

### 数据治理设计参考

<p align="center">
  <img src="./docs/assets/readme/data-governance-design.png" alt="合规策略驱动的多源异构信息获取与可信输出设计" width="100%" />
</p>

<p align="center"><sub>竞赛材料中的数据治理与可信输出设计参考。运行时的实际 Agent 边界和验收口径以本 README、<code>AGENTS.md</code> 与 API 契约为准。</sub></p>

## 证据、数据与安全

### 统一数据模型

| 数据域 | 核心对象 | 用途 |
| --- | --- | --- |
| 知识资产 | `documents`、`document_assets`、`chunks`、`knowledge_nodes`、`knowledge_edges` | 将课程、政策、岗位、竞赛等多 domain 资料收敛到同一资产层 |
| 用户成长 | `user_profiles`、`user_capabilities`、学习事件与测验结果 | 管理对话画像、能力分数、学习偏好与动态回流 |
| 运行审计 | `agent_runs`、工作流事件与证据引用 | 记录请求、执行阶段、模型/证据摘要、质量结果和时延 |
| 生成产物 | `generated_resources`、`storage_objects` | 管理文档、PPT、导图、题目、实操和视频脚本等资源及其对象存储引用 |

### Evidence Contract v1.2

前后端以冻结的 `EvidenceChunkDTO` 传递可显示证据，而不是把内部 metadata 作为无约束字典传给 UI。

| 证据维度 | 必要字段 | 作用 |
| --- | --- | --- |
| 身份与正文 | `chunk_id`、`document_id`、`chunk_text`、`score` | 稳定定位检索片段，并区分“当前查询相关度” |
| 来源与权利 | `platform`、`source_url`、`rights_note`、`license` | 显示外部来源、版权边界与可点击原链 |
| 审计上下文 | `author`、`published_at`、`fetched_at`、`collection_mode`、`reliability` | 支持时效性、采集方式和可信度判断 |
| 资产定位 | `asset_type`、`page_no`、`chapter`、`timestamp` | 将网页、PDF、章节和视频转写片段定位到正确的上下文 |

`score` 表示结果与当前查询的相关度，`reliability` 表示来源本身的可信度，两者独立。完整字段语义见 [Evidence Contract](./docs/api/evidence-contract.md)。

### 安全与合规原则

| 场景 | 系统原则 |
| --- | --- |
| 证据不足 | 返回 `InsufficientEvidence`，不以裸 LLM 输出伪装成有依据的答案 |
| 模型与凭据 | API Key、完整 prompt、模型 reasoning 和不必要的用户原文不进入运行事件或 Git |
| 外部资料 | 保留 `platform`、`source_url`、作者、时间、许可/权利说明；不绕过登录、验证码或反自动化机制 |
| 教材与敏感资产 | 原始 PDF、整本 Markdown、数据库文件和私密数据不随仓库分发 |
| 对象存储 | 大文件通过 `storage_objects.object_key` 进行抽象；COS 以私有读写和最小权限为前提 |

## 技术栈

| 层 | 选择 | 说明 |
| --- | --- | --- |
| 前端 | React 18、TypeScript、Vite 6、React Router v7 | 路由、懒加载、学生端/教师端工作台与展示模式 |
| UI | Tailwind CSS v4、shadcn/ui、Radix、Lucide、Recharts | 一致的组件基础、可访问交互、图表与证据呈现 |
| 后端 | Python 3.11+、FastAPI、Pydantic v2、SQLAlchemy async、Alembic、`uv` | 版本化 API、配置、持久化与迁移 |
| 运行时 | LangGraph、Provider 抽象、Harness、7 类 SSE | 工作流表达、执行过程、实时事件与质量复核 |
| 数据 | PostgreSQL 16、pgvector、Redis 7 | 关系数据、向量检索与事件扇出/缓存 |
| LLM / Embedding | 讯飞星火、DeepSeek、Qwen `text-embedding-v4` | A3 演示要求、开发 fallback 策略与 1024D dense 向量 |
| 存储 | Local provider、Tencent COS | 运行时产物和私有同步链路的统一对象存储抽象 |
| 质量门禁 | pytest、TypeScript、GitHub Actions、Compose config、契约测试 | 代码、API、铁律和容器配置的基础回归 |

## 接口与事件

### API 快查

所有服务位于 `/api/v1` 下。产品接口的字段与状态以 [课程主路径 API 契约](./docs/api/course-contract.md) 为准。

| 能力 | 代表接口 | 当前定位 |
| --- | --- | --- |
| 运行与身份 | `GET /health`、`GET /system/ping`、`POST /login`、`POST /register` | 服务健康、系统探针和基础身份入口 |
| 课程学习 | `GET /courses`、`POST /courses/{course_id}/plan` | 课程目录与基于知识节点的路径规划 |
| 生成资源 | `POST /courses/{course_id}/resources/generate` | SSE 资源生成；需先发 evidence 再发 token |
| 画像与辅导 | `POST /profile/chat`、`GET/PUT /profile/me`、`POST /tutor/ask` | 画像构建、能力读取与课程上下文答疑 |
| 评估与检索 | `POST /assessment/run`、`POST /rag/search` | 测验回流与带来源元数据的领域检索 |
| 可观测性 | `GET /agent-runs`、`GET /llm/health` | 运行记录和 Provider 健康状态 |

> [!NOTE]
> API 可达、前端可回放与真实工作流验收不是同一个状态。主路径当前按 `partial-real` / 真实联调收敛方式维护，调用前请以接口契约、状态标识和运行记录为准。

### SSE 事件词汇表

| 事件 | 语义 | 前端行为 |
| --- | --- | --- |
| `progress` | 运行阶段或百分比变化 | 更新加载状态和阶段说明 |
| `evidence` | 检索通过阈值后的 `EvidenceChunkDTO[]` | 渲染 EvidenceDrawer / CitationPanel |
| `token` | Provider 的增量内容 | 逐步渲染文本或结构化资源 |
| `artifact` | 已提交的生成资源或对象存储引用 | 刷新资源卡片，不能把未持久化产物当作完成 |
| `trace` | Agent / Skill / run 的状态变化 | 更新智能体活动与执行轨迹 |
| `done` | 正常终态 | 收敛加载状态，展示最终引用 |
| `error` | 可恢复或不可恢复失败 | 显示可行动的错误信息；证据不足时不继续调用模型 |

## 快速开始

### 前置条件

| 运行方式 | 需要的软件 |
| --- | --- |
| 推荐：完整本地栈 | Docker Desktop / Docker Compose v2 |
| 前端单独开发 | Node.js 22、Corepack、pnpm 9 |
| 后端单独开发 | Python 3.11+、`uv`、PostgreSQL 16、Redis 7 |

### 启动完整本地栈

```bash
git clone https://github.com/BUPT-ResearchAgent/SecureHub-Full-Stack-Monorepo.git
cd SecureHub-Full-Stack-Monorepo
docker compose up --build
```

首次启动会下载镜像和依赖。服务就绪后：

| 服务 | 地址 |
| --- | --- |
| 前端 | http://127.0.0.1:5173 |
| 后端 API | http://127.0.0.1:8000 |
| OpenAPI | http://127.0.0.1:8000/docs |
| PostgreSQL（宿主机） | `127.0.0.1:15432` |
| Redis（宿主机） | `127.0.0.1:6379` |

PowerShell 健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

停止并移除本地容器：

```bash
docker compose down
```

### PowerShell 手动开发

先启动基础服务：

```powershell
docker compose up -d postgres redis
```

在一个终端启动后端。Compose 将 PostgreSQL 映射到宿主机 `15432`，所以手动运行时必须覆盖默认地址：

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

### 受控 WEBSEC-101 课程场景数据

`websec-101-showcase-v5` 是仅供本地开发、比赛演示和明确授权测试数据库使用的显式 seed profile。它写入真实的课程、教学班、选课、作答、学习路径、可恢复辅导记录、资源、作业、AgentRun/Evidence 和治理关系，现有 API、权限和审计会照常消费这些实体。

该 profile 包含 32 个虚构课程花名学生，以及复用本地登录账号的 1 名 demo 课程学习者。固定课程资料属于 `curated-demo`，外部链接保持 `external-preview` 来源边界；它们不是实时模型输出、平台自有视频或真实在校学生数据。seed 不会在应用启动时执行，并且当 `APP_ENV` 为 `production`、`prod` 或 `release` 时会拒绝运行。

运行前必须确认：当前目录是 `backend/`、依赖已用 `uv` 同步、`DATABASE_URL` 指向明确授权的本地/比赛/测试 PostgreSQL、目标库已通过 `uv run alembic upgrade head` 到当前 head。不要将生产连接串或凭据写入文档、脚本或 Git。

Windows PowerShell：

```powershell
cd backend
uv sync --frozen
uv run alembic upgrade head
$env:SECUREHUB_ALLOW_SHOWCASE_SEED = '1'
uv run python -m app.db.seeds.seed_showcase_course seed
uv run python -m app.db.seeds.seed_showcase_course verify
```

macOS/Linux shell：

```bash
cd backend
uv sync --frozen
uv run alembic upgrade head
SECUREHUB_ALLOW_SHOWCASE_SEED=1 uv run python -m app.db.seeds.seed_showcase_course seed
SECUREHUB_ALLOW_SHOWCASE_SEED=1 uv run python -m app.db.seeds.seed_showcase_course verify
```

`verify` 应输出 `valid: True`，并报告 manifest、质量门、对象数和关系链检查结果。需要清理时，仅能在同一类受控环境中显式执行 profile-scoped reset；它只删除该 profile 所有的稳定 ID，不会替代备份、迁移验证或浏览器验收：

```powershell
cd backend
$env:SECUREHUB_ALLOW_SHOWCASE_SEED = '1'
uv run python -m app.db.seeds.seed_showcase_course reset
```

```bash
cd backend
SECUREHUB_ALLOW_SHOWCASE_SEED=1 uv run python -m app.db.seeds.seed_showcase_course reset
```

当前仅在 Windows 项目环境中完成了命令实测；macOS/Linux 使用相同的 `uv run python -m ...` 入口和项目相对资源路径，仍须在目标环境执行 `seed` 与 `verify` 后才能记录为该平台已验收。后端目录中的更详细约束见 [backend/README.md](./backend/README.md#controlled-websec-101-showcase-course-seed)。

### 体验建议路径

1. 打开 `http://127.0.0.1:5173`，完成注册或登录。
2. 进入 `/course`，依次查看课程入口、学习路径、资源工作台、辅导和评估视图。
3. 打开 `/workspace#agent-runs` 与全局证据链面板，观察运行与来源的可视化。
4. 从 `/writing`、`/research`、`/careers` 或 `/tasks` 继续验证学习成果如何进入选题、机会、发展与执行计划。
5. 演示真实链路前，再执行 [演示 smoke](#开发验证) 并核对 Provider、RAG、数据库和 SSE 是否处于同一运行窗口。

### 配置真实 Provider

后端通过环境变量读取配置。请在被忽略的 `backend/.env.local` 或部署环境中设置凭据，绝不提交密钥；活跃配置面以 [`backend/app/core/config.py`](./backend/app/core/config.py) 为准。

<details>
<summary><strong>最小配置示例（不要提交到 Git）</strong></summary>

```dotenv
# 选择运行时 Provider；真实凭据由本地安全存储或部署平台注入。
LLM_PROVIDER=xfyun
XFYUN_APP_ID=<your-app-id>
XFYUN_API_KEY=<your-api-key>
XFYUN_API_SECRET=<your-api-secret>

# Qwen text-embedding-v4 的 OpenAI-compatible 配置。
DASHSCOPE_API_KEY=<your-dashscope-key>
DASHSCOPE_OPENAI_COMPATIBLE_BASE_URL=<your-compatible-endpoint>

# 真实模式必须被显式打开；不要在没有受控预算时开启。
AGENT_RUN_REAL_ENABLED=false
MIN_EVIDENCE=3
```

</details>

| 配置类别 | 关键变量 | 用途 |
| --- | --- | --- |
| 大模型 | `LLM_PROVIDER`、`XFYUN_*`、`DEEPSEEK_API_KEY` | 讯飞星火满足 A3 演示要求；DeepSeek 通过透明的 real-to-real fallback 策略参与开发 |
| 向量化 | `DASHSCOPE_API_KEY`、`DASHSCOPE_OPENAI_COMPATIBLE_BASE_URL` | Qwen `text-embedding-v4` 的真实检索配置 |
| 存储 | `STORAGE_PROVIDER`、`COS_*` | 本地存储或私有 Tencent COS |
| 运行时 | `MIN_EVIDENCE`、`AGENT_RUN_REAL_ENABLED` | 证据门槛与真实执行开关 |

> [!CAUTION]
> Live LLM 测试默认不进入 CI。没有经过批准的凭据与预算时，应使用 fixture / 演示路径，并清楚标识其状态；不得伪造“真实调用已通过”的结论。

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

演示回归：

```powershell
.\scripts\demo_smoke.ps1
```

`demo_smoke.ps1` 会调用本地服务、写入临时运行数据，并依赖已准备好的数据库与课程 seed；它适合演示前的 smoke，不是无状态的纯前端检查。

### CI 门禁

| 工作流 | 覆盖范围 |
| --- | --- |
| Frontend | `pnpm install --frozen-lockfile`、`pnpm typecheck`、`pnpm build` |
| Backend | `uv sync --frozen`、应用导入、Alembic 迁移、`pytest -m "not llm_live"` |
| Ironclad rules | 新 endpoint/service/repository 的状态标记、Skill 审计、RAG 先于 LLM、禁止 domain 专用知识表 |
| Docker | `docker compose config` |

## 当前状态与路线图

### 已验证基线

- 固定 9 Agent / 28 Skill catalog、唯一 RuntimeEngine/StateMachine、PostgreSQL
  durable run/outbox/SSE 以及五条产品路径已收敛。
- Wave 4-6 已实现 typed Artifact/Evidence state、资源 fan-out、QualityCheck
  taxonomy/rework、Spark-primary real fallback policy、HITL/budget/policy/metrics
  与 legacy authority removal。
- 两轮完整后端回归、可逆迁移、fixture E2E、客户端 reducer 和浏览器检查的
  证据见 `Workout/Agent-Runtime-Wave-4-6.md`。真实外部 gate 与本地 fixture
  证据严格分开。

### 正在收敛的边界

| 范围 | 当前目标 | 不能被误读为 |
| --- | --- | --- |
| 五条产品主路径 | `courses/plan`、`courses/resources/generate`、`profile/chat`、`tutor/ask`、`assessment/run` 统一走真实端到端链路 | 固定 Agent Run 专项完成就代表所有产品 endpoint 已完成 |
| 运行时统一 | 统一 Harness、RuntimeEngine、StateMachine、事件与持久化控制面 | 多条兼容路径或内存 replay 是生产级恢复语义 |
| 前端真实接入 | typed SSE、real-first 请求、错误状态与真实运行控制对齐 | mock replay 可代替真实 evidence / trace |
| Artifact 与存储 | 产物在元数据和对象存储提交后再广播，并可审计恢复 | 少量 COS 样本代表全部 GitHub 外数据已同步 |

### 工程推进顺序

| 阶段 | 工作重点 | 说明 |
| --- | --- | --- |
| AR-00 | 契约冻结与回归门禁 | 先统一 Agent-Skill catalog、API/SSE 契约和架构测试，避免迁移中出现第二套真相 |
| Wave 1 | 单一执行内核 | 统一 Harness、fixture/real 语义、Provider policy、RuntimeEngine 与状态机 |
| Wave 2 | Durable Control Plane | 持久化 run/step/event/checkpoint/evidence/provider-call，补 Worker、lease、recovery 与 Redis fan-out |
| Wave 3-4 | 产品路径与质量协作 | 将五条产品 workflow、前端 WorkflowRunClient、artifact、ContextBuilder、QualityCheck 有界返工串为一体 |
| Wave 5-6 | 治理与最终签收 | 权限/预算、可观测性、安全、控制操作、兼容路径清理、真实 E2E 与故障注入验收 |

完整工作包、依赖关系与验收条件见 [多智能体架构 TODO](./TODO.md)。

## 常见问题

| 现象 | 优先检查 |
| --- | --- |
| `pnpm` 不可用 | 运行 `corepack enable`，并确认 Node.js 22；仓库 CI 以 pnpm 锁文件为准 |
| 后端连不上 PostgreSQL | Compose 的宿主机端口是 `15432`，手动后端进程需要使用 `postgresql+asyncpg://securehub:securehub@127.0.0.1:15432/securehub` |
| `docker compose up` 端口冲突 | 检查 `5173`、`8000`、`15432`、`6379`；可通过 `FRONTEND_PORT` 和 `BACKEND_PORT` 覆盖前后端端口 |
| SSE 只显示演示内容 | 检查当前页面是否启用 mock / fallback、后端是否可达、RAG 是否有足够证据、真实模式是否被显式授权 |
| 真实 Provider 失败 | 检查凭据、模型策略、预算和网络；失败应保留为真实失败，不应静默切到 fixture |
| 生成资源没有可用文件 | 检查 `generated_resources` / `storage_objects` 是否提交成功；未持久化 artifact 不应被当作完成结果 |
| `pytest` 无法启动 | 先启动 PostgreSQL 和 Redis，再执行 Alembic 迁移；live LLM 用例默认被 `not llm_live` 排除 |

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
├─ CLAUDE.md              # 项目上下文与架构规则
└─ TODO.md                # 多智能体完整架构工作包与验收计划
```

## 文档索引

| 文档 | 适合谁 | 说明 |
| --- | --- | --- |
| [工程约束与阶段口径](./AGENTS.md) | 所有贡献者 | 固定 9 Agent、证据门槛、数据边界和当前联调状态 |
| [项目上下文](./CLAUDE.md) | 新成员与 AI 辅助开发工具 | 技术栈、架构铁律、历史决策与阅读路径 |
| [多智能体架构 TODO](./TODO.md) | 架构与运行时负责人 | 统一 Runtime 的工作包、依赖、验收和收尾顺序 |
| [Wave 4-6 交付记录](./Workout/Agent-Runtime-Wave-4-6.md) | 验收与维护负责人 | 实际范围、测试、根运行、外部阻塞与提交列表 |
| [Runtime 运维与恢复](./docs/operations/agent-runtime-wave-4-6.md) | 部署与值班负责人 | 部署前置、迁移、恢复、指标和真实 gate 口径 |
| [课程主路径 API 契约](./docs/api/course-contract.md) | 前后端协作者 | 课程、画像、RAG、资源生成、辅导与评估接口 |
| [证据契约](./docs/api/evidence-contract.md) | RAG、前端与合规协作者 | Evidence DTO、来源字段、版权边界与对齐要求 |
| [演示 Checklist](./docs/demo/seven-minute-demo-checklist.md) | 演示与验收负责人 | 7 分钟演示分镜、素材、smoke 与门禁 |
| [CI 工作流](./.github/workflows/ci.yml) | 开发者 | 前端、后端、铁律和 Compose 的自动化校验 |

## 开发协作与治理

- 默认在 `dev` 分支协作；提交前仅暂存本次任务相关文件，避免把本地运行产物或其他人的改动带入 PR。
- 新增 endpoint、service 或 repository 时需要明确 `# Status: real | mock | partial-real | planned`。
- 新增生成式 Skill 前先确认其 RAG、证据门槛、质量复核、`agent_runs` 审计与 artifact 持久化路径。
- 改动铁律、schema、Harness 契约或架构差异说明时，同步更新 `CLAUDE.md`、`.codex/AGENTS.md` 和相关 API 文档。
- 不提交 `.env`、密钥、数据库、原始受版权保护资料、原始爬取数据或用户数据。

## 许可证

仓库当前未提供顶层 `LICENSE` 文件。在项目维护者明确授权前，请勿将其作为可再分发依赖或独立开源组件使用。
