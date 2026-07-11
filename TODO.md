# SecureHub Agent Runtime TODO

> Version: v2.2
> Updated: 2026-07-11
> Authority: `Plan/2026-07-11_SecureHub_多智能体底层完整架构实施方案.md` v1.1
> Delivery evidence: `Workout/Agent-Runtime-Wave-0-3.md` and
> `Workout/Agent-Runtime-Wave-4-6.md`

## Current Status

Wave 0-6 implementation is complete. In addition to the Wave 0-3 durable
core, Wave 4 adds typed artifact/evidence lineage, bounded collaboration
fan-out, defect-aware QualityCheck rework and transparent real-to-real provider
replacement. Wave 5 adds pause/resume/retry/approval, budgets, tool policy,
checkpoint migration, metrics and audit facts. Wave 6 removes legacy execution
and duplicate SSE authorities. External live gates remain explicitly separate
from this code-complete status.

The fixed nine business Agents remain:

`policy_interpreter`, `hot_analyst`, `job_analyst`, `competition_advisor`,
`career_planner`, `topic_explorer`, `doc_archivist`, `task_orchestrator`, and
`outcome_evaluator`.

### Post-Merge Verification Note

- PR #43 merged the Wave 0-3 implementation into `upstream/dev`. A separate
  follow-up stabilizes the SQLite heartbeat test without weakening production
  lease/fencing semantics; two consecutive full `pytest -q` runs report
  `255 passed, 3 skipped`.
- `backend/data/runtime_wave_storage/` is regenerated local Artifact Saga
  output and is ignored precisely. Existing local evidence files are retained,
  not deleted or committed.
- The currently available local PostgreSQL volume remains at
  `20260611_0960`, before the durable-runtime migrations, so it cannot
  independently re-query the six historical real roots. It was not migrated
  for verification and no external database was queried without authority.

## Wave 0: Contract Freeze

- [x] Freeze `RuntimeEngine` as the unique production execution authority and
  `SecureHubStateMachine` as the unique state-machine authority.
- [x] Freeze framework-neutral versioned `WorkflowDefinition`; LangGraph is
  limited to a replaceable topology adapter.
- [x] Lock nine Agents, their stable UUID derivation, and the 28-Skill
  production catalog through manifest/seed/architecture tests.
- [x] Freeze root/node state vocabulary, error taxonomy, real/fixture policy,
  requested/actual provider identity, semantic version compatibility, and
  provider started/completed/unknown semantics.
- [x] Freeze exactly seven external SSE event types and the EventEnvelope,
  Last-Event-ID, terminal exclusivity, and stream-replacement contract.
- [x] Freeze explicit QualityCheck nodes and the separation of Runtime Ports,
  deterministic Workflow Actions, and Model Tools.
- [x] Publish the contract in `docs/api/workflow-run-contract.md` and sync
  `CLAUDE.md` and `.codex/AGENTS.md`.

## Wave 1: Golden Vertical Slice

- [x] Deliver `resource_generate_v1` through durable root, step attempt,
  running child `agent_runs`, true RAG, evidence snapshot, ContextBuilder,
  provider journal, real provider, strict parse, candidate output, explicit
  QualityCheck, Artifact Saga, transactional outbox, SSE, and terminal state.
- [x] Prove real DeepSeek `deepseek-v4-pro` execution without fixture fallback,
  fake evidence, relaxed quality acceptance, or fabricated artifacts.
- [x] Verify bounded QualityCheck rework and root/step/child/evidence/provider/
  artifact/event correlation. See the Golden root in the delivery report.

## Wave 2: Durable Core

- [x] Add durable Run/Step/Event/Checkpoint/Evidence/ProviderCall models and
  additive migrations through `20260711_1020`.
- [x] Use PostgreSQL queued scans as the source of worker recovery, with Redis
  only for notification/fan-out acceleration.
- [x] Implement atomic event sequencing, Transactional Outbox, publisher
  retry/crash recovery, replay-first SSE, duplicate dedupe, and live gap fill.
