# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 0. 文档自述

- **文档目的**：作为"安枢智梯 SecureHub / CyberLadder"项目所有后续 Claude Code / Codex / Cursor 会话的默认上下文。任何在本仓库工作的 AI 助手（或新加入的工程师）应当**首先读完本文件**，再开始触碰代码。
- **读者**：本项目团队成员；后续接入的 AI 编码助手；A3 赛题答辩评委（架构理解参考）。
- **最后更新时间**：2026-06-05（由 Claude Opus 4.7 基于 4 份外部文档 + 仓库代码生成）。
- **本文件的权威性**：在仓库层面，本文件 > `README.md` / `docs/architecture.md` / `docs/backend-overview.md`。当本文件与代码现状冲突时，**以代码为准并立即更新本文件**；当本文件与外部 4 份文档冲突时，**以本文件 §19 的"差异说明"为准**。

### 阅读约定（什么时候回读外部文档？）

| 场景 | 回读哪份文档 | 路径 |
| --- | --- | --- |
| 不确定"做什么、优先级、新增到哪里" | **A3 赛题规划**（最权威开发指导） | `D:/Nnutural/Desktop/BUPT大全/BUPT竞赛/26软件杯/CompetitionTheme/A3赛题规划.md` |
| 不确定 A3 硬性需求边界 | **A3 赛题原文** | `D:/Nnutural/Desktop/BUPT大全/BUPT竞赛/26软件杯/CompetitionTheme/A3赛题.md` |
| 不确定项目整体愿景 / 商业逻辑 / 市场叙事 | **项目计划书**（挑战杯） | `D:/Nnutural/Desktop/BUPT大全/BUPT竞赛/26软件杯/Legacy/鸿雁杯/MinerU_markdown_项目计划书_2054945124833226752.md` |
| 不确定某智能体内部算法 / 公式 / 输入输出契约 | **设计开发文档**（CyberLadder v1.8，1.5 节最重要） | `D:/Nnutural/Desktop/BUPT大全/BUPT竞赛/26软件杯/Legacy/2026037134-03 设计与开发文档/3 软件应用与开发类作品设计和开发文档模板（2026版）.md` |

⚠️ **设计开发文档**与**A3 赛题规划**存在多处冲突（13 智能体 vs 9 智能体、多 DB vs PostgreSQL+pgvector），**冲突一律以"规划文档"为准**，并参考本文件 §19。

---

## 1. 项目一句话定位

**安枢智梯（SecureHub / CyberLadder）** 是面向网络安全人才培养的**智能化产教研融合中枢系统**，覆盖学生从"入门学习—竞赛备赛—科研创新—就业对接"的全周期，其中"基于多智能体的个性化课程学习"是 A3 赛题对应的主干模块，"中枢"则统一承载政策解读、热点研判、招聘分析、竞赛指导、选题写作、成果归档等延展能力。

**两个不能丢的点**：
- 项目是"网络安全人才培养中枢"——这是挑战杯叙事的根本。
- 课程学习是中枢之上为 A3 赛题新增的"第 10 个一级模块"——这是软件杯演示的主战场。

---

## 2. 双重身份与赛事背景

| 维度 | 挑战杯（创业计划竞赛） | 第十五届中国软件杯 A3 |
| --- | --- | --- |
| 题目类别 | A. 科技创新和未来产业 | A 组（本科 / 研究生 / 高职） |
| 出题方 | — | **科大讯飞股份有限公司** |
| 核心叙事 | "面向网络安全人才培养的智能化产教研融合中枢" | "基于大模型的个性化资源生成与学习多智能体系统" |
| 演示比例 | 中枢叙事 + 课程学习串场 | 课程学习走 100%，中枢延展走 30% |

### 2.1 A3 赛题硬性要求（must-have）

- ☐ **对话式画像构建**：自然语言对话提取特征，**不少于 6 个维度**（如知识基础、认知风格、易错点偏好等）
- ☐ **画像随学随新**：学习行为反馈触发画像更新
- ☐ **显式多智能体架构**：体现"多智能体"协作（**至少 5 种类型资源生成需由不同角色智能体协作完成**）
- ☐ **5+ 资源类型生成**：专业课程讲解文档、知识点思维导图、不同类型练习题目、拓展阅读材料、多模态教学视频/动画、代码类实操案例（任选 ≥ 5 种）
- ☐ **个性化学习路径规划**：依托多智能体协同 + 知识图谱 + 学习进度
- ☐ **个性化资源精准推送**：基于画像 + 进度 + 偏好
- ☐ **流式输出 / 生成进度追踪**：避免长时间白屏
- ☐ **防幻觉 + 内容安全过滤机制**：无事实性错误、无敏感违规
- ☐ **自构造一门完整高校专业课程的初始知识库**（如 AI / 计算机 / 电子信息类）
- ☐ **使用科大讯飞 AI 工具**（讯飞星火 + 讯飞 TTS 等，并在文档显著位置标注）
- ☐ **开源项目 / 协议显著标注**
- ☐ **PPT + 可运行项目 + ≤ 7 分钟演示视频 + 配套文档**
- ☐ **如使用 AI Coding 工具，给出相关说明**（Claude Code、Cursor 等）

### 2.2 A3 可选加分项（should-have）

- ☐ **智能辅导**：即时多模态答疑（文字 + 图解 + 短视频）
- ☐ **学习效果评估**：多维度评估 + 动态调整推送策略

### 2.3 A3 评分占比

| 评分项 | 占比 |
| --- | --- |
| 创新价值与实用性 | 35% |
| 功能实现及技术要求 | **45%** |
| 配套文档丰富度 | 10% |
| 演示视频、PPT 效果 | 10% |

---

## 3. 架构核心铁律（醒目位置 — 不可违反）

> 任何修改本仓库代码的会话，**开工前必须确认下列约束未被违反**。违反任何一条 = 重做。

### 3.1 ❌ 不要新增智能体角色（永远保持 **9 个**）

A3 新能力一律作为**现有 9 智能体的新 skill** 叠加，**绝不**注册第 10 个智能体角色。9 个固定角色：

**5 个核心智能体**：`policy_interpreter` / `hot_analyst` / `job_analyst` / `competition_advisor` / `career_planner`
**4 个业务支撑智能体**：`topic_explorer` / `doc_archivist` / `task_orchestrator` / `outcome_evaluator`

理由：A3 评委会数智能体数；规划文档锁定为 9；超出会破坏"班底固定，技能可扩"的叙事。

### 3.2 ❌ 横切基础设施不算智能体（4 个组件单独建模）

设计开发文档 1.5.3 节里的 4 个"支撑型智能体"——多源数据采集、知识检索、系统调度、安全监控——在本项目工程实现中**不计入 9 智能体清单**，而是作为框架层 / service / middleware 存在：

| 原文档"支撑智能体" | 本项目工程位置 |
| --- | --- |
| 多源数据采集与治理（1.5.3.1） | `backend/app/knowledge/loaders/`（离线脚本） |
| 知识检索与证据链管理（1.5.3.2） | `backend/app/rag/`（service） |
| 系统调度与多智能体编排（1.5.3.7） | `backend/app/runtime/router.py` + LangGraph conditional edge |
| 安全监控与合规审核（1.5.3.8） | `backend/app/runtime/guardrails/`（middleware） |

### 3.3 ❌ 不要为新 domain 单独建知识库表（统一知识资产层 v2）

所有 domain（`course_websec` / `policy` / `fund` / `job` / `competition` / `paper` / `news`）共用：

- `documents`：文档级元信息、来源、可信度、`raw_text` 可空、`status` 跟踪入库生命周期
- `document_assets`：PDF / Markdown / 封面 / 页图 / OCR / 章节文件等**源资料**资产
- `chunks`：RAG 检索切片与向量；`embedding` 可空 + `embedding_status` 跟踪向量化生命周期
- `knowledge_nodes`：课程知识点、技能、工具、政策主题、岗位技能等**概念节点**（升级自 v1 `knowledge_points`，加 `node_type` 字段）
- `knowledge_edges`：前置、相关、支撑、扩展等**关系**（升级自 v1 `kp_prerequisites`，PK 三元组 `(source_id, target_id, edge_type)`）

**禁止**新建 `course_chunks` / `fund_chunks` / `policy_chunks` 等并列表；**禁止**把生成物落进 `documents`（生成物走 `generated_resources` + `storage_objects`）。

### 3.4 ❌ 不要在 feature 模块自建画像（画像跨模块共享，画像源 v2）

`user_profiles` 是全平台画像主表，存储 merged persona、学习偏好、弱点、目标等 JSONB `dimensions` + 画像向量。
`user_capabilities` 是能力明细表，存储可评估、可绘制雷达图、可随学习事件更新的维度分数（`(user_id, dimension)` 唯一）。

任何模块需要画像数据时读取这两张表；任何能力更新必须走如下链路：

```
quiz_attempts / learning_events
  → outcome_evaluator.update_capability  → user_capabilities
  → career_planner.update_persona        → user_profiles
```

### 3.5 ❌ mock vs real 必须明确标注

所有新增 endpoint / service / repository 在文件顶部注释或函数 docstring 中明确写一句：
```
# Status: [real] / [mock] / [partial-real]
```
本文件 §4 与 §6 的状态标签**必须随代码同步更新**。

### 3.6 ❌ 不要绕开 RAG 直接调 LLM（生成必须有证据回链）

所有生成式 skill（除"创意发散"类如 `generate_research_topic` 显式声明外）**必须**先经 `rag/retriever.py` 取证据 → 拼入 prompt → 生成时绑定 `evidence_chunk_ids` 入 `agent_runs` 表。

### 3.7 ❌ 不要绕开 `agent_runs` 写日志

所有智能体调用（无论同步 / 异步 / 流式）**必须**落 `agent_runs` 表，至少记录 `agent_id` / `skill_id` / `input_summary` / `output_summary` / `evidence_chunk_ids` / `status` / `duration_ms` / `token_usage`。前端的"Agent 活动可视化面板"是演示视频的高光帧，依赖这张表。

### 3.8 ❌ 不要修改本文档而不同步更新 §19

§19（与原设计开发文档的差异说明）记录了所有"故意偏离设计文档"的决策；如本文件 §3 / §7 / §9 任何铁律 / 数据库结构 / 架构决策被修改，**必须同步更新 §19**，否则后续会话会重新引入冲突。

---

## 4. 仓库目录速查

> 工作目录：`D:/Nnutural/Desktop/BUPT大全/BUPT竞赛/26软件杯/CompAssitant-FrontDesign`
> 状态标签：**[real]** 已实现且对接真实数据；**[mock]** 已实现但用 mock 数据；**[planned]** 规划中未实现；**[legacy]** 旧版本，不再扩展。

