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
2. **Cross-cutting infra is not an agent.** `rag/`, `knowledge/loaders/`, `runtime/router.py`, `runtime/guardrails/` are middleware. Do not list them as agents.
3. **One `documents` + one `chunks` table for every domain.** Filter by `domain` column. Never create `course_chunks`, `fund_chunks`, etc.
4. **`user_profiles` is the single source of truth** for the learner profile. Feature modules read/write this table; they do not maintain their own profile tables.
5. **Every new endpoint / service / repository file starts with a status comment**: `# Status: real` | `# Status: mock` | `# Status: partial-real`. No exceptions.
6. **Generative skills must call `rag.retrieve()` before composing the prompt.** Bypassing RAG to call the LLM directly is forbidden — it kills the anti-hallucination story.
7. **Every skill ends with `await ctx.log_run(...)`** writing to `agent_runs`. The trace visualization depends on it. CI greps for this.
8. **Changes that touch §3 rules, §9 schema, or §19 deltas in `.codex/AGENTS.md` must update `.codex/AGENTS.md` in the same change.** Code and constitution stay in sync.

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
| Streaming | SSE — 5 event types: `token` / `evidence` / `progress` / `done` / `error` |
| State mgmt (FE) | `useReducer` + `localStorage` per feature. **No Redux / Zustand.** |
| Path alias | `@/*` → `src/*`; custom `figma:asset/` Vite resolver |

Do **not** introduce: Milvus, Neo4j, MongoDB, Doris, Elasticsearch, MUI, Redux. They are competing choices we already ruled out.

---

## 4. Repo layout (top level)

```
backend/app/
  agents/          # 9 agent folders, each = agent.py + skills/*.py + tools.py
  runtime/         # router, capability_manifest, logger, guardrails/, graphs/
  llm/             # xfyun.py · deepseek.py · embedding.py
  rag/             # chunker · retriever (BM25 + vector + RRF) · reranker · evidence_builder
  knowledge/       # loaders/ for each domain
  db/              # models/ (12 tables) + migrations/
  streaming/       # SSE events + writer
  api/v1/endpoints/  # FastAPI routes
frontend/src/app/
  pages/           # 10 top-level routes (CourseStudy is the 10th)
  features/        # course/ · profile/ · chat/ · research/ ... each self-contained
  components/      # Layout, EvidenceDrawer, etc.
  lib/             # api.ts · sse.ts
.codex/
  AGENTS.md        # ← full constitution (everything in detail). Read on first session.
  context/         # Codex-specific session context
  workflows/       # Codex playbooks
../CompetitionTheme/A3赛题规划.md   # A3 task spec + capability→agent→skill mapping
../Workout/                          # Long-form planning artefacts (FRAMEWORK_COMPLETION_PLAN, etc.)
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

## 8. Database — the 12 tables (no others)

`documents` · `chunks` · `knowledge_points` · `kp_prerequisites` · `quiz_items` · `users` · `user_profiles` · `learning_events` · `agents` · `agent_skills` · `agent_runs` · `courses`

Full DDL and SQLAlchemy mappings live in `.codex/AGENTS.md §9`. Migration filenames follow `YYYYMMDD_HHMM_<verb>_<noun>.py`. The first migration must run `CREATE EXTENSION IF NOT EXISTS vector;`.

---

## 9. What lives where (deep references)

| If you need… | Open |
|---|---|
| The constitution: every rule, full schema, agent×skill matrix, design rationale | `.codex/AGENTS.md` (≈1500 lines) |
| A3 grading rubric, capability → agent → skill mapping, demo storyboard | `../CompetitionTheme/A3赛题规划.md` |
| Engineering execution plan: P0/P1/P2 file list, Gantt, completion checklist | `../Workout/1-2FRAMEWORK_COMPLETION_PLAN.md` |
| What Codex already built and where it diverged | `../Workout/1-3.md` |
| Codex-specific playbooks (backend / frontend session scripts) | `.codex/workflows/` |

**Order of authority** when documents conflict: `.codex/AGENTS.md` > A3赛题规划 > Workout plans > inline code comments. Update the higher source if the lower one is right.

---

## 10. Boundaries — do not touch without explicit instruction

- The existing real-API endpoints: `health.py`, `system.py`, `ctftime.py`. They work; leave them.
- The existing mock endpoints (`policy.py`, `placeholder.py`, `research.py` and their `services` / `repositories`). They back the挑战杯 demo; do **not** convert them to real until the A3 P0 surface is green.
- `.codex/`, `.github/`, `docker-compose.yml`, `pyproject.toml`, `package.json` — change only when the task explicitly calls for it; never sweep "while we're here".
- `frontend/node_modules/`, `backend/.venv/`, `.codegraph/*.db*`, `daemon.pid`, `daemon.log` — runtime artefacts, never commit.

---

## 11. When stuck

- Constitutional question (Is this rule still in force? Can I add this table?) → re-read `.codex/AGENTS.md` and ask before acting.
- Scope question (Is this P0 or P1?) → consult `../Workout/1-2FRAMEWORK_COMPLETION_PLAN.md §3` priority columns.
- Demo / scoring question (Will this win A3 points?) → consult `../CompetitionTheme/A3赛题规划.md §6` checklist.
- If two docs disagree → trust order in §9, then surface the conflict to the user.

---

*Last refreshed: 2026-06-08. Constitution source: `.codex/AGENTS.md` (formerly this file before the AGENTS migration).*
