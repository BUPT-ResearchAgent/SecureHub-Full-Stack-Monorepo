<!--
  Rule numbers below refer to CLAUDE.md §2 (the eight ironclad rules, quick reference).
  Full rationale and schema lives in .codex/AGENTS.md §3 / §9 / §19.
  If a rule wording confuses you, open .codex/AGENTS.md first.
-->

## Summary

- 
- 

## Scope

- [ ] P0 / P1 / P2 priority of this change (see `Workout/1-2FRAMEWORK_COMPLETION_PLAN.md §3`):  ____
- [ ] Touches one of the 9 agents → which?  ____
- [ ] Touches the shared schema (`documents` / `chunks` / `user_profiles` / `agent_runs`) → yes / no

## Eight ironclad rules — self-check

> Reference: `CLAUDE.md §2.1`–`§2.8`. Authoritative source: `.codex/AGENTS.md §3`.

- [ ] **§2.1** I did not add a 10th agent role. The fixed nine remain: policy_interpreter, hot_analyst, job_analyst, competition_advisor, career_planner, topic_explorer, doc_archivist, task_orchestrator, outcome_evaluator.
- [ ] **§2.2** I did not model cross-cutting infrastructure (`rag/`, `knowledge/loaders/`, `runtime/router.py`, `runtime/guardrails/`) as an agent.
- [ ] **§2.3** I did not create domain-specific knowledge tables such as `course_chunks` or `fund_chunks`. All domains share `documents` + `chunks` filtered by the `domain` column.
- [ ] **§2.4** I did not create feature-local persona storage. `user_profiles` remains the single source of truth.
- [ ] **§2.5** Every new endpoint / service / repository file starts with `# Status: real | mock | partial-real`.
- [ ] **§2.6** Generative skills call `rag.retrieve()` before composing the LLM prompt (no direct LLM bypass).
- [ ] **§2.7** Every skill ends with `await ctx.log_run(...)` writing to `agent_runs`.
- [ ] **§2.8** If I changed §2 rules, §8 schema, or §19 deltas in `.codex/AGENTS.md`, I updated both `.codex/AGENTS.md` and `CLAUDE.md` in the same change.

## Verification

- [ ] `uv run pytest --collect-only -q` passes
- [ ] `uv run alembic upgrade head` clean (if migrations changed)
- [ ] `pnpm typecheck` passes
- [ ] `docker compose config` valid (if compose / env changed)
- [ ] Manual SSE smoke (if a generative skill changed): `evidence` event carries ≥ `MIN_EVIDENCE` chunk ids before any `token` event

## Notes for reviewers

<!-- Anything reviewers should know: trade-offs, follow-ups, demo links, screenshots. -->