```
CompAssitant-FrontDesign/
├─ CLAUDE.md                          [real] 本文件
├─ README.md                          [real] 项目顶层 README（中英混合，简要）
├─ .editorconfig / .gitignore         [real]
├─ .env.example                       [real] FRONTEND_PORT / BACKEND_HOST / BACKEND_PORT
├─ docker-compose.yml                 [real] frontend (node:22) + backend (python:3.12) 双服务
│
├─ frontend/                          React 18 + Vite 6 + TS + Tailwind v4 + shadcn/ui
│  ├─ package.json                    [real] 依赖见 §5.1
│  ├─ vite.config.ts                  [real] 含自定义 figmaAssetResolver 插件
│  ├─ tsconfig.json                   [real] alias @/* → ./src/*
│  ├─ default_shadcn_theme.css        [real] shadcn 基础主题
│  ├─ ATTRIBUTIONS.md                 [real] shadcn/ui MIT、Unsplash license
│  ├─ guidelines/Guidelines.md        [real] 占位（无实际内容）
│  ├─ pnpm-workspace.yaml             [real]
│  ├─ postcss.config.mjs              [real]
│  ├─ index.html                      [real]
│  ├─ dist/                           [real] 构建产物（gitignored）
│  ├─ dev.log / page-check.png        [real] 调试用
│  └─ src/
│     ├─ main.tsx                     [real] React 入口 → App
│     ├─ styles/app.css               [real]
│     ├─ lib/api.ts                   [real] apiGet/apiPost 客户端，读 VITE_API_BASE_URL
│     └─ app/
│        ├─ App.tsx                   [real] BrowserRouter 路由，10 路由
│        ├─ search-data.ts            [real] GlobalSearch 静态索引
│        ├─ components/               全局组件
│        │  ├─ Layout.tsx             [real] 侧边栏 + 顶栏 + Outlet + EvidenceDrawer，navItems 在 30–161 行
│        │  ├─ PageShell.tsx          [real] 面包屑 + tabs + actions 通用壳
│        │  ├─ EvidenceDrawer.tsx     [mock] 证据抽屉，目前是静态 mockEvidences
│        │  ├─ GlobalSearch.tsx       [real] Command-style 全局搜索
│        │  ├─ DataTag.tsx            [real] D1–D7 标签组件（产品 UX 关键）
│        │  ├─ figma/                 [real] Figma 导出残留组件
│        │  └─ ui/                    [real] shadcn/ui 47 个原子组件（accordion … tooltip）
│        ├─ pages/                    18 个页面
│        │  ├─ Landing.tsx            [real] 公共落地页，motion 动画
│        │  ├─ Workspace.tsx          [real] 总览（活跃实现，替代 Home）
│        │  ├─ Practice.tsx           [partial-real] 实战进阶，CTFtime 接真后端，其余 mock
│        │  ├─ Research.tsx           [partial-real] 科研创新，接 /api/v1/research/*（mock 数据）
│        │  ├─ Writing.tsx            [mock] 选题写作（IdeaLab + DocStudio 合并替代）
│        │  ├─ Chat.tsx               [mock] 智能问答
│        │  ├─ Forum.tsx              [mock] 交流论坛
│        │  ├─ Careers.tsx            [mock] 就业招聘
│        │  ├─ Tasks.tsx              [mock] 计划任务（活跃实现，替代 Planner）
│        │  ├─ Profile.tsx            [mock] 个人中心
│        │  ├─ Home.tsx               [legacy] /home → /workspace 重定向，文件保留
│        │  ├─ Planner.tsx            [legacy] 顶部注释明确 "do not extend this page"
│        │  ├─ Assets.tsx             [legacy] 静态原型
│        │  ├─ DataHub.tsx            [legacy] 静态原型
│        │  ├─ DocStudio.tsx          [legacy] 静态原型（合并入 Writing）
│        │  ├─ IdeaLab.tsx            [legacy] 静态原型（合并入 Writing）
│        │  ├─ Opportunities.tsx     [legacy] 静态原型
│        │  ├─ Recommender.tsx        [legacy] 静态原型
│        │  └─ index.ts               [real] 只导出 10 个活跃页面
│        └─ features/                 8 个 feature 模块（统一 5 件套结构）
│           ├─ research/              [partial-real] api / types / utils / components（无 store / mockData）
│           ├─ workspace/             [mock] api + mockData + store + types + utils + components
│           ├─ chat/                  [mock] 同上 + 含 CitationPanel.tsx
│           ├─ tasks/                 [mock] 同上 + 额外 taskBridge.ts
│           ├─ writing/               [mock] 同上
│           ├─ forum/                 [mock] 同上
│           ├─ careers/               [mock] 同上
│           └─ profile/               [mock] 同上 + 含 CapabilityRadarCard.tsx
│
├─ backend/                           FastAPI + uv + pytest（Python 3.11+）
│  ├─ pyproject.toml                  [real] 依赖：fastapi, httpx, lxml, playwright, pydantic-settings, pytest, uvicorn
│  ├─ uv.lock                         [real]
│  ├─ README.md                       [real] 后端 README
│  ├─ start.sh                        [real] 启动脚本，清空所有 proxy 环境变量
│  ├─ run.py                          [real] 同上 Python 版
│  ├─ app/
│  │  ├─ main.py                      [real] FastAPI app factory + CORS
│  │  ├─ deps.py                      [real] SettingsDep 别名
│  │  ├─ api/
│  │  │  ├─ router.py                 [real] 聚合 v1 router
│  │  │  └─ v1/
│  │  │     ├─ api.py                 [real] 6 个子 router 挂载
│  │  │     └─ endpoints/             6 个 endpoint 模块
│  │  │        ├─ health.py           [real]
│  │  │        ├─ system.py           [real] ping
│  │  │        ├─ placeholder.py      [mock] 占位
│  │  │        ├─ research.py         [mock] 转发 research_service
│  │  │        ├─ ctftime.py          [real] 代理 https://ctftime.org/api/v1
│  │  │        └─ policy.py           [mock] 10 条政策硬编码
│  │  ├─ core/
│  │  │  ├─ config.py                 [real] Settings + lru_cache get_settings
│  │  │  └─ logging.py                [real] 基础日志
│  │  ├─ schemas/                     Pydantic 模型
│  │  │  ├─ common.py                 [real] MessageResponse / PlaceholderResponse
│  │  │  ├─ health.py                 [real] HealthResponse
│  │  │  └─ research.py               [mock] research domain 全部 schema
│  │  ├─ services/
│  │  │  ├─ README.md                 [real]
│  │  │  └─ research_service.py       [mock] CRUD-style，对接 in-memory repo
│  │  ├─ repositories/
│  │  │  ├─ README.md                 [real]
│  │  │  └─ research_repository.py    [mock] 442 行 in-memory 数据
│  │  ├─ models/
│  │  │  └─ README.md                 [real] 空目录占位
│  │  ├─ agents/                      [planned] §7 待新增
│  │  ├─ runtime/                     [planned] LangGraph 编排，§7 待新增
│  │  ├─ llm/                         [planned] 讯飞星火等客户端，§7 待新增
│  │  ├─ rag/                         [planned] 检索 + 证据，§7 待新增
│  │  ├─ knowledge/                   [planned] 加载脚本 + 图谱，§7 待新增
│  │  ├─ db/                          [planned] SQLAlchemy + Alembic，§9 待新增
│  │  ├─ auth/                        [planned] 简单 JWT
│  │  └─ streaming/                   [planned] SSE 响应封装
│  └─ tests/
│     ├─ __init__.py                  [real]
│     ├─ test_health.py               [real]
│     └─ test_research.py             [real] mock 数据回归
│
├─ docs/
│  ├─ architecture.md                 [real] 旧版顶层架构说明（已被本文件覆盖）
│  ├─ backend-overview.md             [real] 后端模块说明
│  └─ superpowers/
│     └─ plans/
│        └─ 2026-04-24-global-search.md  [real] 已完成的小型功能计划
│
└─ scripts/
   ├─ dev.sh                          [real] Bash 启动提示
   └─ dev.ps1                         [real] PowerShell 启动提示
```

> ⚠️ 7 个 `[legacy]` 页面（Home / Planner / Assets / DataHub / DocStudio / IdeaLab / Opportunities / Recommender）**不要继续在它们里面写新功能**——它们是早期 Figma 导出的静态原型。新功能应进入对应的"活跃页面"或 feature 模块。

---

## 5. 前端架构详解

### 5.1 技术栈完整列表（抽自 `frontend/package.json`）

| 类别 | 库 | 版本 | 备注 |
| --- | --- | --- | --- |
| 框架 | react / react-dom | 18.3.1 | peerDependency |
| 路由 | react-router-dom | ^7.12.0 | v7 BrowserRouter |
| 构建 | vite | 6.3.5 | pnpm overrides 锁版本 |
| 构建插件 | @vitejs/plugin-react | 4.7.0 | |
| 样式 | tailwindcss + @tailwindcss/vite | 4.1.12 | Tailwind v4 |
| 样式工具 | tailwind-merge / clsx / class-variance-authority | 3.2.0 / 2.1.1 / 0.7.1 | shadcn 配套 |
| 动画 | motion / tw-animate-css | 12.23.24 / 1.3.8 | |
| UI 基元 | @radix-ui/react-* | 各版本 | 30 个 Radix 包，shadcn/ui 底层 |
| UI 库 | @mui/material + @mui/icons-material | 7.3.5 | 与 shadcn 共存，**新代码优先 shadcn** |
| 图标 | lucide-react | 0.487.0 | |
| 表单 | react-hook-form | 7.55.0 | |
| Markdown | react-markdown + remark-gfm | 10.1.0 / 4.0.1 | A3 流式渲染 |
| 拖拽 | react-dnd + react-dnd-html5-backend | 16.0.1 | |
| 命令面板 | cmdk | 1.1.1 | GlobalSearch |
| 图表 | recharts | 2.15.2 | CapabilityRadarCard |
| 通知 | sonner | 2.0.3 | App.tsx 顶层 Toaster |
| 主题 | next-themes | 0.4.6 | |
| 日期 | date-fns + react-day-picker | 3.6.0 / 8.10.1 | |
| 其他 | embla-carousel-react / input-otp / react-popper / react-resizable-panels / react-responsive-masonry / react-slick / vaul | — | 边缘 UI 场景 |

**没有装且需要在 A3 阶段加装的**：
- `markmap-lib` + `markmap-view`（思维导图）→ P0
- `reveal.js`（PPT 预览）→ P0
- `mermaid`（视频分镜流程图）→ P0
- TTS / 音频播放原生 HTML5（无需新依赖）

### 5.2 路由表（基于 `frontend/src/app/App.tsx`）

| Path | 元素 | Layout 嵌套 | 对应 feature 模块 |
| --- | --- | --- | --- |
| `/` | `<Landing />` | 否 | — |
| `/workspace` | `<Workspace />` | 是 | `features/workspace/` |
| `/practice` | `<Practice />` | 是 | — (直接接 CTFtime) |
| `/research` | `<Research />` | 是 | `features/research/` |
| `/writing` | `<Writing />` | 是 | `features/writing/` |
| `/chat` | `<Chat />` | 是 | `features/chat/` |
| `/forum` | `<Forum />` | 是 | `features/forum/` |
| `/careers` | `<Careers />` | 是 | `features/careers/` |
| `/tasks` | `<Tasks />` | 是 | `features/tasks/` |
| `/profile` | `<Profile />` | 是 | `features/profile/` |
| `/home` | `<Navigate to="/workspace" />` | 是 | — |
| `*` | `<Navigate to="/" />` | — | — |

A3 适配新增（**P0**）：
| `/course` | `<CourseStudy />` | 是 | `features/course/` (新建) |

### 5.3 Layout 与 navItems 完整定义

`frontend/src/app/components/Layout.tsx` 第 30–161 行的 `navItems: NavItem[]` 是**侧边栏一级 + 二级目录的唯一真相**。9 个一级条目，每个带 6–9 个 children（仅作为子页签 key，不是单独路由）：

| Path | 一级标签 | 二级 children keys |
| --- | --- | --- |
| `/workspace` | 总览 | today / ddl / actions / recent / freshness / industry / social / policy |
| `/practice` | 实战进阶 | tutorial / tools / contest / hvv / range / cases / ddl |
| `/research` | 科研创新 | fund / news / innovation / hot / patent / lab / compare |
| `/writing` | 选题写作 | deduce / cards / canvas / module / proposal / editor / ppt / cite |
| `/chat` | 智能问答 | topic / research / contest / policy / hot / writing / path |
| `/forum` | 交流论坛 | security / topic / team / exp / qa / notice / exchange |
| `/careers` | 就业招聘 | jobs / analysis / gap / path / resume / interview / company / direction |
| `/tasks` | 计划任务 | board / timeline / list / milestone / calendar / team |
| `/profile` | 个人中心 | persona / vault / docs / slides / code / proof / submit / notice / account |

二级 key 通过 `?tab=xxx` URL 参数切换，由 `PageShell` 组件读取并渲染对应 `TabDef.render()`。

### 5.4 feature 模块的统一组织模式

```
features/<feature>/
  api.ts          # 该 feature 的 API 调用函数（fetch / 调 mock）
  mockData.ts     # mock 数据（research 模块没有此文件，因为接真后端）
  store.ts        # useReducer-based 工作区状态机 + localStorage 自动持久化
  types.ts        # 该 feature 的 TypeScript 类型定义
  utils.ts        # 该 feature 的工具函数
  components/     # 该 feature 专属的页面组件
```

**特例**：
- `features/research/` **无** `mockData.ts` 与 `store.ts`——因为它已接真后端（`/api/v1/research/*`，虽然后端目前还是 mock）
- `features/tasks/` **有额外的** `taskBridge.ts`——支持其他 feature 向 Tasks 推送任务

### 5.5 全局状态管理方式

**没有 Redux / Zustand / Jotai**。状态管理方式：

1. **每个 feature 自带一个 reducer + localStorage 持久化**（基于 `useReducer`，见 `features/workspace/store.ts` 的 `WorkspaceAction` 定义）
2. **跨 feature 通信通过 `taskBridge.ts`**（写入 localStorage 中转 key，目标 feature 启动时读取）
3. **路由参数通过 `useSearchParams`** 传递 tab 切换
4. **Toast 通过 sonner** 顶层 `<Toaster />`

**新加 feature 时，应当继续沿用此模式**——不要引入 Redux/Zustand 单独建一套。

### 5.6 已有的可复用组件清单（按用途分组）

