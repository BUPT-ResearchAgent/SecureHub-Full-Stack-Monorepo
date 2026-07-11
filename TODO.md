# SecureHub Agent Runtime TODO

> Version: v2.1
> Updated: 2026-07-11
> Authority: `Plan/2026-07-11_SecureHub_多智能体底层完整架构实施方案.md` v1.1
> Delivery evidence: `Workout/Agent-Runtime-Wave-0-3.md`

## Current Status

Wave 0-3 is complete and accepted. This means the contract freeze, Golden
Vertical Slice, Durable Core, frozen full production catalog, five product
adapters, and the WorkflowRunClient are delivered. It does **not** mark Wave
4-6 collaboration expansion, HITL/operations/security deepening, or legacy
removal as done.

The fixed nine business Agents remain:

`policy_interpreter`, `hot_analyst`, `job_analyst`, `competition_advisor`,
`career_planner`, `topic_explorer`, `doc_archivist`, `task_orchestrator`, and
`outcome_evaluator`.

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

- [ ] Add parallel resource fan-out and full ArtifactRef/EvidenceRef/TypedState
  collaboration beyond the Wave 0-3 sequential paths.
- [ ] Extend QualityCheck defect taxonomy, rework lineage, resource versioning,
  and budgets beyond the delivered bounded Golden Slice behavior.
- [ ] Validate real-to-real provider fallback and full visible-stream replacement
  against a live alternative provider.

### Wave 5: HITL, Policy, And Operations

- [ ] Add production approval/HITL handling, full pause/resume/retry UI, and
  multi-level budget/rate/permission policy enforcement.
- [ ] Add operational metrics/evals/audit views, signed artifact access, and
  the broader security hardening described by v1.1.

### Wave 6: Legacy Removal And Final Acceptance

- [ ] Retire remaining compatibility-only `BaseSkill`, legacy Harness,
  in-memory registry, direct `skill.run()`, and duplicate serializer paths
  once all consumers have migrated.
- [ ] Run the full multi-provider, multi-worker, browser, migration, and
  deployment/operations acceptance gate.

## External Gate

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
