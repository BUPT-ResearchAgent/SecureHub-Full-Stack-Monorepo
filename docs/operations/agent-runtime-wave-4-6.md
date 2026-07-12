# Agent Runtime Wave 4-6 Operations

Status: real control-plane implementation. The 2026-07-12 local DeepSeek/RAG/
PostgreSQL gate and an independent COS storage gate passed; Spark
primary/fallback remains credential dependent.

## Deployment Preconditions

- Run PostgreSQL at Alembic head `20260712_1040`; Redis is a wake-up/fan-out
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
2. Confirm head `20260712_1040`, catalog `9 agents / 28 skills`, one
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

## 2026-07-12 Local Live Verification

The host ran healthy compose PostgreSQL/Redis, migrated PostgreSQL to
`20260712_1040`, and seeded the frozen `9 agents / 28 skills` catalog. With
explicit real mode, real DeepSeek and Qwen RAG, and explicit local artifact
storage, the opt-in HTTP smoke completed the five product paths below. Each
root had real provider calls, durable `agent_runs`, ordered PostgreSQL SSE
replay equal to the live stream, and no fixture provider.

| Workflow | Root ID | SSE live / replay | Provider calls |
| --- | --- | ---: | ---: |
| `profile_build_v1` | `0645b4c8-7ef4-4e49-ba93-254fc6ac929e` | 613 / 613 | 2 |
| `course_plan_v1` | `9a9f7a1e-6cbe-4ff1-a036-d8d6292ab9f2` | 2913 / 2913 | 4 |
| `tutor_routing_v1` | `a844064f-af33-437a-beab-0d04dd0fdeef` | 422 / 422 | 3 |
| `assessment_update_v1` | `1ff55bbf-a678-4900-a485-5ad5ececd47b` | 537 / 537 | 4 |
| `resource_generate_v1` | `95b4b716-0a95-46ec-8b55-0ab05ac13900` | 1030 / 1030 | 4 |

`GET /api/v1/llm/health` also returned real
`deepseek / deepseek-v4-pro / available`; the endpoint delegates to the health
service and sanitises provider failures. The live embedding test and a
provenance audit passed with 3,549 ready Qwen-profile chunks and eight sourced
retrieval hits. This is a direct-DeepSeek verification, not a provider fallback
test: all roots had `provider_switches=0`.

A separate direct-DeepSeek cancellation test requested cancellation after its
first observed token for `resource_generate_v1`. Root
`2daf935b-e3b7-4dbe-af34-d792dffc66d3` reached `cancelled`; 12 token events
arrived before cancellation took effect, live/replay SSE both contained 21
events, and the DB audit found one `agent_run` and one provider call. This is a
direct-DeepSeek cancellation result (`provider_switches=0`), not Spark
cancellation or fallback verification.

Spark primary, controlled Spark interruption, real DeepSeek fallback and a
real-token Spark cancellation are still open gates. The resolved Spark bearer
key is empty; provider construction returned sanitised `ProviderUnavailable` /
`XFYUN_PROVIDER_UNAVAILABLE`, so no Spark request was sent. Separately, a real
process-scoped `STORAGE_PROVIDER=cos` smoke completed upload, head, download,
signed URL and delete. COS is therefore no longer an open gate on this
workstation; the product paths above remain correctly labelled as local-storage
paths. The prior `451 UnavailableForLegalReasons` result remains historical
external-blocker evidence rather than a retroactive COS success claim.
See `Workout/Agent-Runtime-Wave-4-6.md` for the exact commands, IDs and
sanitised evidence.

## Validation Policy

Use the standard path in `Workout/Agent-Runtime-Wave-4-6.md` before declaring
an external gate: restore compose dependencies, confirm process-resolved real
settings, isolate storage when needed, probe provider and RAG independently,
then run the opt-in workflow smoke with durable DB/SSE checks. A fixture run,
`AGENT_RUN_REAL_ENABLED=false` refusal, local artifact storage, or
`--expect-fallback` without an observed replacement is insufficient evidence.
Likewise, a direct-DeepSeek cancellation check cannot establish Spark primary,
Spark cancellation or Spark-to-DeepSeek fallback behavior.
Bypass ambient proxies for localhost diagnostics, use disposable SQLite only
for migration round-trips, and count durable `agent_runs` from DB audit rather
than the status API's workflow-step `child_run_count` alias.