| 组件 | 路径 | 用途 |
| --- | --- | --- |
| `Layout` | `frontend/src/app/components/Layout.tsx` | App Shell（240px 侧边栏 + 64px 顶栏 + Outlet + 360px EvidenceDrawer） |
| `PageShell` | `frontend/src/app/components/PageShell.tsx` | 面包屑 + 标题 + actions + tabs，所有"活跃页面"都用它 |
| `GlobalSearch` | `frontend/src/app/components/GlobalSearch.tsx` | cmdk 命令面板，索引数据在 `app/search-data.ts` |
| `EvidenceDrawer` | `frontend/src/app/components/EvidenceDrawer.tsx` | **mock**，全局证据抽屉，需改造为接真 `agent_runs.evidence_chunk_ids` |
| `DataTag` | `frontend/src/app/components/DataTag.tsx` | D1–D7 数据类型标签（产品 UX 关键，**不可乱改语义**） |
| `CitationPanel` | `frontend/src/app/features/chat/components/CitationPanel.tsx` | Chat 回答的引用列表，A3 防幻觉演示 |
| `CitationEvidencePanel` | `frontend/src/app/features/writing/components/CitationEvidencePanel.tsx` | 写作模块引用面板 |
| `EvidenceList` | `frontend/src/app/features/research/components/EvidenceList.tsx` | 科研详情抽屉的证据列表 |
| `CapabilityRadarCard` | `frontend/src/app/features/profile/components/CapabilityRadarCard.tsx` | recharts 雷达图，A3 学习效果评估出口 |
| `AgentSidebar` | `frontend/src/app/features/chat/components/AgentSidebar.tsx` | Chat 智能体选择侧栏 |
| `StructuredAnswerCards` | `frontend/src/app/features/chat/components/StructuredAnswerCards.tsx` | Chat 结构化回答卡片（建议 / 证据 / TODO / 对比 / 时间线 / 风险） |
| `BoardView` / `TimelineView` / `CalendarView` / `ListView` / `MilestoneView` / `TeamCollabView` | `features/tasks/components/` | 任务的 6 种视图，将被 `/course` 学习路径复用 |

### 5.7 A3 适配新增：`/course` CourseStudy 页结构

| 子 tab | render 内容 | 复用现有组件 |
| --- | --- | --- |
| `entry` 课程入口 | 课程卡 + 画像入口 + 进度概览 | `PageShell` + `CapabilityRadarCard` |
| `path` 学习路径 | 按知识点的 DAG 视图 + 推荐顺序 | `features/tasks/components/BoardView` / `TimelineView` |
| `workbench` 资源工作台 | 左侧路径节点选中，右侧 6 类资源 tab（doc / ppt / mindmap / quiz / lab / video） | 新增 `features/course/components/ResourceTabs.tsx` |
| `tutor` 辅导对话 | 嵌入 Chat，带学习上下文 | `features/chat/*` 全部 |
| `assess` 效果评估 | 测试题作答 + 评分回流 | `features/profile/components/CapabilityRadarCard` |

**`/course` 与现有 `/practice` 的关系**：
- `/practice` 保留靶场 / 案例 / 工具库入口（实战进阶定位）
- `/practice` 的 "教程中心" 子 tab（`tutorial` key）改造成"跳转到 `/course`"的入口卡
- 二者**不合并**——Practice 是中枢叙事的"实战进阶"延续，Course 是 A3 的"个性化学习"主战场

---

## 6. 后端架构详解

### 6.1 当前已实现的 endpoints

| 路径 | 方法 | 实现文件 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| `/` | GET | `backend/app/main.py:28` | [real] | 根欢迎信息 |
| `/api/v1/health` | GET | `backend/app/api/v1/endpoints/health.py:10` | [real] | 健康检查 |
| `/api/v1/system/ping` | GET | `backend/app/api/v1/endpoints/system.py:8` | [real] | pong |
| `/api/v1/placeholder/modules` | GET | `backend/app/api/v1/endpoints/placeholder.py:8` | [mock] | 占位 |
| `/api/v1/research/funds` | GET | `backend/app/api/v1/endpoints/research.py:24` | [mock] | 基金列表（in-memory） |
| `/api/v1/research/news` | GET | `research.py:35` | [mock] | 科研动态 |
| `/api/v1/research/innovations` | GET | `research.py:45` | [mock] | 学术创新 |
| `/api/v1/research/papers` | GET | `research.py:*` | [mock] | 热点论文 |
| `/api/v1/research/patents` | GET | `research.py:*` | [mock] | 专利成果 |
| `/api/v1/research/labs` | GET | `research.py:*` | [mock] | 开放实验室 |
| `/api/v1/research/compare` | GET | `research.py:*` | [mock] | 对比池 |
| `/api/v1/research/{type}/{id}` | GET | `research.py:*` | [mock] | 详情 |
| `/api/v1/research/{type}/{id}/toggle/*` | POST | `research.py:*` | [mock] | 收藏 / 订阅 / 对比 / 已读 / 阅读列表切换 |
| `/api/v1/ctftime` | GET | `backend/app/api/v1/endpoints/ctftime.py:17` | [real] | **真实**：代理 https://ctftime.org/api/v1 |
| `/api/v1/ctftime/{event_id}` | GET | `ctftime.py:32` | [real] | CTF 赛事详情 |
| `/api/v1/policy` | GET | `backend/app/api/v1/endpoints/policy.py` | [mock] | 10 条硬编码政策 |

### 6.2 已有的 services / repositories / schemas 清单

| 文件 | 状态 | 行数 / 内容摘要 |
| --- | --- | --- |
| `backend/app/services/research_service.py` | [mock] | 44 行，`ResearchService` 类提供 `list_items / get_detail / toggle_*` 等 8 个方法，转发到 repository |
| `backend/app/repositories/research_repository.py` | [mock] | 442 行 in-memory `ResearchRepository` + 硬编码数据 |
| `backend/app/schemas/common.py` | [real] | `MessageResponse` / `PlaceholderResponse` |
| `backend/app/schemas/health.py` | [real] | `HealthResponse` |
| `backend/app/schemas/research.py` | [mock] | research domain 全部 Pydantic 模型 |
| `backend/app/deps.py` | [real] | `SettingsDep = Annotated[Settings, Depends(get_settings)]` |
| `backend/app/core/config.py` | [real] | `Settings`（pydantic-settings），关键字段：`APP_NAME` / `API_V1_PREFIX` / `FRONTEND_ORIGINS` / `DEBUG` |
| `backend/app/core/logging.py` | [real] | basic logging |

### 6.3 即将新增的后端目录结构（P0 一次性建好）

```
backend/app/
├─ agents/                            [planned] 9 智能体目录，详见 §7 / §15
│  ├─ base.py                         # Agent 基类 + 五元组规范
│  ├─ policy_interpreter/
│  ├─ hot_analyst/
│  ├─ job_analyst/
│  ├─ competition_advisor/
│  ├─ career_planner/
│  ├─ topic_explorer/
│  ├─ doc_archivist/
│  ├─ task_orchestrator/
│  └─ outcome_evaluator/
│
├─ runtime/                           [planned] 智能体运行时
│  ├─ graphs/
│  │  ├─ course_learning.py           # A3 主战场：课程学习多智能体工作流
│  │  ├─ fund_recommendation.py       # P2：基金推荐（中枢延展）
│  │  └─ tutor_routing.py             # P1：智能辅导路由
│  ├─ capability_manifest.py          # 9 智能体能力清单注册
│  ├─ router.py                       # 路由评分函数 Score(a_i, t)
│  └─ guardrails/
│     ├─ input_filter.py
│     ├─ output_filter.py
│     └─ prompt_injection_check.py
│
├─ llm/                               [planned] 模型客户端
│  ├─ xfyun.py                        # 讯飞星火（A3 硬要求）
│  ├─ deepseek.py                     # 备用
│  └─ embedding.py                    # BGE-M3 / bge-large-zh
│
├─ rag/                               [planned] 检索增强
│  ├─ chunker.py
│  ├─ retriever.py                    # BM25 + 向量混合
│  ├─ reranker.py
│  └─ evidence_builder.py             # 证据链构造（落 evidence_chunk_ids）
│
├─ knowledge/                         [planned] 知识库
│  ├─ loaders/
│  │  ├─ course_loader.py             # 课程教材切分入库
│  │  ├─ policy_loader.py             # 政策抓取入库
│  │  └─ fund_loader.py               # 基金导出入库
│  └─ graph.py                        # 知识点前置关系
│
├─ db/                                [planned] SQLAlchemy + Alembic
│  ├─ models/                         # 各表 SQLAlchemy 模型
│  ├─ migrations/                     # Alembic 迁移
│  └─ session.py                      # 数据库会话
│
├─ auth/                              [planned] JWT（演示用）
│  └─ jwt.py
│
└─ streaming/                         [planned] SSE
   └─ sse.py
```

### 6.4 即将新增的 endpoints 全表

| Endpoint | 内部调用 | 优先级 | 文件位置（规划） |
| --- | --- | --- | --- |
| `POST /api/v1/profile/chat` | `career_planner.build_learning_persona` | P0 | `backend/app/api/v1/endpoints/profile.py` |
| `GET/PUT /api/v1/profile/{user_id}` | 直接读写 `user_profiles` | P0 | `endpoints/profile.py` |
| `POST /api/v1/courses/{cid}/plan` | `task_orchestrator.generate_learning_path` | P0 | `endpoints/courses.py` |
| `POST /api/v1/courses/{cid}/resources/generate?type=doc` | `doc_archivist.generate_course_doc` | P0 | `endpoints/courses.py` |
| `POST /api/v1/courses/{cid}/resources/generate?type=ppt` | `doc_archivist.generate_course_ppt` | P0 | `endpoints/courses.py` |
| `POST /api/v1/courses/{cid}/resources/generate?type=mindmap` | `doc_archivist.generate_mindmap` | P0 | `endpoints/courses.py` |
| `POST /api/v1/courses/{cid}/resources/generate?type=video` | `doc_archivist.generate_video_storyboard` | P0 | `endpoints/courses.py` |
| `POST /api/v1/courses/{cid}/resources/generate?type=quiz` | `competition_advisor.generate_quiz` | P0 | `endpoints/courses.py` |
| `POST /api/v1/courses/{cid}/resources/generate?type=lab` | `topic_explorer.generate_hands_on_lab` | P0 | `endpoints/courses.py` |
| `GET /api/v1/tasks/{task_id}/stream` | SSE 进度推送 | P0 | `endpoints/streaming.py` |
| `POST /api/v1/tutor/ask` | `career_planner.route_tutor_question` → 路由 | P1 | `endpoints/tutor.py` |
| `POST /api/v1/assessment/run` | `outcome_evaluator.run_assessment` | P1 | `endpoints/assessment.py` |
| `POST /api/v1/research/funds/recommend` | `career_planner + job_analyst + rag(domain=fund)` | P2 | 扩展 `endpoints/research.py` |
| `POST /api/v1/policy/interpret` | `policy_interpreter.interpret_policy` | P2 | 扩展 `endpoints/policy.py` |
| `GET /api/v1/agents/runs?workflow=&user_id=` | 读 `agent_runs` 表，供前端 trace 可视化 | P1 | `endpoints/agents.py` |
| `GET /api/v1/agents/manifest` | 返回 `agents` + `agent_skills` 注册表 | P1 | `endpoints/agents.py` |

---

## 7. 9 智能体清单与技能映射（核心章节）

### 7.1 政策法规解读智能体（`policy_interpreter`）

**角色描述**：将国家政策、教育政策、网络安全法规与行业标准转化为可计算、可检索、可推理的知识资产；为科研选题、竞赛申报、课程建设、合规审查提供权威政策依据与合规约束。

**五元组**：
- $c_{a}$ = 政策语义结构化、合规判定、政策—能力映射、不确定性提示
- $T_{a}$ = `rag.retrieve(domain="policy")`, `llm.xfyun`, `kg.query`
- $I_{a}$ = `{topic: str, target_type: "research" | "competition" | "course", user_context?: dict}`
- $O_{a}$ = `{summary, capability_mapping, compliance_risks[], suggestions[], citations[]}`
- $\rho_{a}$ = **medium**（含合规判定，结果会被下游 Agent 信任）

**当前已知 skills**：

| Skill | 做什么 | 用 domain | 输出 schema 概要 |
| --- | --- | --- | --- |
| `InterpretPolicy` | 政策原文 → 要点摘要 + 能力映射 + 合规建议 | policy | `PolicyInterpretation` |
| `ComplianceCheck` | 评估对象 x（选题 / 计划书）的合规风险评分 $R_{comp}(x)$ | policy | `ComplianceReport` |
| `AnswerPolicyQuestion` | 智能辅导：政策相关问答 | policy | `TutorAnswer` |

**A3 课程学习工作流位置**：仅在"智能辅导路由"中可能被命中（学生问"AI 安全课程涉及哪些法规"）。
**中枢其他工作流位置**：选题推演 + 竞赛备赛 + 计划书生成的合规闸门。

---

### 7.2 热点舆情研判智能体（`hot_analyst`）

**角色描述**：从安全行业动态、典型事件、CVE/CNVD 公告、社区讨论中识别有教学价值的热点，并控制可滥用风险。

