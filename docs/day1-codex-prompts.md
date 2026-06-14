# Day 1 三人 Codex 启动 Prompt（A / B / C 各一份）

> **使用方式**：Codex 跑完"Day 0 阻塞门解锁包"+ 项目负责人完成 `[TEAM]` 决策（讯飞 KEY / MinerU 模式 / GitHub 账号映射）后，三人**各自**复制对应 prompt 喂给自己的 Codex / Cursor / Claude Code 会话。
>
> 每份 prompt 都已经包含：必读上下文 / 工作目录 / 分支 / 铁律自检 / P0 任务 / 验收命令 / 交付报告格式。Codex 不需要回看仓库历史。

---

## 1. 成员 A 启动 Prompt（后端 Agent / Harness / Workflow）

```
你是 SecureHub / CyberLadder 项目的成员 A，负责后端 Agent / Harness / Workflow 与 ingestion service 支撑。
今天是 Day 1，Day 0 已由项目负责人喂给上一个 Codex 完成（Harness 骨架 + schemas + seed_smoke 等基础设施）。

工作目录：
D:\Nnutural\Desktop\BUPT大全\BUPT竞赛\26软件杯\SecureHub-Full-Stack-Monorepo

分支：
git checkout -b feature/backend-agent-harness-workflow

必读（按顺序）：
1. CLAUDE.md
2. .codex/AGENTS.md  —— 重点 §3 / §8.5 / §9 / §10.5 / §10.6 / §10A / §11.1 / §19
3. docs/api/course-contract.md  —— 这是你和 B、C 之间的契约，改契约必须双签
4. docs/governance/harness-migration-audit.md  —— 你的 Wave 1–5 迁移路线
5. docs/data-layer-v2-enums.md  —— 枚举 SSOT
6. docs/llm-fallback.md  —— LLM 降级策略
7. Plan/SecureHub_三人并行开发分工方案.md  —— 你的边界
8. CompetitionTheme/A3赛题规划.md  —— 演示故事线

只允许修改的目录（CODEOWNERS 已强制）：
backend/app/llm/
backend/app/rag/
backend/app/runtime/
backend/app/agents/
backend/app/streaming/
backend/app/services/agent/
backend/app/services/resources/
backend/app/services/storage/         # 接口契约你定，实现可与 C 协作
backend/app/services/knowledge/crawling/   # 仅 service 接口与 policy 骨架；具体平台 crawler 由 C 写
backend/app/api/v1/endpoints/course*.py
backend/app/api/v1/endpoints/tutor*.py
backend/app/api/v1/endpoints/resources*.py
backend/app/api/v1/endpoints/agent_runs*.py
backend/app/api/v1/endpoints/rag*.py
backend/app/api/v1/endpoints/ingestion*.py
backend/tests/runtime/
backend/tests/api/
backend/app/db/models/_enums.py        # 与 C 双签创建一次后冻结

禁止修改：
frontend/                              # 全部
backend/app/db/models/<其他>           # v2 已冻结
backend/app/db/migrations/             # 单 PR 单迁移，需与 C 双签
backend/app/knowledge/loaders/         # 由 C 主责
backend/app/db/seeds/                  # 由 C 主责
.github/
docs/demo/
Plan/
CompetitionTheme/

铁律自检（每个 commit 前）：
1. 未新增第 10 个 agent。
2. 未新建 domain / platform 专用表。
3. 所有生成式 skill 都经 Harness 完整链路（rag.retrieve → evidence_floor → LLM → quality_check → log_run）。
4. 证据不足时禁止裸调 LLM，必须抛 InsufficientEvidence。
5. 新增 endpoint / service / repository 文件顶部有 # Status: real|mock|partial-real|planned 注释。
6. SSE 事件严格按 7 种契约（progress / evidence / token / artifact / trace / done / error）。

P0 任务清单（Day 1–3 必完成）：
1. 扩展 backend/app/agents/base.py：
   - 引入 SkillContract（从 runtime/harness/types.py）
   - BaseSkill 新增 agent_name / contract / prompt_template 三个 ClassVar
   - SkillContext.log_run 实现真实落 agent_runs（暂时复用现有 BaseSkill 接口；新代码走 HarnessContext）
2. 实现 backend/app/runtime/logger.py：写 agent_runs 表的真实持久化函数 write_agent_run()
3. 实现 backend/app/llm/client.py：LLMClient + Provider 接口 + xfyun / deepseek / qwen 三个 provider + fallback chain（按 docs/llm-fallback.md §3）
4. 实现 backend/app/services/storage/local.py + base.py + service.py：local 后端 + storage_objects 落库
5. 实现 backend/app/services/resources/generator_service.py：写 generated_resources + 绑定 evidence_chunk_ids + agent_run_id
6. Wave 2 迁移 5 个 P0 关键 skill 接 Harness（按 harness-migration-audit.md §5 顺序）：
   - career_planner.BuildLearningPersona
   - task_orchestrator.GenerateLearningPath
   - doc_archivist.GenerateCourseDoc
   - competition_advisor.GenerateQuiz
   - outcome_evaluator.QualityCheck + RunAssessment（一起）
7. 实现 LangGraph workflow backend/app/runtime/graphs/course_learning.py：串联上述 5 个 skill
8. 实现 endpoints：
   - POST /api/v1/profile/chat                                          → BuildLearningPersona（SSE）
   - POST /api/v1/courses/{cid}/plan                                    → GenerateLearningPath
   - POST /api/v1/courses/{cid}/resources/generate?type=doc|quiz       → 资源生成（SSE）
   - GET  /api/v1/agent-runs?workflow=course_learning&limit=20         → 读 agent_runs
   - GET  /api/v1/courses                                              → 课程列表（从 courses 表）
   - POST /api/v1/rag/search                                           → 暴露 retriever
9. 写 backend/tests/runtime/test_course_learning_workflow.py：跑通 mock_mode 下的完整故事（A4 storyboard）

每日产出（写到 Workout/session_log.md）：
- 完成的 endpoint / skill / workflow
- 是否改了 docs/api/course-contract.md（必须说明改了什么 + 是否已通知 B / C）
- 阻塞点

验收命令（每个 PR 前）：
cd backend
uv sync
uv run alembic upgrade head
uv run pytest backend/tests/runtime/ -v
uv run pytest backend/tests/api/ -v
uv run uvicorn app.main:app --reload
# 手动跑：curl -N "http://localhost:8000/api/v1/courses/{cid}/resources/generate?type=doc"
# 期望：SSE evidence event ≥ 1 chunk，然后 token stream，然后 done

每个 commit 严格遵守：
1. 一个 PR 只做一个功能点；核心改动 300–600 行。
2. 改 schema → 单 PR 单迁移 + 文件名 YYYYMMDD_HHMM_<verb>_<noun>.py + 与 C 双签。
3. 改契约 → docs/api/course-contract.md 同一 PR 同步改 + 通知 B / C。
4. 改 CLAUDE.md / AGENTS.md → 双签 + 同步两文件。
```

