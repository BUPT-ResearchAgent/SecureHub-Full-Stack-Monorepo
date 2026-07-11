# SecureHub Agent Runtime v1.1 Wave 4-6 Delivery

Date: 2026-07-11

## Scope Completed

- Wave 4: `course_learning_full_v1` creates path then document/PPT/quiz/lab
  resource fan-out, uses minimal declared typed-state projections, persists
  `EvidenceRef`/`ArtifactRef` lineage and uses deterministic QualityCheck
  defects/rework. PostgreSQL branches own isolated sessions; SQLite stays
  sequential for deterministic local tests.
- Wave 4 provider policy is Spark (`xfyun`) primary and explicit real DeepSeek
  fallback. Each provider attempt is journalled and correlated; fallback emits
  a replacement trace/new draft instead of concatenating text.
- Wave 5 adds durable approval/audit rows, pause/resume/retry controls,
  compatibility/migration checks, root/node/provider budgets, rate/circuit
  policy, model-tool ALLOW/ASK/DENY, metrics/evals and artifact/action recovery.
- Wave 6 removes `planned_skill.py`, production `RunRegistry`, direct
  `skill.run()`, implicit skill fixtures, old runtime Harness/context/graphs,
  legacy SSE endpoints/serializers and production LangGraph execution power.
  The fixed catalog remains exactly 9 Agents and 28 Skills.

## Migration And Tests

Migration head: `20260711_1030`.

| Gate | Result |
| --- | --- |
| Disposable SQLite migration | `upgrade head -> downgrade 20260611_0960 -> upgrade head` passed at head `20260711_1030` |
| Focused runtime/fault suite | `45 passed` for durable core/recovery, Wave 4-5, architecture and smoke coverage |
| Full backend suite, first run | `220 passed, 3 skipped` |
| Full backend suite, second consecutive run | `220 passed, 3 skipped` |
| Frontend | `npm run typecheck`, WorkflowRunClient reducer/reconnect/replacement harness and `npm run build` passed; Playwright desktop ran/pause/resumed to completed and mobile paused with `390px` client/scroll width parity and no API 4xx |
| Fault coverage | stale-worker fencing, outbox crash/replay, Redis loss/duplicate hints, SSE gap replay, unknown provider, artifact activation/action recovery, budget, approval, migration and terminal barriers are covered by focused tests |

## Fixture Runtime Evidence

All following runs used explicit `mode=fixture`; they are not external Provider
success claims. Each was started through authenticated HTTP, replayed through
SSE and checked against the same durable SQLite test database.

| Workflow | Root ID | Terminal | SSE | Provider calls |
| --- | --- | --- | --- | ---: |
| `course_learning_full_v1` | `199e8418-3709-4078-b034-ae10963abced` | succeeded | 380: artifact 4, done 1, evidence 6, progress 22, token 335, trace 12 | 6 |
| `profile_build_v1` | `4f3fd1a9-fc55-4c83-87d0-9c93ab432b44` | succeeded | 84 | 2 |
| `course_plan_v1` | `4cabd6d0-cf28-44cf-a14c-4d63bc6c0e0a` | succeeded | 87 | 2 |
| `tutor_routing_v1` | `eee1d0d8-2a04-4a6b-9233-4792a8d2dccb` | succeeded | 65 | 3 |
| `assessment_update_v1` | `31fc4b90-05fb-4693-9f41-69b33945630f` | succeeded | 80 | 4 |
| `resource_generate_v1` | `f23786ba-e5e8-429a-9b7b-a61d8c7117fc` | succeeded | 83 | 2 |
| token-boundary cancel | `a9388707-146b-4fb3-9966-9b514df48a13` | cancelled | 27, no artifact and no post-terminal token/artifact | 1 |

For the full course root, the DB check found six durable provider calls, six
child agent runs, four active artifacts and ordered replay count `380` equal to
the live stream count. The product-path roots had matching root status, child
records and provider-call IDs. A service-level pause/resume fixture control
run completed previously as `f0b624b2-fb47-4b7b-9cfd-856ea795755c`; focused
tests cover pause/resume/retry/approval and the final browser run covers the
control presentation.

## External Gates And Boundaries

- Real smoke against the local service returned sanitised
  `HTTP_503_REAL_MODE_DISABLED`; no fixture provider was injected.
- Real RAG returned `503 RAG_UNAVAILABLE` with the generic message
  `real RAG embedding dependency is unavailable`, not a DashScope credential
  detail or fixture evidence.
- Local configuration had no valid Spark/DeepSeek/DashScope/COS credentials,
  `AGENT_RUN_REAL_ENABLED` was disabled, and the configured PostgreSQL
  connection did not authenticate. COS activation remains blocked by the
  recorded HTTP 451 billing state.
- Docker is unavailable in the local execution environment, so a disposable
  PostgreSQL/Redis compose gate could not be started locally. The CI workflow
  still provisions those services; this report does not claim that remote CI
  has completed before its push-triggered run is observed.
- A deliberately concurrent SQLite-only control probe encountered a SQLite
  write lock. SQLite is not an accepted multi-worker deployment backend; no
  PostgreSQL live gate was claimed from this result. The durable fault suite
  remains green and production fan-out is PostgreSQL-only.

Therefore no real Spark primary, DeepSeek fallback/draft replacement, real RAG,
PostgreSQL production-root or COS success is claimed by this report. The code
and isolated fake-provider tests verify the real-to-real replacement semantics;
the external gate remains pending until credentials and services are available.

## Legacy Search Result

Production source search found no remaining `planned_skill.py`, production
`RunRegistry`, direct `skill.run()`, old runtime graph/harness execution
modules, duplicate streaming serializer or legacy streaming endpoint. The only
intentional `skill.run()` mention is the negative assertion in
`tests/runtime/test_legacy_removal.py`.

## Commits

- `586fdb39` `feat(runtime): complete wave 4-6 control plane`
- `f093d60e` `chore(ci): annotate static skill audit ownership`
- `docs(runtime): record wave 4-6 delivery and operations` (this documentation
  commit on `dev`)