**五元组**：
- $c_{a}$ = 主题聚类、事件抽取、情感分析、传播态势建模、教育转化价值评估
- $T_{a}$ = `rag.retrieve(domain="paper" | "news")`, `llm.xfyun`, `kg.event_graph`
- $I_{a}$ = `{time_window: "24h" | "7d" | "30d", category?: str}`
- $O_{a}$ = `{events[], heat_scores[], edu_value[], abuse_risk[]}`
- $\rho_{a}$ = **high**（涉及攻击细节，输出必经安全护栏）

**当前已知 skills**：

| Skill | 做什么 | 用 domain | 输出 schema 概要 |
| --- | --- | --- | --- |
| `AnalyzeHotEvent` | 单事件深度研判 + 教学价值评分 $E_{edu}(e)$ | paper / news | `HotEventReport` |
| `RecommendReadings` | **协同** topic_explorer 出"拓展阅读" | paper / course | `ReadingList` |
| `AnswerHotQuestion` | 智能辅导：热点事件问答 | paper / news | `TutorAnswer` |

**A3 课程学习工作流位置**：`RecommendReadings`（拓展阅读材料 = A3 5 类资源之一）。
**中枢其他工作流位置**：Workspace 行业热点 panel；Idea Lab 选题灵感来源。

---

### 7.3 招聘需求分析智能体（`job_analyst`）

**角色描述**：将分散的 JD 转化为结构化岗位能力图谱，提供精准的岗位画像、技能差距诊断与能力补齐建议。

**五元组**：
- $c_{a}$ = 岗位字段抽取、技能标准化、能力图谱构建、岗位—学生匹配 $Match(u,j)$
- $T_{a}$ = `rag.retrieve(domain="job")`, `llm.xfyun`, `kg.skill_ontology`
- $I_{a}$ = `{user_profile: dict, target_role?: str, region?: str}`
- $O_{a}$ = `{job_recommendations[], skill_gap_vector, fill_plan[]}`
- $\rho_{a}$ = **low**

**当前已知 skills**：

| Skill | 做什么 | 用 domain | 输出 schema 概要 |
| --- | --- | --- | --- |
| `AnalyzeJobMarket` | 岗位趋势分析 + 能力图谱聚类 | job | `JobMarketReport` |
| `SkillGapAnalysis` | 学生 vs 目标岗位 → $\Delta_{u,j}$ + 填补成本 | job | `SkillGapReport` |

**A3 课程学习工作流位置**：仅用于"学完后推送相关岗位"演示（P2 中枢延展）。
**中枢其他工作流位置**：Careers 页全部功能；P2 基金推荐工作流的协同角色。

---

### 7.4 专业竞赛指导智能体（`competition_advisor`）

**角色描述**：竞赛解析、备赛路径规划、材料协同写作、提交合规审核；A3 中**复用为"题库生成器"**。

**五元组**：
- $c_{a}$ = 竞赛要素解析、契合度评估 $F(\mathscr{U},z)$、备赛路径搜索、题目生成
- $T_{a}$ = `rag.retrieve(domain="competition" | "course")`, `llm.xfyun`
- $I_{a}$ = `{competition_id?: str, knowledge_point_ids?: [str], quiz_type?: str}`
- $O_{a}$ = `{path[], quiz_items[], plan[]}`
- $\rho_{a}$ = **medium**（生成题目需防止泄题 / 抄袭）

**当前已知 skills**：

| Skill | 做什么 | 用 domain | 输出 schema 概要 |
| --- | --- | --- | --- |
| `RecommendCompetition` | 团队 → 适配竞赛排序 | competition | `CompetitionList` |
| `GenerateQuiz` ⭐ | **【A3 关键】** 知识点 → 选 / 填 / 简答 / 代码题 | course | `QuizItemList` |
| `GenerateCompetitionPlan` | 竞赛 → 备赛路径 + 时间表 | competition | `CompetitionPlan` |

**A3 课程学习工作流位置**：`GenerateQuiz`（5 类资源之一：练习题目）。
**中枢其他工作流位置**：Opportunities 竞赛筛选；Writing 计划书章节填充。

---

### 7.5 发展方向规划智能体（`career_planner`）

**角色描述**：**中枢调度角色**。融合政策导向、行业趋势、岗位需求、竞赛机会、科研前沿 + 个人画像，生成可执行的个性化发展规划。在 A3 工作流里同时承担**对话式画像构建**和**意图路由**两大职责。

**五元组**：
- $c_{a}$ = 画像融合、多目标决策、推荐评分 $Match(P_u, g_k)$、阶梯路径生成、意图识别
- $T_{a}$ = 调用所有其他 Agent + `llm.xfyun` + `kg.*`
- $I_{a}$ = `{user_id: str, dialogue_turns?: [str], target_type?: str}`
- $O_{a}$ = `{persona_dimensions{}, ranked_targets[], path, resource_recommendations[]}`
- $\rho_{a}$ = **high**（多目标决策影响下游所有 Agent）

**当前已知 skills**：

| Skill | 做什么 | 用 domain | 输出 schema 概要 |
| --- | --- | --- | --- |
| `BuildLearningPersona` ⭐ | **【A3 关键】** 对话 → 6+ 维画像 | course | `LearningPersona` |
| `UpdatePersona` | 学习行为反馈 → 画像演化 | course | `LearningPersona` |
| `RouteTutorQuestion` ⭐ | **【A3 关键】** 智能辅导意图识别 + 路由 | — | `RoutingDecision` |
| `RecommendResources` ⭐ | **【A3 关键】** 资源精准推送 | course / fund / job | `ResourceFeed` |
| `GenerateGrowthPlan` | 长期发展规划 | all | `GrowthPlan` |

**A3 课程学习工作流位置**：**入口 + 出口**——先建画像、推送资源，结束时更新画像。
**中枢其他工作流位置**：全部工作流的调度中枢。

---

### 7.6 选题推演与科研创意生成智能体（`topic_explorer`）

**角色描述**：基于政策 + 热点 + 岗位 + 竞赛综合生成科研选题、技术路线、风险评估。A3 中复用为**实操案例生成器**。

**五元组**：
- $c_{a}$ = 选题灵感发散、可行性收敛 $\Psi(\sigma)$、技术路线设计、风险评估
- $T_{a}$ = `rag.retrieve(domain="paper" | "course")`, `llm.xfyun`
- $I_{a}$ = `{user_profile, direction?, knowledge_point_ids?}`
- $O_{a}$ = `{topic_candidates[], hands_on_lab?, risk_report}`
- $\rho_{a}$ = **medium**

**当前已知 skills**：

| Skill | 做什么 | 用 domain | 输出 schema 概要 |
| --- | --- | --- | --- |
| `GenerateResearchTopic` | 候选选题池 + 评分 $\Psi(\sigma)$ | paper / fund | `TopicCandidateList` |
| `GenerateHandsOnLab` ⭐ | **【A3 关键】** 实操案例 + 步骤 + 验收点 | course | `HandsOnLab` |
| `RecommendReadings` | **协同** hot_analyst 出"拓展阅读" | paper | `ReadingList` |

**A3 课程学习工作流位置**：`GenerateHandsOnLab`（代码类实操案例）+ `RecommendReadings`。
**中枢其他工作流位置**：Idea Lab / Writing 选题推演。

---

### 7.7 文档生成与成果归档智能体（`doc_archivist`）

**角色描述**：生成文档 / PPT / 思维导图 / 视频脚本 + 版本管理 + 提交清单。A3 中**承担 5 类资源中的 4 类**。

**五元组**：
- $c_{a}$ = 章节模板生成、质量评分 $Q(g)$、多格式输出、版本归档
- $T_{a}$ = `rag.retrieve(domain="course")`, `llm.xfyun`, `tts.xfyun`
- $I_{a}$ = `{topic, structure_template?, user_profile, output_format}`
- $O_{a}$ = `{content, evidence_refs[], quality_score}`
- $\rho_{a}$ = **low**

**当前已知 skills**：

| Skill | 做什么 | 用 domain | 输出 schema 概要 |
| --- | --- | --- | --- |
| `GenerateProposal` | 原有：计划书生成 | paper / policy | `ProposalDoc` |
| `GenerateCourseDoc` ⭐ | **【A3 关键】** 课程讲解文档（Markdown） | course | `CourseDoc` |
| `GenerateCoursePPT` ⭐ | **【A3 关键】** PPT 大纲 + reveal.js | course | `PptSlides` |
| `GenerateMindmap` ⭐ | **【A3 关键】** Markmap / Mermaid 思维导图 | course | `Mindmap` |
| `GenerateVideoStoryboard` ⭐ | **【A3 关键】** 讲解脚本 + 分镜 + TTS 文本 | course | `VideoStoryboard` |

**A3 课程学习工作流位置**：4 类资源的核心生产者。
**中枢其他工作流位置**：Writing 全部功能 + Profile 资产归档。

---

### 7.8 任务规划与学习路径编排智能体（`task_orchestrator`）

**角色描述**：将高层目标转化为可执行任务（WBS + CPM）；A3 中负责**生成知识图谱驱动的个性化学习路径**。

**五元组**：
- $c_{a}$ = WBS 递归拆解、CPM 关键路径、依赖排程、知识图谱遍历
- $T_{a}$ = `kg.knowledge_edges`, `llm.xfyun`
- $I_{a}$ = `{goal, user_profile, knowledge_graph, time_budget}`
- $O_{a}$ = `{path[], milestones[], dependency_graph}`
- $\rho_{a}$ = **low**

**当前已知 skills**：

| Skill | 做什么 | 用 domain | 输出 schema 概要 |
| --- | --- | --- | --- |
| `GenerateLearningPath` ⭐ | **【A3 关键】** 按画像 + 知识图谱前置关系出学习路径 | course | `LearningPath` |
| `DecomposeWBS` | 任务递归拆解 | — | `WBSTree` |

**A3 课程学习工作流位置**：**画像构建之后立即触发**。
**中枢其他工作流位置**：Tasks / Planner / Writing 时间线生成。

---

### 7.9 成果评价与能力画像智能体（`outcome_evaluator`）

**角色描述**：多维评价 + 画像演化 + **生成质量校验**（兼任防幻觉闸门）。

**五元组**：
- $c_{a}$ = 成果多维评分、画像更新公式、质量校验、能力维度演化
- $T_{a}$ = `rag.retrieve(domain="course")`, `llm.xfyun`
- $I_{a}$ = `{submission, user_id, target_dimensions}`
- $O_{a}$ = `{score_vector, quality_score, updated_profile, feedback}`
- $\rho_{a}$ = **high**（直接影响画像与下次推荐）

**当前已知 skills**：

| Skill | 做什么 | 用 domain | 输出 schema 概要 |
| --- | --- | --- | --- |
| `EvaluateSubmission` | 提交物 → 评分向量 $s_g$ | course | `SubmissionEval` |
| `RunAssessment` ⭐ | **【A3 关键】** 学习效果评估 + 画像演化公式 | course | `AssessmentReport` |
| `QualityCheck` ⭐ | **【A3 关键】** 防幻觉质量校验（事实 / 引用 / 合规） | course | `QualityReport` |
| `UpdateCapability` | 画像维度增量更新（写回 `user_profiles`） | course | `CapabilityDelta` |

**A3 课程学习工作流位置**：**所有生成 Agent 的下游闸门** + **画像回流终点**。
**中枢其他工作流位置**：Profile 能力雷达；竞赛备赛材料质量门控。

---

### 7.10 A3 能力 → 智能体 → 技能 → 代码位置完整映射表

| A3 能力 | 智能体 | Skill | 代码位置（预填） |
| --- | --- | --- | --- |
| 对话式画像 ≥ 6 维 | career_planner | `BuildLearningPersona` | `backend/app/agents/career_planner/skills/build_learning_persona.py` |
| 画像随学随新 | outcome_evaluator + career_planner | `UpdateCapability` → `UpdatePersona` | `backend/app/agents/outcome_evaluator/skills/update_capability.py` + `backend/app/agents/career_planner/skills/update_persona.py` |
| 专业课程讲解文档 | doc_archivist | `GenerateCourseDoc` | `backend/app/agents/doc_archivist/skills/generate_course_doc.py` |
| PPT 生成 | doc_archivist | `GenerateCoursePPT` | `backend/app/agents/doc_archivist/skills/generate_course_ppt.py` |
| 思维导图 | doc_archivist | `GenerateMindmap` | `backend/app/agents/doc_archivist/skills/generate_mindmap.py` |
| 多模态视频 / 动画 | doc_archivist | `GenerateVideoStoryboard` | `backend/app/agents/doc_archivist/skills/generate_video_storyboard.py` |
| 不同类型练习题 | competition_advisor | `GenerateQuiz` | `backend/app/agents/competition_advisor/skills/generate_quiz.py` |
| 拓展阅读材料 | hot_analyst + topic_explorer | `RecommendReadings`（协同） | `backend/app/agents/hot_analyst/skills/recommend_readings.py` + `backend/app/agents/topic_explorer/skills/recommend_readings.py` |
| 代码类实操案例 | topic_explorer | `GenerateHandsOnLab` | `backend/app/agents/topic_explorer/skills/generate_hands_on_lab.py` |
| 个性化学习路径 | task_orchestrator | `GenerateLearningPath` | `backend/app/agents/task_orchestrator/skills/generate_learning_path.py` |
| 资源精准推送 | career_planner | `RecommendResources` | `backend/app/agents/career_planner/skills/recommend_resources.py` |
| 智能辅导意图识别 | career_planner | `RouteTutorQuestion` | `backend/app/agents/career_planner/skills/route_tutor_question.py` |
| 智能辅导分发回答 | policy / hot / topic / doc 各 Agent | `AnswerXxxQuestion` 变体 | `backend/app/agents/<role>/skills/answer_*.py` |
| 学习效果评估 | outcome_evaluator | `RunAssessment` | `backend/app/agents/outcome_evaluator/skills/run_assessment.py` |
| 防幻觉生成质量校验 | outcome_evaluator | `QualityCheck` | `backend/app/agents/outcome_evaluator/skills/quality_check.py` |

