# CLAUDE.md

> Operating manual for AI coding assistants (Claude Code / Codex / Cursor) working in this repo.
> Keep this file lean — under ~250 lines. Deep design lives in `.codex/AGENTS.md` and `../CompetitionTheme/A3赛题规划.md`.

---

## 1. Project at a glance

**SecureHub / CyberLadder (安枢智梯)** — a cybersecurity talent-cultivation hub powered by a 9-agent multi-agent system.

This single repo is presented to **two competitions in parallel** — do **not** fork:

| Competition | Narrative angle |
|---|---|
| 挑战杯 (Challenge Cup) | "网络安全人才培养中枢" — the full 9-module hub |
| 第十五届中国软件杯 A3 (iFLYTEK) | "基于大模型的个性化资源生成与学习多智能体系统" — the `/course` route is the showcase |

Same code, two stories. The `/course` module is the A3 showcase; the other 9 modules sell the "central-hub" extensibility story by reusing the **same 9 agents** on different RAG `domain`s.

---

## 2. Eight ironclad rules — break any and the work is rejected

1. **The 9 agents are fixed** — never add a 10th, never rename, never drop.
   `policy_interpreter` · `hot_analyst` · `job_analyst` · `competition_advisor` · `career_planner` · `topic_explorer` · `doc_archivist` · `task_orchestrator` · `outcome_evaluator`
   New A3 capabilities arrive as **new skills under existing agents**, not as new agents.
2. **Cross-cutting infra is not an agent.** `rag/`, `knowledge/loaders/`, `services/knowledge/crawling/`, `services/storage/`, `runtime/router.py`, `runtime/guardrails/`, `runtime/harness/` are middleware. Do not register them — or external tools like **Scrapling / MediaCrawler / MindSpider** — as a 10th agent (no `crawler_agent` / `media_agent` / `spider_agent`).
3. **One unified knowledge asset layer (data-layer v2) for every domain.** All domains share `documents` + `document_assets` + `chunks` + `knowledge_nodes` + `knowledge_edges`, filtered by `domain`. Never create `course_chunks` / `fund_chunks` / `policy_chunks` / `bilibili_chunks` / `zhihu_chunks` / platform_chunks parallel tables. Source assets (PDF · Markdown full/chapter · cover · page image · OCR text · video transcript) live in `document_assets` keyed by `object_key` against `storage_objects`. All **generated** resources (course doc · PPT · mindmap · quiz set · lab · video storyboard · reading list · assessment report) land in `generated_resources` + `storage_objects` — never in `documents`.
4. **Learner profile has one source of truth plus evaluable capability rows.** `user_profiles` stores the merged persona (JSONB `dimensions` + embedding); `user_capabilities` stores radar-chart dimensions and assessment-updatable scores. Feature modules must not create their own profile tables; updates flow through `outcome_evaluator.update_capability` → `user_capabilities` → `career_planner.update_persona` → `user_profiles`.
5. **Every new endpoint / service / repository file starts with a status comment**: `# Status: real` | `# Status: mock` | `# Status: partial-real` | `# Status: planned`. No exceptions.
6. **Generative skills must call `rag.retrieve()` before composing the prompt, then pass through `outcome_evaluator.quality_check`.** The Harness contract is: `validate input → rag.retrieve → evidence_floor check → LLM → parse → quality_check → write generated_resources/storage_objects → log_run`. Bypassing RAG or the quality gate kills the anti-hallucination story.
7. **Every skill ends with `await ctx.log_run(...)`** writing to `agent_runs`. The trace visualization depends on it. CI greps for this.
8. **Changes that touch §2 rules, §8 schema, collection strategy, the Harness contract, or §19 deltas in `.codex/AGENTS.md` must update both `CLAUDE.md` and `.codex/AGENTS.md` in the same change.** Code and constitution stay in sync.

### 2.1 Multi-source collection — compliance is non-negotiable

Three external tools, one normalization pipe — none is an agent.

- **Scrapling** (P0/P1): generic public web — OWASP, PortSwigger, GitHub README/Docs, official docs, technical blogs.
- **MediaCrawler** (P1, same tier as Scrapling): Chinese social platforms — 小红书 / 抖音 / 快手 / B站 / 微博 / 贴吧 / 知乎.
- **MindSpider** (P2 reference only): hot-topic discovery and sentiment flow as inspiration for `hot_analyst` demos. Not in P0 main path; **never** import its platform-specific DB schema.

