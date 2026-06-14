# SecureHub Pre-Fork Checklist

> 三人并行开发分工**正式启动前**必须打勾的清单。
>
> 状态约定：
> - `[CODEX]` —— 已包含在喂给 Codex 的"Day 0 阻塞门解锁包"提示词中；Codex 跑完后逐项核对
> - `[TEAM]`  —— 需团队 / 项目负责人决策或线下交付；Codex 不会做
> - `[CODEX+TEAM]` —— Codex 出骨架，团队补真实凭证 / 真实账号 / 法律审核
>
> 验收规则：每一项必须有"完成定义（DoD）" + "验证方式"，光打勾不算。

---

## A. Day 0 阻塞门（不完成不能 fork 任务）

### A1. `docs/api/course-contract.md` 冻结版  `[CODEX]`
- **主责**：成员 A 起草 → 全员评审
- **DoD**：覆盖 11 个 endpoint + 7 种 SSE 事件 + 7 个公共 DTO；字段与 `backend/app/schemas/*.py` 1:1 对齐
- **验证**：`grep -E "EvidenceChunkDTO\|LearningPathNodeDTO\|GeneratedResourceDTO" docs/api/course-contract.md` 命中；改契约自动触发 PR 双签（A6）
- **截止**：Day 0 18:00

### A2. `.github/CODEOWNERS` 落库  `[CODEX+TEAM]`
- **主责**：项目负责人补 @member-X 真实 GitHub 账号
- **DoD**：按 AGENTS.md §10A.2 草案逐行落地；高风险文件 2 签；GitHub Settings → Require code owner review 已勾
- **验证**：随便提一个改 `backend/app/db/models/` 的 PR，GitHub 自动要求 A + C 两人 review
- **截止**：Day 0 18:00（Codex 出文件） + Day 1 09:00（项目负责人补账号）

### A3. `runtime/harness/` 骨架 + 1 mock skill + 1 pytest  `[CODEX]`
- **主责**：成员 A
- **DoD**：
  - `SkillContract` / `HarnessContext` / `BaseSkill` / `Harness.run()` 接口冻结
  - `_examples/echo_skill.py` 可跑通 happy path
  - `test_skill_harness.py` 含**关键断言**：`InsufficientEvidence` 时 `llm.chat` 调用次数 == 0（防幻觉红线）
- **验证**：`uv run pytest backend/tests/runtime/test_skill_harness.py -v` 两用例全绿
- **截止**：Day 0 18:00

### A4. `docs/demo/storyboard-v0.md` 故事冻结  `[CODEX]`
- **主责**：成员 C 维护，全员评审
- **DoD**：5 幕 + 时间轴 + endpoint + SSE 期望 + 落库期望 + 验收阈值 + 失败兜底
- **验证**：所有 endpoint 必须在 A1 contract 出现；所有 seed 必须在 B9 出现（grep 双向验证）
- **截止**：Day 0 18:00

### A5. `backend/.env.example` 升级 + `docs/env-and-credentials.md`  `[CODEX+TEAM]`
- **主责**：Codex 出占位 → 项目负责人补真实凭证（**不入 git**）
- **DoD**：覆盖 LLM / Embedding / DB / Redis / Storage / MinerU / Harness / Crawling / App 9 大类
- **必决策**：
  - 讯飞星火 KEY 是个人号还是公司号？共享额度多少？  `[TEAM]`
  - DeepSeek / Qwen fallback 是否启用？谁的 KEY？  `[TEAM]`
  - MinerU 选 API / 本地 / 手动？（**直接决定知识库 P0 路线**）  `[TEAM]`
  - 共享凭证用 1Password / Bitwarden / 飞书密码本 哪个？  `[TEAM]`
- **验证**：`.env.example` 不含真实 secret；`docs/env-and-credentials.md` 表格行数 = `.env.example` 字段数
- **截止**：Day 0 18:00（文件） + Day 1 12:00（凭证就绪）

### A6. PR / Issue 模板 + `docs/governance/high-risk-files.md`  `[CODEX]`
- **主责**：成员 C
- **DoD**：
  - PR 模板含 6 条铁律 checkbox（未新增 agent / 未新增 domain 表 / rag.retrieve / agent_runs / Status 注释 / 改 schema 同步 CLAUDE+AGENTS）
  - Issue 模板分 bug / feature / decision 三类
  - 高风险文件清单 7 行（models / migrations / lib/api.ts / lib/sse.ts / CLAUDE.md / AGENTS.md / course-contract.md）