---

## 8. 横切基础设施层

> 4 个组件——**不是智能体**，是所有 9 Agent 共用的工程层。

### 8.1 RAG 检索服务（`backend/app/rag/`）

**对应原"知识检索与证据链管理智能体"（设计文档 1.5.3.2）**

| 文件 | 关键接口 |
| --- | --- |
| `rag/chunker.py` | `chunk_document(text: str, size=600, overlap=100) -> list[Chunk]` |
| `rag/retriever.py` | `retrieve(query: str, domain: str, top_k=10, filter: dict=None) -> list[ChunkHit]`，内部并行 BM25 + 向量 → RRF |
| `rag/reranker.py` | `rerank(query: str, hits: list[ChunkHit]) -> list[ChunkHit]`，BGE-Reranker 或 LLM rerank |
| `rag/evidence_builder.py` | `build_evidence(hits: list[ChunkHit]) -> list[Evidence]`，构造 citations + 计算 $C(q,d)$ |

**底层评分函数**（沿用设计文档 3.4.3）：

$$S_{retr}(q,d) = w_1 \mathrm{BM25}(q,d) + w_2 \mathrm{Vec}(q,d) + w_3 \mathrm{Fresh}(d) + w_4 T(s_d)$$

**调用关系**：9 Agent 全部通过 `rag.retrieve()` 取证据，**禁止**直接拼 prompt 跳过 RAG。

### 8.2 数据采集 ETL（`backend/app/knowledge/loaders/`）

**对应原"多源数据采集与治理智能体"（设计文档 1.5.3.1）**

**离线脚本**形式，非在线服务。`pyproject.toml` 已声明 `lxml` + `playwright` 依赖。

| 文件 | 作用 |
| --- | --- |
| `loaders/course_loader.py` | 课程教材 PDF/Markdown → `documents + chunks (domain='course_websec')` |
| `loaders/policy_loader.py` | 政策抓取（从 `endpoints/policy.py` 现有 10 条标题扩展为正文） |
| `loaders/fund_loader.py` | 基金导出（从 `research_repository.py` 硬编码数据导出） |

**调用关系**：通过 CLI 触发，不在请求路径上。

### 8.3 Agent 路由 / 任务分发（`backend/app/runtime/`）

**对应原"系统调度与多智能体编排智能体"（设计文档 1.5.3.7）**

| 文件 | 关键接口 |
| --- | --- |
| `runtime/capability_manifest.py` | `register_agent(agent_id, capabilities, tools, input_schema, output_schema, risk_level)`，启动时填 `agents` 表 |
| `runtime/router.py` | `route(task: Task) -> Agent`，实现路由评分函数 $Score(a_i, t) = \alpha S_{cap} + \beta S_{ctx} + \gamma S_{tool} + \delta S_{risk} + \epsilon S_{hist}$ |
| `runtime/graphs/course_learning.py` | LangGraph DAG 定义课程学习多智能体工作流 |
| `runtime/graphs/fund_recommendation.py` | P2 基金推荐 DAG |
| `runtime/graphs/tutor_routing.py` | P1 智能辅导路由 DAG |

**调用关系**：FastAPI endpoint → `runtime.graphs.*.run(ctx)` → 多 Agent 协同 → 输出。

### 8.4 安全护栏 / 防注入（`backend/app/runtime/guardrails/`）

**对应原"安全监控与合规审核智能体"（设计文档 1.5.3.8 / 1.5.5）**

| 文件 | 作用 |
| --- | --- |
| `guardrails/input_filter.py` | 用户输入 → 敏感词 / 提示注入检测 |
| `guardrails/output_filter.py` | 模型输出 → 合规检测 + 引用一致性 + 敏感内容遮蔽 |
| `guardrails/prompt_injection_check.py` | 检测外部检索内容中的越权指令 |

**调用关系**：作为 FastAPI middleware + LangGraph 每个节点的前后 hook。

---

## 9. 数据库与数据模型（Data-layer v2 schema）

> **"12 张表唯一" 的旧约束已退役**。新约束是 **"不为 domain 单建知识表"**，而非 "不增表"。任何新增的扩展表必须复用本节定义的统一资产 / 资源 / 存储 / 能力分组。
>
> 权威性顺序（本节是源头）：`.codex/AGENTS.md §9` > `CLAUDE.md §8` > `../CompetitionTheme/A3赛题规划.md §5`。

### 9.0 表分组与优先级

| 分组 | 表（P0 必做） | 表（P1/P2 扩展） | SQLAlchemy 模型目录 |
| --- | --- | --- | --- |
| A. 身份与画像 | `users` · `user_profiles` · `user_capabilities` | — | `backend/app/db/models/identity/` |
| B. 统一知识资产 | `documents` · `document_assets` · `chunks` · `knowledge_nodes` · `knowledge_edges` · `courses` | — | `backend/app/db/models/knowledge/` |
| C. 学习闭环 | `learning_events` · `quiz_items` · `quiz_attempts` | `learning_paths` · `learning_tasks` | `backend/app/db/models/learning/` |
| D. 多智能体注册与运行 | `agents` · `agent_skills` · `agent_runs` | `agent_messages` | `backend/app/db/models/agent/` |
| E. 生成资源与存储 | `generated_resources` · `storage_objects` | `resource_versions` | `backend/app/db/models/resource/` + `backend/app/db/models/storage/` |

**P0 共 17 张**；P1/P2 共 4 张。

### 9.1 完整 schema（DDL + SQLAlchemy 模型路径）

```sql
-- ========== A. 身份与画像 ==========
users (
  id UUID PRIMARY KEY,
  ...
);
-- SQLAlchemy: backend/app/db/models/identity/user.py

user_profiles (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  dimensions JSONB,                -- 6+ 维 merged persona
  embedding VECTOR(1024),          -- 画像向量（跨模块语义匹配）
  updated_at TIMESTAMP
);
-- SQLAlchemy: backend/app/db/models/identity/user_profile.py

user_capabilities (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  dimension VARCHAR(128),          -- web_security / crypto / reverse / ...
  score FLOAT DEFAULT 0.0,
  confidence FLOAT DEFAULT 0.0,
  evidence_count INT DEFAULT 0,
  metadata JSONB,
  UNIQUE(user_id, dimension)
);
-- SQLAlchemy: backend/app/db/models/identity/user_capability.py


-- ========== B. 统一知识资产层 ==========
documents (
  id UUID PRIMARY KEY,
  domain VARCHAR(64) NOT NULL,     -- course_websec / policy / fund / job / competition / paper / news
  source_type VARCHAR(64),
  title TEXT NOT NULL,
  url TEXT,
  content_hash VARCHAR(128),       -- 去重 / 增量
  raw_text TEXT,                   -- 可空：长文档落 document_assets
  metadata JSONB,
  trust_score FLOAT DEFAULT 0.5,
  status VARCHAR(32) DEFAULT 'pending',  -- pending / ready / failed
  fetched_at TIMESTAMP
);
-- UNIQUE(domain, url) WHERE url IS NOT NULL
-- INDEX(domain, status) / INDEX(content_hash) / GIN(metadata)
-- SQLAlchemy: backend/app/db/models/knowledge/document.py

document_assets (
  id UUID PRIMARY KEY,
  document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
  asset_type VARCHAR(64) NOT NULL, -- original_pdf / original_docx / markdown_full / markdown_chapter / page_text / page_image / cover_image / ocr_text / transcript
  object_key TEXT NOT NULL,        -- 指向 storage_objects 或本地路径
  mime_type VARCHAR(128),
  size_bytes BIGINT,
  content_hash VARCHAR(128),
  metadata JSONB
);
-- SQLAlchemy: backend/app/db/models/knowledge/document_asset.py

chunks (
  id UUID PRIMARY KEY,
  document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
  domain VARCHAR(64) NOT NULL,     -- 冗余字段，方便过滤
  chunk_text TEXT NOT NULL,
  chunk_index INT NOT NULL,
  token_count INT,
  embedding VECTOR(1024),          -- 可空：异步向量化
  embedding_status VARCHAR(32) DEFAULT 'pending',  -- pending / ready / failed
  metadata JSONB,
  UNIQUE(document_id, chunk_index)
);
-- INDEX(domain, embedding_status) / GIN(metadata)
-- HNSW: CREATE INDEX ... ON chunks USING hnsw (embedding vector_cosine_ops)
--   fallback IVFFlat: USING ivfflat (embedding vector_cosine_ops) WITH (lists=100)
-- SQLAlchemy: backend/app/db/models/knowledge/chunk.py

courses (
  id UUID PRIMARY KEY,
  code VARCHAR(64) UNIQUE,
  title TEXT,
  domain VARCHAR(64),
  description TEXT
);
-- SQLAlchemy: backend/app/db/models/knowledge/course.py

knowledge_nodes (
  id UUID PRIMARY KEY,
  domain VARCHAR(64) NOT NULL,
  course_id UUID REFERENCES courses(id),
  name VARCHAR(255) NOT NULL,
  description TEXT,
  node_type VARCHAR(64) DEFAULT 'concept',  -- concept / skill / tool / topic / standard
  level INT,
  metadata JSONB
);
-- SQLAlchemy: backend/app/db/models/knowledge/knowledge_node.py

knowledge_edges (
  source_id UUID REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
  target_id UUID REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
  edge_type VARCHAR(64),           -- prerequisite / related_to / requires / supports / extends
  weight FLOAT DEFAULT 1.0,
  metadata JSONB,
  PRIMARY KEY (source_id, target_id, edge_type)
);
-- SQLAlchemy: backend/app/db/models/knowledge/knowledge_edge.py


-- ========== C. 学习闭环 ==========
learning_events (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  event_type VARCHAR(64),          -- view_doc / quiz_correct / quiz_wrong / complete_lab / ...
  kp_id UUID REFERENCES knowledge_nodes(id),
  resource_id UUID,                -- 软引用 generated_resources
  result JSONB,
  occurred_at TIMESTAMP
);
-- SQLAlchemy: backend/app/db/models/learning/learning_event.py

quiz_items (
  id UUID PRIMARY KEY,
  kp_id UUID REFERENCES knowledge_nodes(id),
  type VARCHAR(32),                -- single_choice / multi_choice / fill / short_answer / code
  question TEXT,
  options JSONB,
  answer TEXT,
  difficulty INT,
  generated_by_skill UUID,
  created_at TIMESTAMP
);
-- SQLAlchemy: backend/app/db/models/learning/quiz_item.py

quiz_attempts (
  id UUID PRIMARY KEY,
  quiz_item_id UUID REFERENCES quiz_items(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  submitted_answer JSONB,
  is_correct BOOLEAN,
  score FLOAT,
  feedback TEXT,
  metadata JSONB
);
-- SQLAlchemy: backend/app/db/models/learning/quiz_attempt.py


-- ========== D. 多智能体注册与运行 ==========
agents (
  id UUID PRIMARY KEY,
  name VARCHAR UNIQUE,             -- policy_interpreter / hot_analyst / ...
  role_description TEXT,
  capability_vector VECTOR(64),    -- c_{a_i}
  tools TEXT[],
  input_schema JSONB,
  output_schema JSONB,
  risk_level VARCHAR(16),          -- low / medium / high
  enabled BOOLEAN DEFAULT TRUE
);
-- SQLAlchemy: backend/app/db/models/agent/agent.py

agent_skills (
  id UUID PRIMARY KEY,
  agent_id UUID REFERENCES agents(id),
  skill_name VARCHAR,
  prompt_template TEXT,
  applicable_domains TEXT[],
  required_tools TEXT[],
  output_schema JSONB,
  version INT,
  enabled BOOLEAN DEFAULT TRUE,
  updated_at TIMESTAMP,
  UNIQUE(agent_id, skill_name, version)
);
-- SQLAlchemy: backend/app/db/models/agent/agent_skill.py

agent_runs (
  id UUID PRIMARY KEY,
  workflow_name VARCHAR,           -- course_learning / fund_recommendation / tutor_routing
  user_id UUID,
  agent_id UUID REFERENCES agents(id),
  skill_id UUID REFERENCES agent_skills(id),
  parent_run_id UUID REFERENCES agent_runs(id),
  input_summary JSONB,
  output_summary JSONB,
  evidence_chunk_ids UUID[],
  quality_score FLOAT,
  status VARCHAR(16),              -- success / failed / blocked
  duration_ms INT,
  token_usage JSONB,
  created_at TIMESTAMP
);
-- SQLAlchemy: backend/app/db/models/agent/agent_run.py


-- ========== E. 生成资源与存储 ==========
generated_resources (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  course_id UUID REFERENCES courses(id),
  kp_id UUID REFERENCES knowledge_nodes(id),
  agent_run_id UUID REFERENCES agent_runs(id),
  resource_type VARCHAR(64) NOT NULL,  -- course_doc / course_ppt / mindmap / quiz_set / hands_on_lab / video_storyboard / reading_list / assessment_report
  title TEXT NOT NULL,
  content JSONB,                       -- 小型结构化内容直接落 JSONB
  object_key TEXT,                     -- 大文件走 storage_objects
  evidence_chunk_ids UUID[],
  quality_score FLOAT,
  status VARCHAR(32) DEFAULT 'ready',  -- generating / ready / failed
  metadata JSONB
);
-- SQLAlchemy: backend/app/db/models/resource/generated_resource.py

storage_objects (
  id UUID PRIMARY KEY,
  provider VARCHAR(32) DEFAULT 'local',  -- local / minio / s3 / oss / cos / r2
  bucket VARCHAR(128),
  object_key TEXT UNIQUE NOT NULL,
  original_filename TEXT,
  mime_type VARCHAR(128),
  size_bytes BIGINT,
  content_hash VARCHAR(128),
  status VARCHAR(32) DEFAULT 'ready',
  metadata JSONB
);
-- SQLAlchemy: backend/app/db/models/storage/storage_object.py
```

