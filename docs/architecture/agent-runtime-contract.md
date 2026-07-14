# SecureHub Agent Runtime Contract

Version: `v1.1`
Status: implemented and frozen through Waves 0-6
Authority: the v1.1 implementation plan dated 2026-07-11

This is the executable contract for `backend/app/runtime/contracts.py`. It
supersedes older descriptions that place QualityCheck inside Harness or allow a
product endpoint to run a Skill directly.

## Authorities

1. `RuntimeEngine` is the only production execution authority. It owns root and
   step lifecycle, scheduling, cancellation, rework, terminal convergence and
   checkpoint recovery.
2. `SecureHubStateMachine` is the only state transition authority.
3. PostgreSQL is the state, lease, checkpoint and audit truth. Redis is only a
   rebuildable wake-up/fan-out projection.
4. `workflow_events` is the only external event truth and transactional outbox.
5. `SkillExecutor` is the only production Skill execution core.
6. `ArtifactRef`, `EvidenceRef` and typed workflow state are the only agent
   collaboration media. Agent free-chat is not a workflow transport.

LangGraph may validate or visualise topology. It may not own run state,
checkpointing, scheduling, recovery or terminal state.

## Fixed Agent And Skill Catalog

Exactly these nine UUIDv5-backed names are enabled:

`policy_interpreter`, `hot_analyst`, `job_analyst`, `competition_advisor`,
`career_planner`, `topic_explorer`, `doc_archivist`, `task_orchestrator`,
`outcome_evaluator`.

The frozen production binding count is 28. `runtime.skill_catalog` derives the
full list from those Agent classes and asserts both the count and UUIDv5 rule.
`_examples/EchoSkill` is not a production binding. Missing, extra, renamed, or
UUID-drifted enabled agents are startup/CI failures.

## Lifecycle

Root states:

```text
queued -> running -> reworking -> running
                 -> pausing -> paused -> queued/running
                 -> waiting_approval -> queued/running
                 -> cancelling -> cancelled
                 -> succeeded | failed | blocked
```

Step attempt states:

```text
pending -> ready -> running -> succeeded | failed | blocked | cancelled
pending/ready -> skipped
```

All transitions require the expected `state_version` and `lease_epoch`. A
terminal root has exactly one terminal event; no token or artifact may be
appended afterwards.

## Execution And Quality

For an accepted Skill call, RuntimeEngine first creates a running step attempt
and running child `agent_runs` record. `SkillExecutor` then performs exactly:

```text
validate -> guardrail -> RetrieverPort -> evidence floor -> evidence snapshot
-> ContextBuilder -> ProviderCallJournal(started) -> ProviderPort
-> strict parse -> output guardrail -> CandidateOutput
```

Real execution is fail-closed. It never substitutes fixture evidence, a fixture
provider, default output fields, an accepted quality result, or a successful
artifact after a failed durable write. Prompt text, secrets, provider reasoning
and full model output are never placed in events or logs.

`QualityCheck` is an explicit `outcome_evaluator.QualityCheck` Workflow node
with its own step attempt and child `agent_runs` record. It consumes a Candidate
Output and EvidenceRefs, returns structured accept/defect data, and routes to
Artifact Saga or bounded deterministic rework. It never runs recursively from
SkillExecutor.

## Capability Categories

| Category | Owner | Examples | Model-selectable |
| --- | --- | --- | --- |
| Runtime Port | Runtime / SkillExecutor | Retriever, Provider, RunRecorder, EvidenceSnapshotStore, ProviderCallStore, ArtifactStore, CheckpointStore | No |
| Workflow Action | RuntimeEngine from definition | UpdateProfile, UpdateCapability, PersistLearningPath, PersistGeneratedResource | No |
| Model Tool | ToolRegistry and PolicyEngine | schema-authorised low-risk tools only | Explicit ALLOW/ASK/DENY |

Runtime ports and actions must never be registered as model tools. Production
Agents receive no arbitrary shell, filesystem, or browser tool.

## Modes And Providers

Only `fixture` and `real` modes exist. Fixture is isolated from real persistence
and is only selected explicitly. Real uses true RAG and a real provider; a
fallback is a transparent real-to-real Provider Policy, not a third mode and
never fixture. Root stores requested provider/model; provider calls, child runs
and artifacts store actual provider/model.

Every provider request is journaled before I/O as `started`, then becomes
`completed` with an outcome or `unknown`. A started request after a crash is
unknown unless the upstream result is confirmed. Unknown calls block or await
explicit approved retry, which creates a new attempt. SecureHub does not claim
external-provider exactly-once.

Each stream carries `provider_call_id`, `stream_attempt`, step attempt and event
sequence. After visible tokens, a provider fallback must emit a trace replacement
instruction and start a replacement draft; output from different providers is
never concatenated.

## Events And SSE

The public event vocabulary is exactly:

```text
progress / evidence / token / artifact / trace / done / error
```