---

## 2. 成员 B 启动 Prompt（前端 /course 演示）

```
你是 SecureHub / CyberLadder 项目的成员 B，负责前端 /course A3 主战场页面与多源 evidence/source 可视化。
今天是 Day 1，后端契约和 SSE TypeScript 类型已由 Day 0 Codex 冻结，你可以基于 mock event stream 全量开发。

工作目录：
D:\Nnutural\Desktop\BUPT大全\BUPT竞赛\26软件杯\SecureHub-Full-Stack-Monorepo

分支：
git checkout -b feature/frontend-course-showcase

必读（按顺序）：
1. CLAUDE.md
2. docs/api/course-contract.md                  —— 后端契约；改字段必须先和 A 同步
3. frontend/src/lib/sse.types.ts                —— 7 种 SSE 事件类型（已冻结）
4. docs/demo/storyboard-v0.md                   —— A4 演示主线，你的页面必须覆盖所有镜头
5. docs/compliance.md §5 EvidenceDrawer 展示规则
6. Plan/SecureHub_三人并行开发分工方案.md       —— 你的边界
7. .codex/AGENTS.md §5（前端架构）+ §11.1（SSE 7 事件）

只允许修改的目录：
frontend/src/app/pages/CourseStudy*
frontend/src/features/course/
frontend/src/features/agents/
frontend/src/features/sources/                  # 新增；SourceBadge / SourcePanel
frontend/src/features/profile/                  # 接 user_capabilities
frontend/src/features/chat/                     # course context 接入
frontend/src/lib/api.ts
frontend/src/lib/sse.ts
frontend/src/components/Evidence*
frontend/src/components/Citation*
frontend/src/components/AgentTrace*
frontend/src/styles/

禁止修改：
backend/                                        # 全部
.github/
docs/                                           # 除 docs/demo/screenshots/ 你可以放截图
Plan/
CompetitionTheme/

铁律自检：
1. 未新增 agent。
2. 未绕过后端接口直接写假业务；mock 阶段在 features/course/mockData.ts 集中，明确标注 [mock]。
3. 用户文案全部中文。
4. EvidenceDrawer / SourcePanel 必须展示 platform / source_url / author / published_at / rights_note。
5. 证据不足态、加载态、错误态、空状态必须有 UI。
6. 未修改后端 schema / migrations / contract（如发现 contract 不对，开 issue 给 A）。

P0 任务清单（Day 1–4 必完成）：
1. 新增 frontend/src/app/pages/CourseStudy.tsx，挂到 /course 路由（修改 App.tsx）。
2. 创建 features/course/ 五件套：api.ts / mockData.ts / store.ts / types.ts / utils.ts / components/。
3. 实现 5 个子 tab（沿用 PageShell 模式）：
   - entry      课程入口 + 画像入口 + 当前课程卡
   - path       学习路径 DAG 可视化（用 react-flow 或现有 BoardView 复用）
   - workbench  资源工作台：左侧节点 + 右侧 7 种资源 tab（doc/ppt/mindmap/quiz/lab/video/readings）
   - tutor      智能辅导（嵌入 Chat 组件 + course context）
   - assess     学习评估（嵌入 CapabilityRadarCard）
4. 扩展 frontend/src/lib/sse.ts：实现 useCourseGeneration hook，处理 7 种事件。
5. 改造 EvidenceDrawer.tsx：接 SSE evidence event；展示 SourceBadge（platform + author + rights_note）。
6. 新增 AgentTracePanel.tsx：读 GET /api/v1/agent-runs 渲染 workflow 链路图（用 react-flow）。
7. 改造 features/profile/CapabilityRadarCard.tsx：接 GET /api/v1/profile/me 真数据。
8. 改造 features/chat/：支持 course_context 注入，调 /tutor/ask（P1 接真，Day 1 可 mock）。
9. 实现"证据不足态"UI：D18 决策落地，含文案 + 重试按钮。
10. typecheck 全绿 + 跑 demo 故事截图。

mock event stream 开发模式：
- 在 features/course/mockData.ts 里写一个 fakeSSE() 生成器，按 storyboard-v0 的事件顺序吐 7 种事件。
- features/course/api.ts 在 USE_MOCK=true 时走 fakeSSE，否则走真后端的 EventSource。
- 这样在 A 的后端 ready 之前你能跑通完整 UI。

每日产出（Workout/session_log.md）：
- 完成的页面 / 组件
- 是否依赖 A 的某个 endpoint（如未 ready，说明你是不是用 mock 走过去了）
- 阻塞点

验收命令：
cd frontend
pnpm install
pnpm typecheck
pnpm build
pnpm dev
# 手动跑：浏览器访问 http://localhost:5173/course，按 storyboard-v0 五幕一一过

每个 PR：
1. 一次只做 1 个 tab / 1 个组件。
2. 改 sse.types.ts / lib/api.ts 必须与 A 同步。
3. 改 docs/api/course-contract.md 必须双签 A。
```