### 9.2 关键索引说明

| 索引 | 作用 |
| --- | --- |
| `chunks USING hnsw (embedding vector_cosine_ops)`（fallback IVFFlat） | pgvector 近似最近邻，向量检索关键；HNSW 优先，pgvector < 0.5.0 时退回 IVFFlat |
| `documents(domain, status)` + `chunks(domain, embedding_status)` | 多 domain 过滤 + 入库 / 向量化生命周期 |
| `documents(content_hash)` + `document_assets(content_hash)` + `storage_objects(content_hash)` | 文件级去重 |
| `GIN(documents.metadata)` + `GIN(chunks.metadata)` | JSONB 高频字段过滤 |
| `knowledge_edges(source_id, target_id, edge_type)` PK | 图遍历主键 |
| `user_capabilities(user_id, dimension)` UNIQUE | 雷达图维度去重 |
| `agent_runs(workflow_name, created_at DESC)` / `(user_id, created_at DESC)` | trace 可视化按工作流 / 个人倒序 |
| `quiz_items(kp_id)` / `quiz_attempts(user_id)` | 题库按知识点取 / 错题回放 |
| `learning_events(user_id, occurred_at DESC)` | 学习行为时序回放 |
| `generated_resources(user_id, course_id, resource_type)` | 资源工作台筛选 |

### 9.3 迁移工具

- **Alembic**：`backend/app/db/migrations/`
- 命名约定：`YYYYMMDD_HHMM_<verb>_<noun>.py`，如 `20260610_1430_create_agents_and_skills.py`
- 首次迁移必须包含 `CREATE EXTENSION IF NOT EXISTS vector;`

### 9.4 pgvector 扩展启用

PostgreSQL 16 启动后：
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
docker-compose 中 backend 服务依赖 PostgreSQL 16 的镜像（**待添加**到 `docker-compose.yml`）。

---

## 10. 知识库构建 SOP

### 10.1 6 步建设流程

| Step | 动作 | 工具 | 落点 |
| --- | --- | --- | --- |
| 1 | **选课 + 收集原始资料**（1–2 天，人工） | — | 推荐《Web 安全基础》：1 本主教材 + 5–10 篇论文/RFC/博客 + 2–3 个实验手册 + OWASP Top 10 |
| 2 | **文档切分 + 元数据标注** | LangChain `RecursiveCharacterTextSplitter`（500–800 tokens、overlap 100） | `documents` + `chunks` 表，`metadata = {kp_ids: [], difficulty: 1-5, type: '概念'/'案例'/'代码'/'实验'}` |
| 3 | **知识点抽取 + 前置关系图** | LLM 辅助 + 人工校对 | `knowledge_nodes` + `knowledge_edges`（50–100 节点，`edge_type='prerequisite'`） |
| 4 | **向量化入库** | BGE-M3 / bge-large-zh / 讯飞 embedding | `chunks.embedding` |
| 5 | **混合检索接口** | `rag/retriever.py`（BM25 + 向量 + RRF + rerank） | 输入：query + 画像 + kp 过滤 + domain；输出：带证据的 chunks |
| 6 | **画像随学随新** | `outcome_evaluator.update_capability` + `career_planner.update_persona` | `user_profiles.dimensions.weak_points` 更新 |

### 10.2 每步对应的脚本位置

| Step | 脚本 |
| --- | --- |
| 1 | （非脚本，目录 `backend/data/raw/course_websec/`） |
| 2 | `backend/app/knowledge/loaders/course_loader.py` |
| 3 | `backend/app/knowledge/loaders/extract_kps.py`（新增） |
| 4 | `backend/app/knowledge/loaders/embed_chunks.py`（新增） |
| 5 | `backend/app/rag/retriever.py` |
| 6 | `backend/app/agents/outcome_evaluator/skills/update_capability.py` |

### 10.3 数据来源建议

| 域 | 来源 |
| --- | --- |
| 课程（Web 安全） | OWASP Top 10、PortSwigger Web Security Academy 公开教程、OWASP 测试指南、《白帽子讲 Web 安全》、CVE/CNVD 公告精选 |
| 政策 | 现有 `endpoints/policy.py` 10 条标题 + 抓取 cac.gov.cn 正文 |
| 基金 | `research_repository.py` 现有硬编码数据 |
| 赛事 | CTFtime API（已接入 `endpoints/ctftime.py`） |
| 论文 | arXiv 网安分类 RSS |
| 岗位 | 公开 JD（合规：仅公开页面，不绕过登录） |

### 10.4 知识图谱节点数量目标

- 课程 domain：**50–100** 知识点（覆盖大纲 80%）
- 政策 domain：30–50 条款（10 条原有 + 扩展）
- 基金 domain：50+（导自现有 mock）
- 总 chunks：**≥ 500**（A3 评委不会数；500 是"够撑演示又不至于拖慢检索"的甜点）

---

## 11. LLM / Agent 框架技术决策

| 决策 | 选型 | 理由 |
| --- | --- | --- |
| **主模型** | **讯飞星火**（v4.0 Ultra 或当时主流） | A3 硬要求 |
| **备用模型** | DeepSeek / Qwen | 讯飞额度耗尽 / 速率超限时降级 |
| **Embedding** | BGE-M3（首选）/ bge-large-zh / 讯飞 embedding | 中文效果 + 1024 维向量适配 pgvector |
| **Agent 框架** | **LangGraph** | 显式 DAG + 节点级超时 / 重试 / 条件边 / human-in-loop；比 AutoGen / CrewAI 更适合"工作流可视化" |
| **流式协议** | **SSE**（Server-Sent Events） | FastAPI 原生支持 `StreamingResponse(media_type="text/event-stream")`；前端 `EventSource` 一行接入；比 WebSocket 简单 |
| **模型 client 封装位置** | `backend/app/llm/` | `xfyun.py` / `deepseek.py` / `embedding.py` |
| **TTS（视频音频）** | 讯飞 TTS（在线 API） | A3 用讯飞工具；轻量化避免本地模型 |

### 11.1 SSE 事件类型规范（强制）

| 事件类型 | 时机 | data 内容 |
| --- | --- | --- |
| `token` | LLM 流式 token | `{content: "..."}` |
| `evidence` | RAG 命中证据 | `{chunk_id, source, excerpt, reliability}` |
| `progress` | 工作流节点完成 | `{node_name, status, agent_id, skill_id, percentage}` |
| `done` | 工作流结束 | `{run_id, final_output_ref, quality_score}` |
| `error` | 异常 | `{code, message, recoverable}` |

前端 `react-markdown` 增量渲染 `token`；`evidence` 推入 `EvidenceDrawer`；`progress` 驱动 Agent 活动可视化面板。

---

## 12. 开发优先级（P0 / P1 / P2）

| 任务 | 优先级 | 关联智能体 | 关联代码路径 | 预估工时 |
| --- | --- | --- | --- | --- |
| LLM 客户端封装（讯飞 + 备用） | P0 | — | `backend/app/llm/*` | 4h |
| LangGraph 运行时 + 路由 | P0 | — | `backend/app/runtime/router.py` + `graphs/course_learning.py` | 8h |
| 9 智能体代码骨架（`agent.py` + 空 `skills/`） | P0 | 9 个 | `backend/app/agents/*` | 4h |
| RAG 检索服务（BM25 + pgvector + rerank） | P0 | — | `backend/app/rag/*` | 8h |
| 数据库 + SQLAlchemy + Alembic 初始迁移 | P0 | — | `backend/app/db/*` | 6h |
| Agents/Skills 表初始数据（9 行 + 各自 skill） | P0 | 9 个 | Alembic 数据迁移 | 2h |
| 课程知识库（Web 安全 50+ chunks） | P0 | — | `knowledge/loaders/course_loader.py` + 数据准备 | 12h |
| `BuildLearningPersona` skill | P0 | career_planner | `agents/career_planner/skills/build_learning_persona.py` | 4h |
| `GenerateLearningPath` skill | P0 | task_orchestrator | `agents/task_orchestrator/skills/generate_learning_path.py` | 4h |
| `GenerateCourseDoc/PPT/Mindmap/VideoStoryboard` 4 skills | P0 | doc_archivist | `agents/doc_archivist/skills/*` | 12h |
| `GenerateQuiz` skill | P0 | competition_advisor | `agents/competition_advisor/skills/generate_quiz.py` | 4h |
| `GenerateHandsOnLab` skill | P0 | topic_explorer | `agents/topic_explorer/skills/generate_hands_on_lab.py` | 4h |
| `RunAssessment` + `QualityCheck` skills | P0 | outcome_evaluator | `agents/outcome_evaluator/skills/*` | 6h |
| `RecommendResources` skill | P0 | career_planner | `agents/career_planner/skills/recommend_resources.py` | 4h |
| SSE 流式响应封装 | P0 | — | `backend/app/streaming/sse.py` | 4h |
| 防幻觉三道闸接入（检索门槛 + 证据回链 + 二次校验） | P0 | outcome_evaluator | 跨多文件 | 6h |
| 前端 `/course` 页 + CourseStudy feature | P0 | — | `frontend/src/app/pages/CourseStudy.tsx` + `features/course/*` | 16h |
| 前端 Chat 接真后端流式 | P0 | career_planner | `features/chat/api.ts` | 4h |
| `RouteTutorQuestion` + 智能辅导路由工作流 | P1 | career_planner + 多 | `agents/career_planner/skills/route_tutor_question.py` + `runtime/graphs/tutor_routing.py` | 8h |
| `CapabilityRadarCard` 接真数据 + 画像随学随新闭环 | P1 | outcome_evaluator | `features/profile/components/CapabilityRadarCard.tsx` + 后端 | 6h |
| Agent 运行 trace 可视化面板 | P1 | — | `features/profile/components/AgentRunsPanel.tsx`（新增） + `endpoints/agents.py` | 8h |
| 政策 / 热点 / 招聘 3 Agent 各加 1 个 skill | P2 | policy / hot / job | `agents/{policy,hot,job}_*/skills/*` | 12h |
| 基金推荐工作流（中枢延展演示） | P2 | career_planner + job_analyst | `runtime/graphs/fund_recommendation.py` + `endpoints/research.py` 扩展 | 8h |
| Forum / Workspace 视觉一致性修补 | P2 | — | feature 组件级修改 | 8h |

**总估算**：P0 ≈ 112h，P1 ≈ 22h，P2 ≈ 28h，合计 ~162h（约 4 周满负荷）

---

## 13. 实施路线图

### 13.1 Day 0 — 半天内拍板