`EventEnvelope(workflow_run_id, sequence, event_type, payload)` is the only
serializer contract. Sequence is allocated by atomic increment of
`workflow_runs.next_event_sequence`; `MAX(sequence)+1` is forbidden.

SSE first replays PostgreSQL events after `Last-Event-ID`, then listens to
Redis. A live sequence gap is filled from PostgreSQL before later events are
sent. Duplicate `(run_id, sequence)` is ignored. A disconnect never cancels a
durable run.

## Durable Control Plane

`workflow_runs`, `workflow_step_attempts`, `workflow_events`, checkpoints,
evidence snapshots, provider calls, child `agent_runs` and artifact metadata
are durable. State transition plus event append happens in one transaction.
`workflow_events` is an outbox: a publisher claims unpublished rows with
database locking, emits Redis, then records publication. Publishing may repeat;
fact records do not disappear.

Workers scan PostgreSQL queued/recoverable roots even when Redis is absent.
Claim increments `lease_epoch`; all root, step, checkpoint, retry/rework and
terminal writes compare epoch and state version. A stale worker that updates zero
rows is fenced and stops.

## Artifact Saga And Versioning

Artifact storage statuses are only `staging`, `active`, `orphaned`, `deleted`.
The Saga uploads staging, verifies checksum, commits DB resource metadata, then
activates metadata and makes the artifact event publish-ready. Recovery resumes
staging activation; cleanup tombstones orphaned objects rather than deleting the
audit record.

Every root/checkpoint fixes workflow definition digest, catalog version,
provider policy version, checkpoint schema version and runtime build SHA. Every
skill step also fixes skill version/digest and prompt version/digest. Resume is
`compatible`, explicitly `migratable`, or `incompatible`; it never silently
uses newer workflow/skill/prompt/provider policy.

## API And Ownership

`workflow_runs.id` is the only public root ID. `agent_runs.id` is a child Skill
call only. Start uses `Idempotency-Key`; duplicate start returns the same root.
All query, SSE and controls enforce root ownership. Product endpoints only map
DTO/auth to `WorkflowApplicationService`; they may not import a Skill, create an
async queue/task, generate a random root ID, or inject fixture business data.

## Migration And Rollback

Migrations are additive. A workflow feature flag controls cutover by root, not
random users. During transition `workflow_events` is the only outward event
source. Downgrade is supported for empty/test databases; production rollback
uses forward-compatible code and feature flags, preserving provider-call and
artifact audit history. A stopped worker is replaced through lease expiry and a
new fencing epoch.

## Wave 4-6 Control Plane Amendments

### Typed Collaboration And Fan-out

`TypedWorkflowState` is checkpointed as typed node records, not an unbounded
conversation transcript. A node may see only the `input_sources` declared by
its `WorkflowDefinition`. `EvidenceRef` contains snapshot and provenance
identity; `ArtifactRef` contains resource, version and lineage identity. The
full course workflow fans out document, PPT, quiz and lab resources, then
rejoins at one explicit QualityCheck node. PostgreSQL branches use independent
sessions and the shared fenced root lease; SQLite is intentionally sequential
because it is a disposable/test backend, not the concurrent worker authority.

QualityCheck normalises `evidence_missing`, `fact_conflict`,
`schema_invalid`, `instructional_mismatch`, `citation_mismatch` and
`safety_violation`. Defect routing is deterministic, rework is bounded by the
definition, and a repeated or safety defect blocks the root. Every rework keeps
its previous evidence/artifact lineage rather than overwriting it.

### Provider, Budget And Approval Policy

For `real` roots, Spark is the requested primary chain and DeepSeek is an
explicit real fallback. Every fallback starts a new durable provider call and
stream attempt. A `trace.provider_switch.replace_draft=true` event tells the
client to discard the failed draft; text from two providers is never joined.

Root, node and provider usage is reserved and settled through the durable
budget ledger. Exhaustion blocks before an action/artifact is committed.
Provider policy exposes rate/circuit state without pretending an upstream call
was exactly once. Model tools are evaluated by `PolicyEngine` as `ALLOW`,
`ASK` or `DENY`; ports and Workflow Actions are never model tools. High-risk
actions and unknown provider outcomes create a durable approval record and
audit fact before a user decision can requeue work.

### Recovery, Metrics And Legacy Boundary

Pause/resume only requeues a compatible checkpoint. A version mismatch is
`migratable` only when an explicit checkpoint migration is registered and
persisted; otherwise it is incompatible. Recovery adopts incomplete action
steps and active/staging artifacts by durable identity, preventing duplicate
resource activation after a worker crash.

`GET /workflow-runs/{id}/metrics` reports root statuses, provider outcomes,
unknown calls, outbox lag, trace count and audit count without prompts,
reasoning or model text. `workflow_approvals` and `workflow_audit_logs` are
durable control-plane facts. Production has one RuntimeEngine, StateMachine,
PostgreSQL, `workflow_events`, SkillExecutor and typed collaboration medium;
legacy `RunRegistry`, direct Skill execution, old Harness/graphs and duplicate
SSE serializers are not production authorities.
