# SecureHub Agent Runtime v1.1 Wave 0-3 Delivery

Date: 2026-07-11

Scope completed: Contract Freeze, the `resource_generate_v1` Golden Vertical
Slice, Durable Core, the frozen 9-Agent/28-Skill catalog, and the five product
workflow adapters. Wave 4-6 work is explicitly not claimed by this report.

## Authority And Contract

- `RuntimeEngine` is the sole production execution authority; `SecureHubStateMachine`
  is the only lifecycle validator; `WorkflowDefinition` is framework-neutral.
- PostgreSQL `workflow_runs` and `workflow_events` are the durable state/event
  source. Redis is only a worker/SSE wake-up and fan-out projection.
- The catalog is locked to 9 fixed business Agents and 28 production Skills;
  RuntimeSupervisor startup checks the enabled database mirror before workers
  can claim production work.
- The public SSE vocabulary remains exactly `progress`, `evidence`, `token`,
  `artifact`, `trace`, `done`, and `error`.
- Real execution is fail-closed. It cannot enter fixture mode or skip RAG,
  evidence snapshots, child `agent_runs`, explicit QualityCheck, or artifact
  persistence.

`docs/api/workflow-run-contract.md` freezes the public control/SSE semantics.
Architecture tests lock the Agent catalog, StateMachine, explicit QualityCheck
node rule, real/fixture separation, and framework-neutral workflow boundary.

## Live DeepSeek Evidence

All completed live roots used `mode=real`, provider `deepseek`, and model
`deepseek-v4-pro`. No prompt, key, reasoning, or full model response was
recorded in this report.

| Path | Root ID | Terminal | SSE total and shape |
| --- | --- | --- | --- |
| Golden `resource_generate_v1` | `5ffd1c7a-203f-49c3-8df5-1600afdd4acd` | succeeded | 1132: progress 18, evidence 4, token 1100, artifact 1, trace 8, done 1 |
| `/profile/chat` | `02adc08f-689d-432b-bfc8-37a8718463bc` | succeeded | 593: progress 10, evidence 2, token 576, trace 4, done 1 |
| `/courses/{id}/plan` | `5da3a415-70e5-4096-b131-4903ef818a6e` | succeeded | 758: progress 10, evidence 2, token 741, trace 4, done 1 |
| `/courses/{id}/resources/generate` | `c02715fc-80a2-4fba-8733-16f297b6a0a0` | succeeded | 317: progress 10, evidence 2, token 299, artifact 1, trace 4, done 1 |
| `/tutor/ask` | `93436089-023c-4e74-8944-3c74588f2b92` | succeeded | 841: progress 11, evidence 3, token 820, trace 6, done 1 |
| `/assessment/run` | `a3f78082-ee12-48c7-a148-18b3c1654582` | succeeded | 909: progress 18, evidence 4, token 878, trace 8, done 1 |

The Golden root had one QualityCheck defect, took its bounded deterministic
rework route, and then succeeded. Its active artifact is
`77f28103-d437-47a4-810d-0a0193d0ba56`; the product resource artifact is
`380a86f1-691b-40d6-9c75-c7cd4f44025b`.

For the Golden root, foreign-key/correlation inspection aligned the root,
five step attempts, four child `agent_runs`, twelve evidence snapshots, four
provider-call journal rows, the active artifact, and ordered events. The five
product roots recorded provider-call counts `2 / 2 / 2 / 3 / 4`; together with
the Golden run this is 17 real provider calls.

Last-Event-ID replay was verified on the resource root: cursor `314` returned
only durable sequences `315`, `316`, and `317`. A restart manifest check still
reported exactly 9 Agents and 28 Skills.

## Durable And Failure Evidence

- PostgreSQL queued scan continues to claim work when Redis hints are lost or
  duplicated; stale root/step writes are rejected by `lease_epoch` fencing.
- Event allocation is atomic per root and `workflow_events` is a transactional
  outbox. Publisher crash-after-publish recovery is at-least-once; reducers
  deduplicate `(workflow_run_id, sequence)`.
- Replay-first SSE performs live gap recovery from PostgreSQL, preserves order,
  and does not expose a staging artifact before activation.
- Provider calls journal `started`, `completed`, and `unknown`; an unknown
  result moves the root to approval/retry rather than claiming exactly-once.
- An observed empty provider stream is journaled as completed/unavailable;
  only an opaque provider crash window becomes `unknown`.
- Artifact Saga tests cover staging, active promotion, interrupted activation,
  orphaning, and tombstone cleanup using an explicit local provider.
- Real retrieval without a durable source `chunk_id` now fails closed rather
  than manufacturing an Evidence identity.

## Verification

| Command or gate | Result |
| --- | --- |
| Post-merge `pytest -q` stability gate | The former 150 ms SQLite heartbeat assertion was made lease-expiry-aware with a 1 s lease; two consecutive full runs now each report `255 passed, 3 skipped` |
| Focused post-review runtime checks | `pytest -q tests/runtime/test_skill_executor_guardrails.py tests/runtime/test_durable_recovery_paths.py` -> `17 passed` |
| SQLite migration round trip | `upgrade head -> downgrade 20260611_0960 -> upgrade head` passed; head `20260711_1020` |
| Persisted catalog gate | Fresh migrated SQLite mirror validated exactly `9 agents / 28 skills` |
| Frontend typecheck/build | `pnpm typecheck` and `pnpm build` passed |
| WorkflowRunClient harness | reducer, duplicate suppression, disconnect reconnect, refresh cursor recovery, Last-Event-ID gap replay, and provider stream replacement passed |
| Browser check | Login UI checked with Playwright at desktop and `390x844`; no blank canvas, overlap, or text clipping observed |
| Diff hygiene | `git diff --check` passed; only CRLF conversion warnings were emitted |

## Post-Merge Verification Boundary

- PR [#43](https://github.com/BUPT-ResearchAgent/SecureHub-Full-Stack-Monorepo/pull/43)
  merged the original Wave 0-3 implementation into `upstream/dev` at
  `bc679f6a`. The original evidence root IDs above are retained as historical
  execution evidence.
- The heartbeat test used a 150 ms lease and a fixed 190 ms observation under
  an independent SQLite renewal session. Under full-suite load that left only a
  few milliseconds of scheduling margin and could correctly fence a late
  worker. The production lease/fencing semantics were not relaxed; the test now
  crosses a one-second original lease and proves a later heartbeat expiry
  prevents a second worker claim.
- The local Docker PostgreSQL volume was restarted only for a read-only audit.
  It is at Alembic revision `20260611_0960`, has no `workflow_*` tables, and
  contains no generated resources. It therefore cannot independently re-query
  the six historical roots. No migration was run against that volume and no
  external Neon database was queried without authority.
- `backend/data/runtime_wave_storage/` contains regenerated local staged
  Artifact Saga output and is ignored precisely; existing artifacts were not
  deleted or included in source control.

## External Blocker

The live Tencent COS runtime `put_object` gate returned
`451 UnavailableForLegalReasons` due to the account billing state. It was not
retried without a configuration change, not converted into fixture success, and
not reported as a successful COS activation. The local Artifact Saga evidence
above remains valid. After the account is restored, rerun only this external
COS gate.

## Commit

The implementation was authored as `dbe3e857`
(`feat(runtime): complete agent runtime waves 0-3`) and recorded by
`337fffc2`; its clean rebased equivalents `31bc9ec2` and `e58626c2` were
merged through PR #43. The follow-up stability/ignore hygiene change is kept
separate from the original Wave delivery.