All three feed `source_normalizer` → `storage_objects` → `documents` + `document_assets` → `chunks` → `knowledge_nodes/edges`. Every row must carry `platform / source_url / author / published_at / fetched_at / license / rights_note`. Hard bans (CI/PR review): no login bypass, no CAPTCHA bypass, no anti-bot/Cloudflare bypass, no proxy rotation for evasion, no large-scale concurrent scraping, no bulk re-hosting of copyrighted content.

---

## 3. Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI · Python 3.11+ · uv · Pydantic v2 · SQLAlchemy 2.0 async · Alembic |
| Frontend | React 18 · Vite 6 · TypeScript · Tailwind v4 · shadcn/ui · Radix · React Router v7 |
| Data | PostgreSQL 16 + **pgvector** · Redis 7 |
| LLM | **iFLYTEK Spark (讯飞星火) — A3 hard requirement** · DeepSeek / Qwen as fallback |
| Embedding | BGE-M3 / bge-large-zh / Spark embedding |
| Agent runtime | **LangGraph** (`StateGraph` + conditional edges) |
| Streaming | SSE — 7 event types: `progress` / `evidence` / `token` / `artifact` / `trace` / `done` / `error` |
| State mgmt (FE) | `useReducer` + `localStorage` per feature. **No Redux / Zustand.** |
| Path alias | `@/*` → `src/*`; custom `figma:asset/` Vite resolver |

Do **not** introduce: Milvus, Neo4j, MongoDB, Doris, Elasticsearch, MUI, Redux. They are competing choices we already ruled out.

---

## 4. Repo layout (top level)

```
backend/app/
  agents/          # 9 agent folders, each = agent.py + skills/*.py + tools.py
  runtime/         # router, capability_manifest, logger, guardrails/, graphs/, harness/ (skill executor)
  llm/             # xfyun.py · deepseek.py · embedding.py
  rag/             # chunker · retriever (BM25 + vector + RRF) · reranker · evidence_builder
  knowledge/loaders/   # per-domain loaders: course / policy / fund / pdf (MinerU) / generic_web / owasp / portswigger / media_platform ...
  services/
    knowledge/crawling/  # scrapling_client · mediacrawler_adapter · mindspider_adapter · source_normalizer · crawler_policy
    storage/             # storage_objects writer (local / minio / s3 abstraction)
    {agent,resources,knowledge,learning}/  # business orchestration; status: real|mock|partial-real|planned
  db/              # models/ grouped by {identity,knowledge,learning,agent,resource,storage}/ + migrations/ + seeds/
  repositories/    # grouped by {identity,knowledge,learning,agent,resource,storage}/  — DB read/write only
  streaming/       # SSE events + writer (progress / evidence / token / artifact / trace / done / error)
  api/v1/endpoints/  # FastAPI routes
frontend/src/app/
  pages/           # 10 top-level routes (CourseStudy is the 10th)
  features/        # course/ · profile/ · chat/ · agents/ · sources/ · research/ ... each self-contained
  components/      # Layout, EvidenceDrawer, CitationPanel, AgentTracePanel, SourceBadge ...
  lib/             # api.ts · sse.ts
.codex/
  AGENTS.md        # ← full constitution (everything in detail). Read on first session.
  context/         # Codex-specific session context
  workflows/       # Codex playbooks
../CompetitionTheme/A3赛题规划.md      # A3 task spec + capability→agent→skill mapping
../Chat/SecureHub_Data_Layer_V2_工程化改造任务书.md  # data-layer v2 source of truth
../Plan/SecureHub_三人并行开发分工方案.md            # 3-member parallel split + CODEOWNERS sketch
../Workout/                            # Long-form planning artefacts (FRAMEWORK_COMPLETION_PLAN, etc.)
```

---

## 5. Common commands