- **验证**：开一个空 PR，自动加载模板；自动要求 code owner
- **截止**：Day 0 18:00

---

## B. Day 0–1 加速项（让 A/B/C 当天就能 mock 开发）

### B7. `backend/app/schemas/*.py` 顶层契约  `[CODEX]`
- **主责**：成员 A
- **DoD**：6 个文件（agent / resource / evidence / course / profile / rag），字段与 A1 1:1
- **关键不变量**：`EvidenceChunkDTO` 必填字段 == `{chunk_id, document_id, excerpt}` —— 其余可选但必须在 `model_fields` 里
- **验证**：`uv run pytest backend/tests/schemas/test_contract_alignment.py -v`
- **截止**：Day 0 22:00

### B8. `frontend/src/lib/sse.ts` + `sse.types.ts`  `[CODEX]`
- **主责**：成员 B
- **DoD**：7 种事件 union 类型；`openSSE(url, opts)` + `useSSE(url, opts)` hook；不引入新依赖
- **验证**：`pnpm typecheck` 通过；B 在没有真后端时可手写 mock event stream
- **截止**：Day 1 09:00

### B9. `backend/app/db/seeds/seed_smoke.py`  `[CODEX]`
- **主责**：成员 C
- **DoD**：1 user + 1 course + 3 nodes + 3 edges + 1 doc + 10 chunks + 9 agents + 5 skills + 1 profile + 6 capabilities；**幂等**
- **验证**：`uv run python scripts/seed_smoke.py` 跑 2 次不报唯一键冲突；`uv run pytest backend/tests/db/test_seed_smoke.py` 绿
- **截止**：Day 1 12:00

### B10. `Workout/session_log.md` 模板  `[CODEX]`
- **主责**：全员
- **DoD**：每日 6 字段（完成 / 阻塞 / 明日 / 改契约？ / 需 review？ / 影响 demo？）；Day 0 当天首条由"系统"写入
- **验证**：Day 1 起每天 18:00 三人各补一段
- **截止**：Day 0 23:00

---

## C. 第一周可并行启动但越早完成越好

### C11. `docs/compliance.md` 法律 / 合规清单  `[TEAM]`
- **主责**：成员 C 起草 → 项目负责人审
- **DoD**：≤ 1 页；按 platform 列出 robots / TOS 摘要 + license + `rights_note` 模板；MediaCrawler / MindSpider 学习研究免责声明；EvidenceDrawer 来源展示规则
- **为什么必做**：评委 / 教师问"你们爬 B 站合不合规"时的兜底材料
- **验证**：每个采集源在 AGENTS.md §10.5.7 平台覆盖表中都能查到对应条目
- **截止**：Week 1 Day 3

### C12. `docs/demo/storyboard.md` v1（v0 是 A4 故事冻结，v1 是 7 分钟分镜落到具体镜头）  `[TEAM]`
- **主责**：成员 C
- **DoD**：每 30 秒一个镜头；标注前端 URL / 后端 endpoint / 期望 SSE 事件序列 / 期望 evidence chunk_id；与 A4 storyboard-v0.md 引用一致
- **验证**：能照着脚本走完一遍 demo 不卡壳
- **截止**：Week 3 Day 5

### C13. `.github/workflows/ci.yml` 最小绿线  `[TEAM]`
- **主责**：成员 C
- **DoD**：3 个 job —— backend `uv run pytest --collect-only -q` / frontend `pnpm typecheck` / `docker compose config`；任一红即阻 PR
- **不做的事**：暂不接 e2e / lint / coverage，避免一开始过严
- **截止**：Week 1 Day 5

### C14. `docs/llm-fallback.md` 模型降级决策  `[TEAM]`
- **主责**：成员 A
- **DoD**：明确"讯飞星火限流 / 502 / 内容拒答"三种情况各自降级到哪里；mock_mode 触发条件；降级层在 `llm/` 还是 `runtime/harness/`
- **为什么必做**：演示日讯飞限流时不能现场开会
- **截止**：Week 1 Day 5

---

## D. 一开始就该确认的"小坑"

### D15. `backend/app/db/models/_enums.py` 枚举 SSOT  `[TEAM]`
- **主责**：成员 A + C 共同
- **DoD**：把分散在 schema / AGENTS §9 / A3 §5.2 的 `node_type` / `edge_type` / `asset_type` / `resource_type` / `source_type` 枚举值汇总成单一 Python 常量；现有 model 引用它
- **风险**：不做的话 C 写 seed 用 `markdown_chapter`、A 写代码用 `markdown_section`、B 前端用 `chapter_md` —— 全错位
- **验证**：grep 全仓库无字符串字面量出现在 ResourceType / AssetType 上下文
- **截止**：Day 1 12:00

