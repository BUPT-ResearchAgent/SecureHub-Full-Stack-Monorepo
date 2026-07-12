# SecureHub Agent Runtime v1.1 Wave 4-6 Delivery

Date: 2026-07-12

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

Historical Wave 4-6 migration head: `20260711_1030`. Current handoff head:
`20260712_1040`.

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

## 2026-07-12 Host Handoff Verification

The current workstation has healthy compose `postgres` and `redis` containers;
PostgreSQL is reachable at `127.0.0.1:15432`. The product workflow gate was
explicitly enabled with a `4096` token ceiling and used `STORAGE_PROVIDER=local`
to isolate the historical COS billing incident. A subsequent, separate
process-scoped COS smoke used `STORAGE_PROVIDER=cos`. No secret values, prompts,
reasoning or generated content are recorded here.

| Gate | Result |
| --- | --- |
| PostgreSQL migration and seed | `alembic upgrade head` / `current` reached `20260712_1040`; `seed_smoke.py` was idempotent with 9 agents and 28 skills |
| Disposable SQLite migration | `upgrade head -> downgrade 20260611_0960 -> upgrade head` passed at `20260712_1040` |
| `/api/v1/llm/health` | real `deepseek / deepseek-v4-pro` returned `available`; the endpoint now delegates to `get_llm_health()` rather than a fixture response |
| DeepSeek protocol | opt-in streaming JSON probe passed with `finish_reason=stop` and a valid JSON object |
| Qwen embedding and RAG | live embedding test passed; provenance audit found 3,549 ready same-profile chunks and 8/8 sourced hits for `SQL 注入` |
| Full backend regression | `230 passed, 3 skipped` |
| COS object storage | real process-scoped COS smoke passed upload, head, download, signed URL and cleanup delete |

The first real product-path attempt exposed two code defects without a fixture
fallback: `QualityCheck` accepted an untyped `type/detail` defect shape, and
the smoke script created a new asyncio loop for every `--verify-db` root.
`QualityCheck` now requires the frozen taxonomy and consistent decision shape;
the four product definitions have one bounded deterministic rework route for
recoverable defects; the smoke script batches all DB checks on one event loop.

| Workflow | Root ID | Terminal | Live / replay SSE | DB agent runs / provider calls |
| --- | --- | --- | ---: | ---: |
| `profile_build_v1` | `0645b4c8-7ef4-4e49-ba93-254fc6ac929e` | succeeded | 613 / 613 | 2 / 2 |
| `course_plan_v1` | `9a9f7a1e-6cbe-4ff1-a036-d8d6292ab9f2` | succeeded | 2913 / 2913 | 4 / 4 |
| `tutor_routing_v1` | `a844064f-af33-437a-beab-0d04dd0fdeef` | succeeded | 422 / 422 | 3 / 3 |
| `assessment_update_v1` | `1ff55bbf-a678-4900-a485-5ad5ececd47b` | succeeded | 537 / 537 | 4 / 4 |
| `resource_generate_v1` | `95b4b716-0a95-46ec-8b55-0ab05ac13900` | succeeded | 1030 / 1030 | 4 / 4 |

All five roots were `mode=real` with requested and actual
`deepseek / deepseek-v4-pro`; no root exposed a fixture provider. The resource
root emitted one durable artifact event. `provider_switches=0` is expected for
these direct-DeepSeek probes and is not a Spark-to-DeepSeek fallback claim.

A separate direct-DeepSeek cancellation smoke targeted
`resource_generate_v1` with `--cancel-after-first-token`. The client requested
cancel after observing its first token; 12 token events had durably arrived
before cancellation took effect. Root
`2daf935b-e3b7-4dbe-af34-d792dffc66d3` reached `cancelled`, with 21 live and 21
replayed SSE events, one durable `agent_run` and one `provider_call`. Its
`provider_switches=0` identifies a direct DeepSeek cancellation check, not
Spark cancellation or Spark-to-DeepSeek fallback evidence.

## Standard Validation Paths

### Correct And Accepted

1. Restore and verify the local dependencies first with
   `docker compose up -d --wait postgres redis` and `docker compose ps`. Use
   host PostgreSQL at `127.0.0.1:15432`; do not use the container-only
   `postgres:5432` address from a host process. Run `alembic upgrade head`,
   `alembic current`, and `scripts/seed_smoke.py` before a real root.
