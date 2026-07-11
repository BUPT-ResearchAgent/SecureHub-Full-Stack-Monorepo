# Agent Runtime Wave 4-6 Operations

Status: real control-plane implementation; live external gates are credential
dependent.

## Deployment Preconditions

- Run PostgreSQL at Alembic head `20260711_1030`; Redis is a wake-up/fan-out
  projection, not a replacement for PostgreSQL scans, leases or events.
- Set real execution explicitly and inject Spark, DeepSeek, RAG embedding and
  storage credentials through the deployment secret store. Do not put them in
  repository files, smoke output or event payloads.
- Use `mode=fixture` only for rehearsal/CI. A `mode=real` request must fail
  closed when RAG or a Provider is unavailable and must not route to fixture.
- Use PostgreSQL for multi-worker and fan-out deployment. SQLite is supported
  for migrations/unit tests and deterministic local sequential execution only;
  it is not a concurrent worker deployment target.

## Rollout And Migration

1. Drain or fence old workers, then run `alembic upgrade head`.
2. Confirm head `20260711_1030`, catalog `9 agents / 28 skills`, one
   `RuntimeEngine`, and one public `workflow_events` serializer.
3. Start worker, outbox publisher and artifact recovery loop. PostgreSQL scans
   recover queued/expired roots even if Redis is empty or duplicated.
4. Verify `GET /workflow-runs/{id}/metrics` has no unexpected unpublished
   outbox backlog and inspect `workflow_audit_logs` for control actions.

For an empty/test database the supported proof is:

```text
upgrade head -> downgrade 20260611_0960 -> upgrade head
```

Production rollback is forward-compatible: keep provider-call, approval,
artifact and audit facts, gate the new workflow by root, and deploy a compatible
reader rather than deleting durable history.

## Recovery Runbook

- A stale worker loses its `lease_epoch`; it must stop after a fenced write.
  A new PostgreSQL claimant resumes from the latest checkpoint.
- Resume only a compatible or explicitly migrated checkpoint. Do not modify
  checkpoint JSON by hand. Unknown provider outcomes remain `waiting_approval`
  until an explicit retry or approval creates a later attempt.
- Artifact recovery may promote a matching staging object or reuse an active
  resource; it must not publish a new artifact event or create a duplicate
  resource lineage.
- SSE starts with durable replay after `Last-Event-ID`; on a Redis live gap,
  fetch the missing PostgreSQL range before rendering later frames. A terminal
  `done`/terminal `error` forbids subsequent token/artifact events.
- Pause is cooperative. Wait for `paused` before resume; cancel is terminal
  and must leave no later visible token/artifact.

## Alerts And Audit

Alert on growing `outbox_unpublished`/`outbox_lag_seconds`, unknown provider
calls, open provider circuit, repeated QualityCheck defects, budget exhaustion,
artifact activation failures and approval backlog. Query per-root metrics and
audit records by root UUID; do not store prompts, credentials, reasoning or
full model output in logs.

High-risk model tools are PolicyEngine `ASK`/`DENY` decisions. Runtime Ports
and Workflow Actions cannot be model tools. Approval decisions are durable,
owned by the root owner and append an audit record.

## Live Gate Boundary

The intended live chain is Spark primary with DeepSeek real fallback. A valid
live acceptance run requires PostgreSQL, RAG evidence, both provider credentials
and storage access. Capture only root UUIDs, event counts, provider-call IDs,
EvidenceRef/ArtifactRef IDs and sanitised errors. A fallback must emit a trace
replacement and a new stream attempt; client text from two providers must never
be concatenated.

The local 2026-07-11 environment had real execution disabled, missing provider
and embedding credentials, an unauthenticated PostgreSQL configuration and a
blocked COS account. Those conditions are external gates, not fixture fallback
permission. See `Workout/Agent-Runtime-Wave-4-6.md` for exact validation
evidence and pending gates.