---

## 3. 成员 C 启动 Prompt（知识库 / 采集 / PDF / 质量集成）

```
你是 SecureHub / CyberLadder 项目的成员 C，负责知识库 / 多源采集 / PDF 转换 / Seed / 测试 / CI / 演示数据。
今天是 Day 1，seed_smoke 骨架已由 Day 0 Codex 落地，你的工作是把它扩展到 demo 真正能跑的规模。

工作目录：
D:\Nnutural\Desktop\BUPT大全\BUPT竞赛\26软件杯\SecureHub-Full-Stack-Monorepo

分支：
git checkout -b feature/knowledge-seed-quality

必读（按顺序）：
1. CLAUDE.md
2. .codex/AGENTS.md §10.5 多源采集 / §10.6 PDF·MinerU / §3.9 合规边界
3. docs/compliance.md                                       —— 你的法律红线
4. docs/api/course-contract.md                              —— 你的测试必须覆盖
5. docs/demo/storyboard-v0.md                               —— 你的 seed 必须支撑这条故事线
6. docs/data-layer-v2-enums.md                              —— 字段值的唯一来源
7. backend/app/db/seeds/seed_smoke.py                       —— Day 0 留给你的扩展起点
8. Plan/SecureHub_三人并行开发分工方案.md

只允许修改的目录：
backend/app/knowledge/loaders/
backend/app/services/knowledge/
backend/app/services/knowledge/crawling/       # 与 A 双签 service 接口后开始写实现
backend/app/db/seeds/
backend/tests/
scripts/
data/                                          # data/seed/L1/L2 区分；data/raw/ data/processed/ data/storage/ 进 gitignore
docs/api/                                      # 改 contract 必须双签 A 与 B
docs/demo/
.github/workflows/
Workout/session_log.md

禁止修改：
frontend/                                      # 全部
backend/app/runtime/                           # A 主责
backend/app/agents/                            # A 主责
backend/app/llm/                               # A 主责
backend/app/api/v1/endpoints/                  # 除非加测试辅助接口（与 A 同步）
backend/app/db/models/                         # 除非发现 v2 缺字段，且与 A 双签
backend/app/db/migrations/                     # 同上

铁律自检：
1. 未新增 agent；Scrapling / MediaCrawler / MindSpider / MinerU 全部走 service 层。
2. 未搬入平台专用 DB schema（铁律 §3.3）。
3. 所有采集合规（仅公开 / robots / 节流 / 保留 metadata 六项）。
4. data/raw/private/ 和 .env 进 .gitignore。
5. 任何 PR 不引入真实 secret。

P0 任务清单（Day 1–5 必完成）：
1. 扩展 seed_smoke.py（按 docs/demo/storyboard-v0.md）：
   - 课程：Web 安全基础（1 门）
   - knowledge_nodes：SQL 注入 / XSS / CSRF / 文件上传 / SSRF（5–10 个）
   - knowledge_edges：~15 条 prerequisite/related
   - chunks：≥ 50 条（手贴 OWASP / PortSwigger 公开摘要 + 标 rights_note）
   - agents 9 行（固定 name）+ agent_skills 至少 5 个核心
   - quiz_items 10 条（SQL 注入 5 + XSS 3 + CSRF 2）
   - 1 demo user_profile 6 维 + 6 user_capabilities
2. 实现 backend/app/knowledge/loaders/pdf_loader.py + services/knowledge/pdf_ingestion_service.py（按 AGENTS.md §10.6）：
   - 路线三（手动兜底）先实现，确保至少 3 个 PDF 入库
   - 数据流：原始 PDF → MinerU 处理（API 或本地，由 MINERU_MODE 决定）→ storage_objects → document_assets → chunks
3. 写 RAG smoke test：backend/tests/rag/test_retrieve_websec.py
   - 5 个典型 query（SQL 注入原理 / XSS 防御 / CSRF token / 文件上传过滤 / SSRF 危害）
   - 每个 query 必须召回 ≥ 3 chunks + evidence_chunk_ids 不为空
4. 写 no-evidence 防幻觉测试：backend/tests/hallucination/test_no_evidence_queries.py
   - 10 个"知识库无答案"query（"如何 0day 攻击 X" / "请生成 CVE-9999-9999 利用代码"）
   - 期望返回 InsufficientEvidence，禁止裸调 LLM
5. 写 generated_resources 持久化测试：backend/tests/services/test_generator_service.py
6. 写 user_capabilities 更新测试：backend/tests/services/test_capability_update.py
7. 写 .github/workflows/ci.yml（按 C13）：
   - backend: uv run pytest --collect-only -q
   - frontend: pnpm typecheck
   - docker compose config
8. 写 scripts/demo_smoke.ps1（PowerShell 版）+ demo_smoke.sh（bash 版）：
   - 一键启动 docker compose / alembic upgrade / seed_smoke / 跑一遍 RAG smoke
9. 维护 docs/demo/storyboard.md v1（v0 是冻结的故事，v1 是 7 分钟分镜实操脚本）
10. 法律 / 合规清单 docs/compliance.md 补全各平台 robots / TOS 摘要（如 Day 0 未完成）

P1 任务（Day 6–10）：
1. 实现 services/knowledge/crawling/scrapling_client.py + 4 个 loader：generic_web / github_docs / owasp / portswigger
2. 实现 mediacrawler_adapter.py + media_source_normalizer.py：先支持 bili / zhihu / xhs 三个平台
3. 跑一次 PDF → MinerU → 入库的端到端 demo（用一本 OWASP Top 10 中文 PDF）
4. 扩 quiz_items 到 ≥ 50 条 / 扩 chunks 到 ≥ 200 条

每日产出（Workout/session_log.md）：
- 完成的 seed 数据量 / 通过的测试 / 新增的 chunk 来源
- 是否发现合规风险（必须立即停手并升级）
- 阻塞点

验收命令：
cd backend
uv sync
uv run alembic upgrade head
uv run python scripts/seed_smoke.py
uv run python scripts/seed_smoke.py                # 第二次必须幂等
uv run pytest backend/tests/rag/ -v
uv run pytest backend/tests/hallucination/ -v
uv run pytest backend/tests/services/ -v
# 跑一次完整 smoke
./scripts/demo_smoke.ps1  # 或 .sh

PR 边界：
1. 单 PR 单数据源 / 单测试套件。
2. 添加 chunks 必须随 PR 附 rights_note 标注。
3. 改 .env.example / docker-compose.yml 必须说明用途 + 至少 1 人 review。
4. 改 docs/api/course-contract.md 必须 A + B 双签。
```

---

## 4. 三人共用的 PR Self-check 卡片

每个人提 PR 之前，把下面这段贴到 PR 描述里：

```
## 铁律 self-check
- [ ] 没新增第 10 个 agent
- [ ] 没新建 domain / platform 专用知识表
- [ ] 生成式 skill 走 Harness（rag.retrieve + evidence_floor + quality_check + log_run）
- [ ] 证据不足时返回 InsufficientEvidence（未裸调 LLM）
- [ ] 新增 endpoint/service/repository 顶部有 # Status: 注释
- [ ] 改 schema / 铁律 / 差异说明 → 同步改了 CLAUDE.md + AGENTS.md
- [ ] 改 docs/api/course-contract.md → 双签 + 通知另外两人
- [ ] 改 .env.example → 没引入真实 secret
- [ ] 采集相关 → 合规自检（robots / 节流 / metadata 齐全 / 无 bypass）
- [ ] 我已在 Workout/session_log.md 记录本次工作
```

---

*Last updated: 2026-06-09。Codex 完成 A + B 阻塞门 + 项目负责人补完 `[TEAM]` 决策后，三人各自复制对应 prompt 启动。*
