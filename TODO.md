# SecureHub Agent Runtime TODO

> Version: v2.5
> Updated: 2026-07-16
> Authority: `Plan/2026-07-11_SecureHub_多智能体底层完整架构实施方案.md` v1.1
> Delivery evidence: `Workout/Agent-Runtime-Wave-0-3.md` and
> `Workout/Agent-Runtime-Wave-4-6.md`
> Productization evidence: `../Workout/10-A3-S5-AB-1.md`,
> `../Workout/10-A3-S6-BA-1.md`, and `../Workout/10-A3-S7-ACB-1.md`
> Multi-course catalog evidence: `../Workout/11-A3-Multi-Course-Real-Catalog.md`
> Resource reliability implementation: commit `868b4904`

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

### Resource Generation Reliability (2026-07-16)

- [x] Split the resource producer's per-call Provider completion cap (`2400`) from its cumulative node budget (`8000`) without changing unset legacy workflow serialization; bounded QualityCheck rework remains exactly one attempt.
- [x] Persist QualityCheck defect feedback across checkpoints and canonicalize resource queries from the server-owned knowledge point/course/domain relationship.
- [x] Keep the last ready artifact visible during a new attempt; switch only on root success. Expose durable cancel through `WorkflowRunClient.cancel`, while unsubscribe remains view cleanup only.
- [x] Preserve PR #50 `securehub_swiss_v1` generation and rendering. Commit `868b4904` passed 64 focused/compatibility tests plus frontend typecheck/build and project-owner manual review.
- [ ] Do not reinterpret this fix as "generation can never fail": network/provider failure, insufficient Evidence and safety rejection remain honest terminal outcomes, and none closes the Spark Gate.

### A3 Multi-Course Catalog v1.0

- [x] `courses` 真实目录固定为四门稳定产品：`WEBSEC-101` 为完整 `ready` 课程；`CRYPTO-101`、`NET-SEC-201`、`SDL-201` 是真实目录记录但仍为只读 `preview`。
- [x] preview 的 detail/graph/path/progress 诚实返回空投影；旧前端材料仅以“预置内容预览”展示，不计为 RAG、Evidence、Artifact、AgentRun、Provider Call 或学习进度。
- [x] 课程 plan/resource/tutor/assessment、资源 retry 与直接 `/workflow-runs` 都在 durable root 创建前对 preview 返回 `409 COURSE_CONTENT_NOT_READY`；未知 course 不回落 Web 安全。
- [ ] 三门 preview 升级为 `ready` 前，分别补齐真实资料入库、knowledge_nodes/edges、Evidence manifest、RAG/evidence-floor 验收与独立的 Skill-domain 语义版本评审；不得把此目录工作误报为内容闭环。

### A3 Productization S5-S7

- [x] S5 closes the real quiz -> assessment -> QualityCheck -> atomic
  capability/persona audit loop without changing historical workflow roots.
- [x] S6 projects Evidence, Agent/Skill, QualityCheck, Provider, Artifact and
  control state from one durable root without a second event serializer.
- [x] S7 adds the independent `fund_recommendation_v1` workflow using the
  frozen nine Agents and 28 Skill bindings, the shared profile/capability
  sources and the shared knowledge asset tables under `domain=fund`.
- [x] Re-ran the authenticated real chains with PostgreSQL, Qwen, DeepSeek
  and Browser Use: S5 assessment/profile/path refresh, S6 root-scoped replay,
  and S7 fund recommendation are all `real-accepted`. Spark remains the S8
  external gate.
- [x] Formal lifecycle status is `planned -> in_progress -> code_complete ->
  engineering-accepted -> real-accepted`; `external-gate-open` is a separate
  Gate marker and never a substitute for a lifecycle state.

### Post-Merge Verification Note

- PR #43 merged the Wave 0-3 implementation into `upstream/dev`. A separate
  follow-up stabilizes the SQLite heartbeat test without weakening production
  lease/fencing semantics; two consecutive full `pytest -q` runs report
  `255 passed, 3 skipped`.
- `backend/data/runtime_wave_storage/` is regenerated local Artifact Saga
  output and is ignored precisely. Existing local evidence files are retained,
  not deleted or committed.
- The prior 2026-07-11 local PostgreSQL volume remained at `20260611_0960`,
  before the durable-runtime migrations. That historical constraint no longer
  describes the verified 2026-07-12 host state below.
- 2026-07-12 host verification restored healthy PostgreSQL/Redis and migrated
  the local database to `20260712_1040`. Real DeepSeek, Qwen RAG and all five
  product paths passed with durable root/agent-run/provider/SSE replay checks;
  details and IDs are recorded in `Workout/Agent-Runtime-Wave-4-6.md`.

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

- [x] Re-run PostgreSQL, real DeepSeek, Qwen RAG and the five product workflow
  paths with real `agent_runs`, provider calls and SSE replay. The 2026-07-12
  result used explicit local artifact storage and did not claim COS success.
- [ ] Supply the Spark bearer key, then run the real Spark primary chain, a
  controlled Spark stream interruption with real DeepSeek replacement, and a
  real-token cancel. `--expect-fallback` alone does not manufacture a failure.
- [x] Tencent COS Runtime upload/head/download/signed URL/delete passed on
  2026-07-12. The earlier `451 UnavailableForLegalReasons` is historical;
  GitHub-external data full synchronization remains a separate incomplete
  governance track and is not implied by this Runtime smoke.

## Required Regression Gates

- `pytest -q`
- SQLite disposable migration: `upgrade head -> downgrade 20260611_0960 -> upgrade head`
- `pnpm typecheck` and `pnpm build`
- Runtime architecture/durable recovery tests and the WorkflowRunClient harness
- Manual live gate: record root IDs, actual provider/model, seven-SSE counts,
  Last-Event-ID replay, and no fixture/QualityCheck/Evidence/Artifact bypass