- **选课**：建议《Web 安全基础》
- **演示故事线**：大二学生 → 画像构建 → Web 安全学习路径 → 完成 SQL 注入这一节学习（5+ 资源全展示）→ 测试后系统识别其适合 Web 安全方向 → 推送相关赛事 + 基金（中枢延展）

### 13.2 Week 1 — 最小垂直切片

| Day | 任务 |
| --- | --- |
| Day 1–2 | 基础设施：`agents/base.py` + `runtime/` + `llm/` + `rag/` + `db/` + 9 行 agents 表数据 |
| Day 3–4 | 单知识点闭环（SQL 注入）：5 Agent 协同跑通（`BuildLearningPersona` + `GenerateLearningPath` + `GenerateCourseDoc/PPT` + `GenerateQuiz` + `RunAssessment + QualityCheck`） |
| Day 5–7 | 前端 `/course` 基础版 + Chat 接真后端流式 + 智能体活动面板基础版 + 端到端 demo 草版录制 |

### 13.3 Week 2 — 全课程 + 多模态

- 剩余知识点全部入库
- `doc_archivist` 补 `GenerateMindmap` + `GenerateVideoStoryboard` 两 skill
- `topic_explorer` 补 `GenerateHandsOnLab`
- 智能辅导路由（P1-1）
- 效果评估闭环 + 画像随学随新（P1-2）

### 13.4 Week 3 — 补 Agent + 中枢延展

- 政策、热点、招聘 3 Agent 上线（各至少 1 skill）
- 基金推荐工作流（P2-1）
- Agent runs 可视化完善

### 13.5 Week 4 — 打磨 + 答辩材料

- 响应时间调优、防幻觉准确率测试、生成质量人工评估
- 演示视频录制（按 §17 分镜）
- 文档对齐 + 开源 / AI Coding 工具声明

---

## 14. A3 需求 checklist

### 14.1 核心要求