- [x] Implement worker claim, heartbeat, `lease_epoch` fencing, checkpoint
  recovery, semantic compatibility, idempotent start/cancel, and explicit
  unknown-provider retry semantics.
- [x] Implement COS/local Artifact Saga states `staging`, `active`,
  `orphaned`, and `deleted`, including activation recovery and cleanup tests.
- [x] Exercise API/worker/publisher failure, Redis loss/duplicate notification,
  stale-worker fencing, event gap, unknown provider outcome, and interrupted
  artifact activation through focused tests.

## Wave 3: Catalog And Product Paths

- [x] Migrate the frozen 28-Skill catalog to the canonical `SkillExecutor`.
- [x] Make `/profile/chat`, `/courses/{id}/plan`,
  `/courses/{id}/resources/generate`, `/tutor/ask`, and `/assessment/run`
  adapters over `WorkflowApplicationService` with one queryable root ID.
- [x] Remove direct Skill execution, implicit fixtures, in-memory queues, and
  generated unqueryable run IDs from those five production paths.
- [x] Deliver `WorkflowRunClient` typed reducers for all root/node statuses,
  seven SSE types, Last-Event-ID persistence, live gap recovery, duplicate
  suppression, and provider stream draft replacement.
- [x] Record live DeepSeek success evidence for the Golden Slice and every
  product path; the six root IDs, SSE counts, and 17 real provider calls are in
  the delivery report.

## Remaining Work

### Wave 4: Collaboration Expansion

- [x] Add `course_learning_full_v1` resource fan-out, minimal typed-state
  projection and durable `ArtifactRef` / `EvidenceRef` lineage. PostgreSQL
  uses isolated branch sessions; SQLite retains deterministic sequential mode.
- [x] Add QualityCheck defect taxonomy, deterministic defect routes, repeated
  defect detection and bounded rework lineage.
- [x] Add Spark-primary / DeepSeek-explicit-real-fallback policy, provider
  stream attempts and draft replacement without provider text concatenation.
- [x] Cover fallback replacement with isolated provider fakes. A live fallback
  gate is still blocked until both real provider credentials are available.

### Wave 5: HITL, Policy, And Operations

- [x] Add durable approval/audit records, pause/resume/retry APIs, ownership
  checks, WorkflowRunClient controls and checkpoint compatibility/migration.
- [x] Add root/node/provider budget accounting, rate/circuit policy, typed
  ALLOW/ASK/DENY model-tool policy and high-risk Workflow Action approval.
- [x] Add per-root metrics/evals/trace-safe audit summaries and recovery tests.

### Wave 6: Legacy Removal And Final Acceptance

- [x] Retire legacy `planned_skill.py`, direct `skill.run()`, production
  `RunRegistry`, old Harness/context/graph authority, implicit skill fixtures,
  duplicate SSE serializers/endpoints and production LangGraph execution.
- [x] Run migration round-trip, two full backend suites, focused recovery/fault
  tests, typecheck/build/client harness and desktop/mobile browser checks.
- [x] Record deployment, recovery, demo and external-gate handling in
  `docs/operations/agent-runtime-wave-4-6.md` and the Wave 4-6 report.

## External Gate

- [ ] Supply valid PostgreSQL, Spark, DeepSeek, DashScope/RAG and COS
  credentials, then re-run the real provider primary/fallback, RAG and COS
  gates. Current local configuration has real execution disabled; real requests
  return sanitised `503` failures and never fixture fallback.
- [ ] Re-run the Tencent COS runtime artifact smoke only after account billing
  is restored. The last real `put_object` returned
  `451 UnavailableForLegalReasons`; it is an external blocker, not a success,
  and not a fixture fallback. Local Artifact Saga verification is complete.

## Required Regression Gates

- `pytest -q`
- SQLite disposable migration: `upgrade head -> downgrade 20260611_0960 -> upgrade head`
- `pnpm typecheck` and `pnpm build`
- Runtime architecture/durable recovery tests and the WorkflowRunClient harness
- Manual live gate: record root IDs, actual provider/model, seven-SSE counts,
  Last-Event-ID replay, and no fixture/QualityCheck/Evidence/Artifact bypass