```bash
# Backend
cd backend
uv sync                                 # install deps
uv run uvicorn app.main:app --reload    # dev server
uv run alembic upgrade head             # apply migrations
uv run alembic revision -m "..."        # create a new migration
uv run pytest                           # tests
uv run pytest --collect-only -q         # smoke (must pass even when most tests skip)

# Frontend
cd frontend
pnpm install
pnpm dev                                # Vite dev
pnpm typecheck                          # tsc --noEmit
pnpm build

# Infra
docker compose up -d postgres redis     # boot only data services
docker compose config                   # validate compose file
```

A3 fast-path smoke (week 1 acceptance):
```bash
curl -N "http://localhost:8000/api/v1/courses/{cid}/resources/generate?type=doc"
# expect SSE: evidence event with ≥ 1 chunk, then token stream, then done
```

---

## 6. Coding conventions

- **Status comment is mandatory** on every endpoint/service/repository file (rule §2.5).
- **Imports**: backend uses absolute `from app.xxx import yyy`. Frontend uses `@/...` alias.
- **Async by default** on the backend — sync DB or HTTP calls are a smell.
- **Skill file shape** (see `.codex/AGENTS.md §15.3` for full skeleton):
  1. `PROMPT_TEMPLATE = """..."""` at module top
  2. `class XxxSkill(BaseSkill[InputModel, OutputModel])`
  3. `async def run()` does: `retrieve → compose prompt → call LLM → safety_review → ctx.log_run`
- **Components**: shadcn/ui first; if a primitive doesn't exist, build it on Radix, not from scratch.
- **No comments that restate the code.** Only document non-obvious *why* (workarounds, invariants, citations to A3 spec sections).
- **Never write English-only UI strings.** User-facing copy is Chinese; identifiers and code are English.

---

## 7. Anti-hallucination contract (A3 scoring depends on this)

Three gates, in order, for every generative skill:

1. **Evidence floor** — `rag.retrieve(...)` must return ≥ `MIN_EVIDENCE` (default 3) chunks. Below the floor, the skill returns `InsufficientEvidence`; it does **not** silently fall back to the LLM.
2. **Citation chain** — every generated claim carries `evidence_chunk_ids[]`; the frontend's `EvidenceDrawer` / `CitationPanel` renders them.
3. **Quality check** — `outcome_evaluator.quality_check` re-reads the output against the cited chunks before it reaches the user. Failed checks block the response.

A skill that bypasses any of these three is a rule §2.6 violation and must be reverted.

---

## 8. Database — data-layer v2

The old "12 tables only" rule is retired. The new rule is **no domain-specific knowledge tables**, not "no additional tables". Any extension table must reuse the unified asset / resource / storage / capability tables defined here.

### P0 required tables (17)

`users` · `user_profiles` · `user_capabilities` ·
`documents` · `document_assets` · `chunks` · `knowledge_nodes` · `knowledge_edges` · `courses` ·
`learning_events` · `quiz_items` · `quiz_attempts` ·
`agents` · `agent_skills` · `agent_runs` ·
`generated_resources` · `storage_objects`

### P1 / P2 extension tables (4)

`learning_paths` · `learning_tasks` · `agent_messages` · `resource_versions`

### Hard database rules

- All domains share `documents` / `document_assets` / `chunks` / `knowledge_nodes` / `knowledge_edges`; filter by `domain`.
- PDF, Markdown, cover images, page images, OCR text, generated PPT / audio / video files are **assets**, not main-table blobs. Reference them via `document_assets.object_key` (source materials) or `storage_objects.object_key` (generated artefacts).
- `generated_resources` is the **single** table for course docs, PPT, mindmaps, quiz sets, hands-on labs, video storyboards, reading lists, and assessment reports.
- `chunks.embedding` may be `NULL` during ingestion; lifecycle is tracked by `embedding_status = pending | ready | failed`.
- `documents.raw_text` may be `NULL` (full text lives in `document_assets`); lifecycle is tracked by `documents.status = pending | ready | failed`.
- The first migration must run `CREATE EXTENSION IF NOT EXISTS vector;`. HNSW vector index is preferred for `chunks.embedding`; IVFFlat is an acceptable fallback when local pgvector < 0.5.0.
- GIN indexes are required on `documents.metadata` and `chunks.metadata` for JSONB filtering.
- Migration filenames follow `YYYYMMDD_HHMM_<verb>_<noun>.py`. Full DDL and SQLAlchemy mappings live in `.codex/AGENTS.md §9`.