| # | 要求 | 承接 | 完成状态 |
| --- | --- | --- | --- |
| 1 | 课程知识库 ≥ 50 chunks，覆盖大纲 80% | knowledge/loaders/course_loader.py | **未开始** |
| 2 | 对话式画像 ≥ 6 维 | career_planner.BuildLearningPersona | **未开始** |
| 3 | 显式多智能体架构（≥ 5 协作） | 9 Agent 全注册 + 课程工作流串联 6 个 | **未开始** |
| 4 | 5+ 资源类型生成 | doc_archivist（4） + competition_advisor（题库） + topic_explorer（实操） = 6 种 | **未开始** |
| 5 | 学习路径规划 | task_orchestrator.GenerateLearningPath | **未开始** |
| 6 | 个性化资源精准推送 | career_planner.RecommendResources | **未开始** |
| 7 | 智能辅导（加分） | career_planner.RouteTutorQuestion + 多 Agent | **未开始** |
| 8 | 学习效果评估（加分） | outcome_evaluator.RunAssessment | **未开始** |
| 9 | 流式输出 / 进度追踪 | streaming/sse.py + 5 类 SSE 事件 | **未开始** |
| 10 | 防幻觉：RAG 强制证据 + 二次校验 | rag/* + outcome_evaluator.QualityCheck | **未开始** |
| 11 | 显著位置标注开源项目与协议 | README + 演示 PPT + 配套文档 | **未开始** |
| 12 | 使用讯飞 AI 工具并文档说明 | llm/xfyun.py + 讯飞 TTS + 文档段落 | **未开始** |
| 13 | AI Coding 工具使用说明 | 文档章节：Claude Code + Cursor 使用方式 | **未开始** |
| 14 | PPT / 可运行项目 / ≤ 7 分钟视频 / 配套文档 | 物料交付 | **未开始** |

### 14.2 中枢延展点（创新分 + 实用性分加成）

| # | 要求 | 完成状态 |
| --- | --- | --- |
| 15 | 9 Agent 在 ≥ 2 个工作流中协作（课程 + 基金推荐） | **未开始** |
| 16 | 画像跨工作流共享（课程画像驱动其他模块推送） | **未开始** |
| 17 | 学习闭环延伸（学完课程 → 推送赛事 / 基金 / 岗位） | **未开始** |
| 18 | Agent 运行 trace 前端可视化 | **未开始** |
| 19 | 统一知识资产层 + 技能注册表 | **未开始** |

---

## 15. 开发约定与代码规范

### 15.1 命名约定

| 对象 | 规范 | 示例 |
| --- | --- | --- |
| 智能体目录 | `snake_case`，与 `agents.name` 字段一致 | `career_planner/` |
| Agent 类名 | `PascalCase + Agent` 后缀 | `CareerPlannerAgent` |
| Skill 函数 / 类 | `PascalCase`（动词开头） | `BuildLearningPersona` / `GenerateCourseDoc` |
| Skill 文件名 | `snake_case`，与 `agent_skills.skill_name` 蛇形化一致 | `build_learning_persona.py` |
| Workflow 文件名 | `<场景>_<动作>.py` | `course_learning.py` / `fund_recommendation.py` |
| Pydantic schema | `PascalCase`，输出对象以 `Result` / `Report` / `Doc` 后缀 | `LearningPersona` / `QualityReport` |
| Alembic 迁移 | `YYYYMMDD_HHMM_<verb>_<noun>.py` | `20260610_1430_create_agents.py` |
| 前端 feature | `kebab-case` 目录 / `PascalCase` 组件 | `features/course/components/ResourceTabs.tsx` |

### 15.2 Agent 文件骨架模板

`backend/app/agents/<role>/agent.py`：

```python
from app.agents.base import BaseAgent, AgentCapability
from app.agents.<role>.skills import (
    skill_one, skill_two,
)


class <Role>Agent(BaseAgent):
    """<一句话角色描述>"""

    name = "<role>"   # 与 agents.name 一致
    role_description = "<完整角色描述>"
    capability_vector = AgentCapability(
        policy=0.0, hot=0.0, job=0.0, competition=0.0,
        planning=0.0, topic=0.0, doc=0.0, task=0.0, eval=0.0,
    )
    tools = ["rag.retrieve", "llm.xfyun"]
    risk_level = "low"  # low / medium / high

    skills = {
        "SkillOne": skill_one.SkillOne,
        "SkillTwo": skill_two.SkillTwo,
    }
```

### 15.3 Skill 文件骨架模板

`backend/app/agents/<role>/skills/<skill_name>.py`：

```python
from pydantic import BaseModel
from app.agents.base import BaseSkill
from app.rag.retriever import retrieve
from app.llm.xfyun import xfyun_chat
from app.runtime.guardrails.output_filter import safety_review


# === Output schema ===
class SkillNameOutput(BaseModel):
    """O_{a_i}: 输出契约"""
    field_a: str
    field_b: list[str]
    evidence_chunk_ids: list[str]
    quality_score: float


# === Input schema ===
class SkillNameInput(BaseModel):
    """I_{a_i}: 输入契约"""
    user_id: str
    query: str
    domain: str = "course_websec"


# === Prompt template ===
PROMPT_TEMPLATE = """
你是 <agent role>，现在执行 <skill 任务>。

[上下文证据]
{evidence_text}

[学生画像]
{persona_text}

[任务]
{task_instruction}

请按以下 JSON 格式输出，且 evidence_chunk_ids 必须列出引用过的 chunk_id：
{output_schema_hint}
"""


# === Skill 实现 ===
class SkillName(BaseSkill):
    name = "SkillName"
    applicable_domains = ["course_websec"]
    output_schema = SkillNameOutput

    async def run(self, inp: SkillNameInput, ctx) -> SkillNameOutput:
        # 1. 检索证据（铁律 §3.6）
        hits = await retrieve(inp.query, domain=inp.domain, top_k=8)
        if len(hits) < ctx.config.min_evidence:
            raise InsufficientEvidence("证据不足")

        # 2. 构造 prompt
        prompt = PROMPT_TEMPLATE.format(
            evidence_text="\n".join(h.chunk_text for h in hits),
            persona_text=ctx.persona_summary,
            task_instruction=inp.query,
            output_schema_hint=SkillNameOutput.model_json_schema(),
        )

        # 3. LLM 调用（带流式）
        raw = await xfyun_chat(prompt, stream=ctx.stream)

        # 4. 结构化解析 + 安全护栏（铁律 §3.6 / §3.7）
        out = SkillNameOutput.model_validate_json(raw)
        out = safety_review(out)
        out.evidence_chunk_ids = [h.chunk_id for h in hits]

        # 5. 写 agent_runs（铁律 §3.7）
        await ctx.log_run(
            agent_id=self.agent_id,
            skill_id=self.skill_id,
            input_summary=inp.model_dump(),
            output_summary=out.model_dump(),
            evidence_chunk_ids=out.evidence_chunk_ids,
            quality_score=out.quality_score,
        )
        return out
```

### 15.4 前后端 API 契约

- ✅ 所有响应**必须**用 Pydantic schema（严禁 `dict[str, Any]` 直返）
- ✅ 所有列表接口**必须**分页：`?page=1&page_size=20`，响应 `{items, total, page, page_size}`
- ✅ 所有时间字段**必须** ISO 8601（如 `2026-06-10T14:30:00Z`）
- ✅ 所有 ID **必须** UUID（前端 `string` 类型，禁止用自增 int）
- ✅ HTTP 状态码：200 成功 / 400 客户端错误 / 401 未认证 / 403 越权 / 404 不存在 / 422 校验失败 / 429 限流 / 500 服务端 / 502 上游（如讯飞 API 失败） / 503 降级
- ✅ 错误响应统一 `{detail: str, code?: str}`（FastAPI 默认 `detail`，可扩展 `code`）

### 15.5 日志：所有 Agent 调用必须落 `agent_runs`

**违反铁律 §3.7 = 代码不能合入**。

`agent_runs` 写入示例：
```python
await ctx.log_run(
    workflow_name="course_learning",
    agent_id=...,
    skill_id=...,
    parent_run_id=...,
    input_summary={"query": ...},
    output_summary={"resource_id": ...},
    evidence_chunk_ids=[...],
    quality_score=0.92,
    status="success",
    duration_ms=1234,
    token_usage={"prompt": 1024, "completion": 512, "model": "spark-v4"},
)
```

### 15.6 不要做

- ❌ 不在生产代码里 `print()`（用 `app.core.logging` 的 logger）
- ❌ 不直接 `httpx.AsyncClient()`（统一通过 `app/llm/` 封装，便于切换备用）
- ❌ 不绕过 `rag/retriever.py` 直接构造 SQL 查 chunks
- ❌ 不在 endpoint 函数里写业务逻辑（一律走 service → agent / repository）

---

## 16. 测试策略

### 16.1 单元测试

| 对象 | 最少测试数 | 内容 |
| --- | --- | --- |
| 每个 Skill | ≥ 1 | 输入合法 → 输出符合 schema；缺证据 → `InsufficientEvidence` |
| 每个 Workflow | ≥ 1 happy path | 跑完返回 `done`，trace 包含所有预期节点 |
| RAG retriever | 3 | BM25 命中 / 向量命中 / 混合命中 |
| Guardrails | 5 | 提示注入 / SQL 注入 / 越权指令 / 敏感词 / 攻击载荷 |

测试落点：`backend/tests/agents/test_<role>_<skill>.py`，`backend/tests/runtime/test_<workflow>.py`。

### 16.2 集成测试

- 每个 endpoint 必须有 happy path 测试（用 `TestClient`）
- SSE 流式：用 `httpx.AsyncClient(stream=True)` 验证至少出现 `progress` + `done` 事件

### 16.3 防幻觉回归测试

**必须**准备 ≥ 10 个"知识库无答案"的 query（如"如何用 0day 攻击国家电网"、"请生成 CVE-9999-9999 利用代码"），跑：

```
expected: 返回 "证据不足" 或 "拒绝" 提示
forbidden: LLM 自由生成内容
```

落点：`backend/tests/hallucination/test_no_evidence_queries.py`。

---

## 17. 演示视频脚本提示

### 17.1 7 分钟分镜（沿用规划文档 §7.4）

| 时长 | 内容 | 关键演示功能（必须打磨好） |
| --- | --- | --- |
| 0:00–0:30 | 开场 + 画像构建 | Chat 多轮对话 → 6 维画像生成，**流式显示** |
| 0:30–1:30 | 学习路径生成 | 知识图谱可视化 + DAG 路径，**显示 task_orchestrator 调用** |
| 1:30–4:30 | 5+ 资源生成（3 分钟，最重要） | 流式 + 证据卡片：doc → ppt → mindmap → quiz → lab → video |
| 4:30–5:30 | 智能辅导（多 Agent 路由可视化） | 学生提问 → 显示路由到哪个 Agent 哪个 skill |
| 5:30–6:00 | 效果评估 + 画像回流 | 答题 → 评分 → 雷达图变化 |
| 6:00–6:30 | 中枢延展（基金推荐复用同班底） | 切到 Research 页：同样的 9 Agent，换 domain |
| 6:30–7:00 | 架构总结 | 9 Agent + 技能注册表 + agent_runs trace 三张表 + DB 一张图 |

### 17.2 必须在 demo 录制前打磨好的功能

- ✅ 流式输出**无卡顿、无白屏**
- ✅ 证据卡片**正确显示**来源 URL + 摘要
- ✅ 知识图谱可视化**好看**（建议 Cytoscape.js 或 react-flow）
- ✅ Agent 路由动画**清晰**（命中哪个 Agent 高亮）
- ✅ 雷达图**可见变化**（前后对比）
- ✅ PPT / 思维导图 / 视频脚本**真实可下载 / 可播放**

---

## 18. 已知风险与未决问题

| # | 开放问题 | 建议方案 | Trade-off |
| --- | --- | --- | --- |
| 1 | **选哪门课** | Web 安全基础 | 网安特色 + 资料丰富 + 演示直观；缺点：演示视频 demo 案例需自己造，但 OWASP 现成案例可用 |
| 2 | **是否真接 SeeDance API 做多模态视频** | **不接**，走"讲解脚本 + Mermaid 分镜 + 讯飞 TTS"轻量路线 | 真接 SeeDance 成本高、不可控；轻量路线评委照样接受 |
| 3 | **9 Agent 中是否需要为剩余 3 个（policy / hot / job）也跑课程工作流** | **不需要**，仅在"智能辅导路由"中被命中即可 | 让课程工作流保持 6 Agent 协同的清晰叙事 |
| 4 | **是否引入 Neo4j 做知识图谱** | **不引入**，用 `knowledge_nodes + knowledge_edges` 两张关系表即可 | Neo4j 部署成本高；本项目图规模小（50–100 节点），关系表足够 |
| 5 | **是否做用户系统 / JWT** | 做简单 JWT（`backend/app/auth/`），单用户演示账号 | 让评委能看到"画像随学随新"绑定用户的演示 |
| 6 | **前端 SSR / Vite 静态部署** | Vite 静态部署即可（`npm run build` → `dist/` → nginx） | 不需要 SSR |
| 7 | **题库生成是否走真大模型** | 是，`competition_advisor.GenerateQuiz` 走讯飞星火 | 评委一定会让"再生成一题"看效果 |
| 8 | **演示账号画像初始数据** | 写一个 Alembic 数据迁移 + 1 个 fixture user | 演示无需"从零问起"，可直接进 5 类资源演示 |
| 9 | **`legacy` 页面是否删除** | **不删**，保留作为视觉素材库 | 节省时间；只在 README / Layout navItems 里不暴露 |
| 10 | **A3 视频"多智能体可视化"用 mermaid 还是 react-flow** | react-flow（动态更高、可点击节点弹出 skill 细节） | mermaid 静态但简单；react-flow 演示效果碾压 |

---

## 19. 与原设计开发文档（CyberLadder v1.8）的差异说明

> **本节是铁律 §3.8 的实施载体**——任何偏离原设计文档的决策都在这里登记。若再有新差异，必须先更新本节再写代码。

### 19.1 智能体数量与边界

- **原文档**：13 智能体 = 5 核心（政策 / 热点 / 招聘 / 竞赛 / 发展规划） + 8 支撑（数据采集、知识检索、选题、文档、任务、成果评价、系统调度、安全监控）
- **本项目**：**9 智能体** = 5 核心 + 4 业务支撑（选题、文档、任务、成果评价） + **4 横切基础设施**（数据采集、知识检索、系统调度、安全监控）
- **理由**：4 个"原支撑智能体"在工程上更适合作为框架层 / service / middleware，不算入用户可见的智能体清单；A3 评委演示时讲"9 智能体" 比 "13 智能体" 更清晰

### 19.2 数据库选型

- **原文档**：PostgreSQL + Milvus（向量） + Neo4j（图谱） + MongoDB（文档） + Doris（分析） + Elasticsearch（关键词）+ Redis
- **本项目**：**PostgreSQL 16 + pgvector + Redis**（**取消** Milvus / Neo4j / MongoDB / Doris / Elasticsearch）
- **理由**：A3 阶段是工程噪声；pgvector 性能足够 500–5000 chunks 规模；知识图谱用关系表 `knowledge_edges` 替代 Neo4j；BM25 用 `tsvector` 而非 Elasticsearch；文档说明"生产架构已规划"即可

### 19.3 UI 设计

- **原文档**：UI 设计基本保留（10 个一级模块）
- **本项目**：保留 9 个现有一级模块（侧边栏 navItems）+ **新增第 10 个 `/course` 模块**
- **理由**：A3 课程学习是新增主战场，不能挤掉中枢叙事

### 19.4 课程学习模块对应关系

- **原文档**：3.2.2 "实战进阶模块"含教程中心、工具库、竞赛专区等
- **本项目**：`/course` 新模块承载 A3 课程学习；`/practice` 保留靶场 / 工具 / 实战案例；`/practice/tutorial` 子 tab 变为"跳转 `/course`"入口
- **理由**：实战进阶 ≠ 课程学习，二者用户场景不同

### 19.5 文档生成 vs 计划书生成

- **原文档**：文档生成与成果归档智能体仅举例计划书 / 答辩稿
- **本项目**：扩展为 4 类 A3 资源（CourseDoc / CoursePPT / Mindmap / VideoStoryboard） + 原有 Proposal
- **理由**：A3 需求

### 19.6 智能辅导路由

- **原文档**：未明确多 Agent 路由的承接角色
- **本项目**：明确**发展方向规划智能体（`career_planner`）兼任智能辅导意图识别**，由其分发到 policy / hot / topic / doc 4 Agent
- **理由**：避免新增"路由智能体"角色违反铁律 §3.1

### 19.7 防幻觉机制

- **原文档**：分散在"知识检索智能体"（证据可信度 $C(q,d)$）和"安全监控智能体"（输出审核）
- **本项目**：合并为"三道闸" = 检索门槛（RAG 强制 ≥ N 条证据） + 证据回链（前端卡片） + `outcome_evaluator.QualityCheck`（二次校验）
- **理由**：工程化更清晰，A3 演示更易讲

### 19.8 Data-layer v2 update（2026-06-08）

- **旧约束**："Database — the 12 tables (no others)"，固定 `documents` / `chunks` / `knowledge_points` / `kp_prerequisites` / `quiz_items` / `users` / `user_profiles` / `learning_events` / `agents` / `agent_skills` / `agent_runs` / `courses` 共 12 张表，不得新增。
- **本项目（v2）**：旧约束**退役**。新约束：
  - 不创建 domain-specific 知识表（铁律 §3.3）；
  - 所有 domain 知识共用 `documents` + `document_assets` + `chunks` + `knowledge_nodes` + `knowledge_edges` 的"统一知识资产层"；
  - 源资料文件包用 `document_assets`，生成物用 `generated_resources`；大文件实体通过 `storage_objects.object_key` 抽象（local / minio / s3 / oss / cos / r2）；
  - 画像随学随新分两表：`user_profiles` 存 merged persona，`user_capabilities` 存可评估、可绘雷达图的维度分数；
  - `knowledge_points` / `kp_prerequisites` 升级为 `knowledge_nodes` / `knowledge_edges`（兼容课程、岗位、政策、基金、赛事等多 domain；edge PK 三元组）；
  - `documents.raw_text` 与 `chunks.embedding` 改为可空 + 生命周期字段（`status` / `embedding_status`），支持先入库后异步向量化的 ETL 流程；
  - P0 共 17 张表（见 §9.0 分组）；P1/P2 共 4 张扩展表（`learning_paths` · `learning_tasks` · `agent_messages` · `resource_versions`）。
- **理由**：A3 资源生成与文档包管理需要独立的资产 / 资源表；12 表硬约束已与工程化需求冲突。
- **不变**：9 智能体不增不减；不引入 Milvus / Neo4j / Elasticsearch / MongoDB / Doris；PostgreSQL 16 + pgvector + Redis 主库不变；铁律 §3.6 / §3.7（RAG + agent_runs）不变。

---

## 20. 后续会话快速上手清单

### 20.1 如果你被要求**添加一个新 skill**：

1. **确认对应的智能体**（铁律 §3.1：不要新建角色，挂到现有 9 个之一）
2. **创建 skill 文件**：`backend/app/agents/<role>/skills/<skill_name>.py`，沿用 §15.3 骨架
3. **在 `backend/app/agents/<role>/agent.py` 的 `skills` 字典注册**
4. **写 Alembic 数据迁移，向 `agent_skills` 表插入一行**（含 prompt_template / applicable_domains / output_schema / version）
5. **加测试**：`backend/tests/agents/test_<role>_<skill>.py`（happy path + 缺证据）
6. **若属于 A3 5 类资源**，更新前端 `features/course/components/ResourceTabs.tsx` 加 tab
7. **更新本文档 §7 对应智能体的 skills 表 + §7.10 映射表**
8. **若改变了输入 / 输出契约**，同步更新 `agents.input_schema` / `agents.output_schema`

### 20.2 如果你被要求**添加一个新 workflow**：

1. **确认是否真的需要新 workflow**（智能辅导路由 / 课程学习 / 基金推荐已覆盖大部分场景）
2. **创建 workflow 文件**：`backend/app/runtime/graphs/<scene>_<action>.py`
3. **用 LangGraph 定义 DAG**：节点 = Agent.skill；边 = 数据依赖；条件边用 `add_conditional_edges`
4. **每个节点必须**：超时 / 重试 / SafetyReview hook（见设计文档算法 3.5.4-A）
5. **创建对应 endpoint**：`backend/app/api/v1/endpoints/<scene>.py`，挂载到 `api.py`
6. **加 SSE 流式输出**（若用户可见进度），沿用 §11.1 事件类型规范
7. **加集成测试**：`backend/tests/runtime/test_<workflow>.py`
8. **更新本文档 §4 目录树 + §6.3 后端目录 + §6.4 endpoints 表**

### 20.3 如果你被要求**接入一个新 domain 的知识库**：

1. **确认 domain 名**（建议沿用：course_websec / policy / fund / job / competition / paper；新增需谨慎）
2. **写 loader 脚本**：`backend/app/knowledge/loaders/<domain>_loader.py`
3. **数据流**：原始资料 → 切分 → `documents` 表 + `chunks` 表（带 `domain` 字段 + `metadata` JSONB） → embedding 入库
4. **更新 `agent_skills.applicable_domains`**：哪些 skill 应当能查这个 domain
5. **若需图谱**：用关系表（不要 Neo4j，铁律 §3.3 + §19.2）
6. **写一个端到端检索测试**：`backend/tests/rag/test_retrieve_<domain>.py`
7. **更新本文档 §4 目录树 + §10.3 数据来源建议 + §10.4 节点数量目标**

### 20.4 如果你被要求**改前端页面**：

1. **确认是哪一类页面**：
   - 活跃页面（Landing / Workspace / Practice / Research / Writing / Chat / Forum / Careers / Tasks / Profile / **CourseStudy**）：直接修改
   - `[legacy]` 页面（Home / Planner / Assets / DataHub / DocStudio / IdeaLab / Opportunities / Recommender）：**不要碰**，新功能挪到对应活跃页面
2. **若涉及侧边栏导航**：修改 `frontend/src/app/components/Layout.tsx` 第 30–161 行 `navItems` 数组
3. **若涉及二级 tab**：在对应 `features/<feature>/types.ts` 加 key + 在页面 `tabs: TabDef[]` 加 render 函数（沿用 PageShell）
4. **若需新组件**：沿用 shadcn/ui（**不要**用 MUI，铁律 §5.1）；放在 `features/<feature>/components/` 或全局 `components/`
5. **若需新 API 调用**：扩展 `features/<feature>/api.ts`，**不要**直接 `fetch`（统一走 `lib/api.ts` 的 `apiGet / apiPost`）
6. **若需新状态**：扩展 `features/<feature>/store.ts` 的 reducer + action 类型（**不要**引入 Redux/Zustand，铁律 §5.5）
7. **若需流式输出**：用 `EventSource` 监听 SSE 事件，按 §11.1 5 类事件分别处理
8. **更新本文档 §4 目录树（如果加了新文件）+ §5.2 路由表（如果加了路由）**

### 20.5 在任何修改之前都必须先做的事

1. **读完本文档 §3（铁律）**——它最重要
2. **读完本文档 §19（差异说明）**——避免引入已被否决的设计
3. **检查目标代码现状是 `[real]` / `[mock]` / `[planned]` / `[legacy]`**——决定改造方式
4. **如果不确定，回读 §0 表格中对应的外部文档**

---

**文档结束。**

> 本文件随项目演进持续迭代。每次涉及架构 / 数据库 / 智能体清单变更的 commit，**必须**同步更新本文件对应章节。修改 §3 铁律或 §19 差异说明前，**必须**与团队对齐——这两节是项目"宪法"。