### D16. Embedding 维度统一  `[TEAM]`
- **主责**：成员 A
- **DoD**：P0 用 BGE-M3 / bge-large-zh / 讯飞 之一；`VECTOR(N)` 中 N 与模型维度一致并写进 `.env.example` 的 `EMBEDDING_DIM`
- **风险**：换 embedding 模型 = migration + 重建 HNSW 索引 = 整个 chunks 表重新向量化（演示前一周不能干）
- **验证**：seed_smoke 跑完后 `chunks.embedding_status='pending'`；异步向量化任务跑完所有维度匹配
- **截止**：Day 1 12:00

### D17. `storage_objects.provider=local` 目录约定  `[CODEX+TEAM]`
- **主责**：成员 A + C
- **DoD**：`data/storage/<bucket>/<object_key>` 落地；`data/raw/` / `data/processed/` / `data/storage/` 三类目录区分；全部进 `.gitignore`；`data/seed/` 例外（小文本资料随仓库走）
- **截止**：Day 1 12:00

### D18. "证据不足态"前端设计  `[TEAM]`
- **主责**：成员 B
- **DoD**：`InsufficientEvidence` 返回时前端展示什么 —— 静态图 + 文案 + "试试换问法"按钮；不要让评委看到红色 500 错误
- **验证**：手动触发一次"知识库无答案"query，UI 正常展示
- **截止**：Week 1 Day 4

### D19. 资料合规分级与 git 策略  `[TEAM]`
- **主责**：成员 C
- **DoD**：
  - 公共许可证（OWASP CC BY-SA / GitHub MIT）资料 → `data/seed/`，随 git 提交
  - 版权不明 → 只入 `documents.metadata` + `chunks.metadata.excerpt` 摘要 + URL，**不**入完整正文
  - 教材 / 付费内容 → 仅个人本地 `data/raw/private/`（gitignore）
- **风险**：法律红线
- **截止**：Day 1 18:00

### D20. MinerU 路线选型  `[TEAM]`
- **主责**：成员 C + 项目负责人
- **DoD**：API / 本地 / 手动兜底三选一；写进 `MINERU_MODE`；如选本地，确认 Python ≥ 3.10 + GPU/CPU 模型权重下载完毕
- **截止**：Day 0 18:00（决策） + Day 1 18:00（环境就绪）

---

## Day 0 → Day 1 时间线（建议）

| 时间 | 谁 | 动作 |
|---|---|---|
| Day 0 09:00 | 项目负责人 | 把"Day 0 阻塞门解锁包"提示词喂给 Codex |
| Day 0 12:00 | Codex | 应交付 A1–A6（提交报告） |
| Day 0 14:00 | 三人 | 评审 A1 contract，签字冻结 |
| Day 0 18:00 | Codex | 应交付 B7–B10（提交报告） |
| Day 0 18:00 | 项目负责人 | 完成 A5 / A2 / D20 三项 `[TEAM]` 决策（讯飞 KEY / GitHub 账号 / MinerU 选型） |
| Day 0 23:00 | 全员 | 在 `Workout/session_log.md` 写下 Day 0 总结 |
| Day 1 09:00 | A / B / C | 各自 checkout `feature/backend-agent-harness-workflow` / `feature/frontend-course-showcase` / `feature/knowledge-seed-quality`，正式开工 |
| Day 1 12:00 | A + C | 完成 D15 / D16 / D17 三项枚举 / 维度 / 目录约定 |
| Day 1 18:00 | 全员 | 第一次 15 分钟 stand-up |

---

## 进度对账（项目负责人填）

| 类别 | 总数 | 已完成 | 责任人 |
|---|---|---|---|
| A. Day 0 阻塞门 | 6 | _ / 6 | Codex |
| B. Day 0–1 加速项 | 4 | _ / 4 | Codex |
| C. 第一周可并行 | 4 | _ / 4 | 团队 |
| D. 小坑 | 6 | _ / 6 | 团队 |
| **合计** | **20** | **_ / 20** | — |

---

*Last updated: 2026-06-09。本清单与 `.codex/AGENTS.md §10A`、`Plan/SecureHub_三人并行开发分工方案.md` 保持一致。若任一文档更新，必须同步本清单。*