### Authority order for data-layer rules

When the three docs conflict on schema, use:
`.codex/AGENTS.md §9 (Data-layer v2 schema)` > this `CLAUDE.md §8` > `../CompetitionTheme/A3赛题规划.md §5`.

---

## 9. What lives where (deep references)

| If you need… | Open |
|---|---|
| The constitution: every rule, full schema, agent×skill matrix, design rationale | `.codex/AGENTS.md` (≈1700 lines) |
| A3 grading rubric, capability → agent → skill mapping, demo storyboard | `../CompetitionTheme/A3赛题规划.md` |
| Data-layer v2 engineering task book (assets · resources · storage · v2 migration) | `../Chat/SecureHub_Data_Layer_V2_工程化改造任务书.md` |
| 3-member parallel split (A / B / C ownership, CODEOWNERS, API contracts, Harness, MinerU, Scrapling / MediaCrawler / MindSpider) | `../Plan/SecureHub_三人并行开发分工方案.md` |
| Engineering execution plan: P0/P1/P2 file list, Gantt, completion checklist | `../Workout/1-2FRAMEWORK_COMPLETION_PLAN.md` |
| What Codex already built and where it diverged | `../Workout/1-3.md` |
| Codex-specific playbooks (backend / frontend session scripts) | `.codex/workflows/` |

**Order of authority** when documents conflict: `.codex/AGENTS.md` > A3赛题规划 > Data-Layer v2 任务书 > 三人分工方案 > Workout plans > inline code comments. Update the higher source if the lower one is right.

---

## 10. Boundaries — do not touch without explicit instruction

- The existing real-API endpoints: `health.py`, `system.py`, `ctftime.py`. They work; leave them.
- The existing mock endpoints (`policy.py`, `placeholder.py`, `research.py` and their `services` / `repositories`). They back the挑战杯 demo; do **not** convert them to real until the A3 P0 surface is green.
- `.codex/`, `.github/`, `docker-compose.yml`, `pyproject.toml`, `package.json` — change only when the task explicitly calls for it; never sweep "while we're here".
- `frontend/node_modules/`, `backend/.venv/`, `.codegraph/*.db*`, `daemon.pid`, `daemon.log` — runtime artefacts, never commit.

**Hard "do not" list (collection / agent boundary):**

- Do **not** register a `crawler_agent` / `media_agent` / `spider_agent` / `pdf_agent` / `mineru_agent`. Scrapling, MediaCrawler, MindSpider, MinerU, and the Harness are all infrastructure (rule §2.2).
- Do **not** import MediaCrawler's or MindSpider's platform-specific DB schemas into the SecureHub main DB. Use their JSON / JSONL / CSV / SQLite *exports*, run them through `source_normalizer`, and land them in the unified v2 tables.
- Do **not** add bypass logic for logins, CAPTCHAs, Cloudflare / anti-bot, proxy rotation, or large-scale concurrent scraping. Public-only, throttled, robots-aware, license-respecting.
- Do **not** drop `platform / source_url / author / published_at / fetched_at / license / rights_note` from `documents.metadata` — the EvidenceDrawer relies on them.
- Do **not** rewrite the 3-member ownership boundaries (see `../Plan/SecureHub_三人并行开发分工方案.md` §9 CODEOWNERS) without consensus.

---

## 11. When stuck

- Constitutional question (Is this rule still in force? Can I add this table?) → re-read `.codex/AGENTS.md` and ask before acting.
- Scope question (Is this P0 or P1?) → consult `../Workout/1-2FRAMEWORK_COMPLETION_PLAN.md §3` priority columns.
- Demo / scoring question (Will this win A3 points?) → consult `../CompetitionTheme/A3赛题规划.md §6` checklist.
- If two docs disagree → trust order in §9, then surface the conflict to the user.

---

*Last refreshed: 2026-06-09. Constitution source: `.codex/AGENTS.md` (formerly this file before the AGENTS migration). 2026-06-09 update: added §2.1 multi-source collection compliance, expanded SSE to 7 events (added `artifact` / `trace`), added Harness layout, referenced the data-layer v2 task book and the 3-member parallel split.*