2. Confirm the settings resolved by the target process, not only the contents
   of `.env.local`. `AGENT_RUN_REAL_ENABLED=true`, the intended token ceiling,
   host database/Redis URLs, and the selected storage provider must be visible
   after restarting the backend because settings are process-cached.
3. Isolate external boundaries deliberately. Set `STORAGE_PROVIDER=local` for
   a DeepSeek/RAG/PostgreSQL gate, then label the result as local artifact
   storage. Use the opt-in `probe_deepseek_json_protocol.py --confirm-live`,
   the `embedding_live` test, and `audit_agent_run_provenance.py` separately
   before the HTTP workflow smoke. Validate COS independently under
   `STORAGE_PROVIDER=cos` with `smoke_cos_storage.py`, and require upload,
   head, download, signed URL and delete to all succeed.
4. For a real workflow, use the opt-in HTTP smoke with `--confirm-live`,
   `--verify-db`, explicit `mode=real`, provider and model. It must report a
   succeeded root, no fixture provider, ordered SSE live/replay equality, and
   durable `agent_run_ids` plus `provider_call_ids`. The current helper batches
   all database checks on one asyncio event loop and disposes that engine only
   after all selected roots finish.
5. For a real cancellation, use `--cancel-after-first-token` with explicit
   `mode=real`, provider and model, then require a `cancelled` root plus durable
   DB and equal live/replay SSE evidence. Record the actual provider: a direct
   DeepSeek cancel does not prove a Spark cancel or fallback.
6. Direct localhost diagnostics must bypass an ambient HTTP proxy, for example
   `curl --noproxy '*' http://127.0.0.1:<port>/api/v1/llm/health`. The smoke
   helper already uses a proxy-free opener. Keep the response limited to
   provider/model/status and sanitised errors.
7. Test migration downgrade/upgrade only against a disposable SQLite database.
   Do not downgrade the local PostgreSQL instance that contains real workflow
   records merely to exercise the migration chain.

### Incorrect Or Insufficient

- `AGENT_RUN_REAL_ENABLED=false` correctly produces a sanitised real-mode
  refusal; it is not a Provider, RAG or workflow success. A fixture root proves
  deterministic fixture behavior only and must never replace a real gate.
- `STORAGE_PROVIDER=local` validates local Artifact Saga behavior only. It is
   not evidence that COS upload, head, download, signed URL, or delete works.
   Only the separate real COS smoke that completes all five operations can
   close that gate.
- `--expect-fallback` observes a fallback that happened; it does not induce a
   failure. A valid Spark-to-DeepSeek test needs a configured Spark bearer key
   and a development-only controlled primary stream interruption after the first
   real token. Report it as a controlled fault, never as a Spark service outage.
- A direct DeepSeek `--cancel-after-first-token` run validates cancellation for
   that provider only. It cannot be reported as Spark primary execution, a
   Spark cancellation, or a Spark-to-DeepSeek fallback.
- A `502` returned by an ambient proxy while calling `localhost` is a local
  proxy-routing failure, not an `/llm/health` failure. Repeat through the
  no-proxy path before diagnosing application code.
- Do not use an older smoke implementation that calls `asyncio.run()` once per
  `--verify-db` root: asyncpg connections become bound to a closed loop. Use the
  batched helper in this revision. Also do not equate status API
  `child_run_count` with `agent_runs`; it counts workflow step attempts and may
  include deterministic action nodes. Use the DB audit's `agent_run_ids`.

## Remaining External Gates

- Spark primary, controlled Spark stream interruption, real DeepSeek fallback
  replacement, and a real-token cancel on the Spark path remain unverified:
  the resolved `XFYUN_API_KEY` is empty. The provider construction preflight
  returned sanitised `ProviderUnavailable` / `XFYUN_PROVIDER_UNAVAILABLE`; no
  Spark network request was sent.
- COS has now passed its independent real gate on 2026-07-12: process-scoped
  `STORAGE_PROVIDER=cos` completed upload, head, download, signed URL and
  delete. The product workflow records above still use local artifact storage
  as explicitly labelled. The prior real `451 UnavailableForLegalReasons`
  billing block remains historical evidence, not a retroactive claim that COS
  had succeeded then.
- The earlier 2026-07-11 host record with disabled real execution, unavailable
  RAG and unauthenticated PostgreSQL was superseded by this dated verification;
  its fail-closed behavior remains relevant only as historical evidence.

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
- `e23176b6` `fix(runtime): harden live handoff verification`
- `f625f60f` `docs(runtime): standardize live verification paths`
