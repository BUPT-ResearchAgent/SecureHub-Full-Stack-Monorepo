# SecureHub Workflow Run Contract v1.1

> Status: implemented and frozen through Wave 6. This contract supersedes the event-envelope and
> durable-run portions of the legacy Agent Run v0.4 contract. It does not
> authorize a second runtime, event store, or fixture fallback path.

## Scope and Authority

- `workflow_runs.id` is the only public root `run_id`. `agent_runs.id` is a
  child execution identifier and must never be substituted for the root ID.
- `RuntimeEngine` is the sole production execution authority. Product routes
  are DTO/auth adapters over `WorkflowApplicationService`.
- PostgreSQL `workflow_events` is the event source of truth and transactional
  outbox. Redis is a rebuildable fan-out projection only.
- The external SSE vocabulary is exactly `progress`, `evidence`, `token`,
  `artifact`, `trace`, `done`, and `error`. `sequence` is a cursor, not an
  eighth event type.
- `mode` is only `real` or `fixture`. A `real` run may switch only to a declared
  real provider; it must never become fixture after a provider failure.

## Root Control API

### Start

`POST /api/v1/workflow-runs`

The request must carry an `Idempotency-Key`. Repeating the same key for the
same owner and request returns the existing root instead of creating another.

```json
{
  "workflow": "resource_generate_v1",
  "user_id": "00000000-0000-0000-0000-000000000001",
  "course_id": "00000000-0000-0000-0000-000000000101",
  "input": {
    "resource_type": "doc",
    "kp_id": "00000000-0000-0000-0000-000000000201"
  },
  "mode": "real",
    "provider": "xfyun",
    "model": "spark",
  "stream": true
}
```

`provider` and `model` express the requested policy identity. The server records
the actual provider/model per provider call and may return those actual values
without rewriting the request identity.

```json
{
  "run_id": "00000000-0000-0000-0000-000000000301",
  "workflow": "resource_generate_v1",
  "status": "queued",
  "events_url": "/api/v1/workflow-runs/00000000-0000-0000-0000-000000000301/events",
  "cancel_url": "/api/v1/workflow-runs/00000000-0000-0000-0000-000000000301/cancel",
  "mode": "real",
  "requested_provider": "xfyun",
  "requested_model": "spark",
  "actual_provider": "xfyun",
  "actual_model": "spark"
}
```

Legacy top-level input fields remain accepted only for Agent Run compatibility.
New clients send product input under `input`.

### Query and Control

- `GET /api/v1/workflow-runs/{run_id}` returns the root, actual/requested
  provider identity, child node/attempt state, safe final-output reference, and
  terminal error when present.
- `POST /api/v1/workflow-runs/{run_id}/cancel`
- `POST /api/v1/workflow-runs/{run_id}/pause`
- `POST /api/v1/workflow-runs/{run_id}/resume`
- `POST /api/v1/workflow-runs/{run_id}/retry`
- `POST /api/v1/workflow-runs/{run_id}/approvals/{approval_id}` with
  `{ "approved": true|false, "decision": { ... } }`
- `GET /api/v1/workflow-runs/{run_id}/metrics`

All controls enforce root ownership. `cancel` is explicitly requested control;
an SSE disconnect, browser refresh, or subscription disposal never cancels a
durable run.

Root statuses are `queued`, `running`, `reworking`, `pausing`, `paused`,
`waiting_approval`, `cancelling`, `cancelled`, `succeeded`, `failed`, and
`blocked`. Node statuses are `pending`, `ready`, `running`, `succeeded`,
`failed`, `blocked`, `cancelled`, and `skipped`.

`pause` is cooperative: a worker converges `pausing -> paused` at a durable
boundary. `resume` requires a compatible checkpoint and moves `paused ->
queued`; an explicit registered checkpoint migration may make a root
`migratable`, while an unregistered mismatch is rejected. `retry` is reserved
for a root waiting on an unknown provider outcome and creates a later provider
attempt rather than replaying the opaque request. A high-risk action uses the
approval endpoint; rejection terminally blocks the root. Start may include a
`budget` object; exhausted root/node/provider limits block work before a new
provider/action side effect.

## Event Stream and Replay

`GET /api/v1/workflow-runs/{run_id}/events`

The server verifies ownership, replays PostgreSQL events with
`sequence > Last-Event-ID`, then follows live fan-out. Clients use the standard
header and retain it locally per root:

```text
Last-Event-ID: 42
```

For rollout compatibility, the server accepts `after_sequence=42` and the
legacy `after_event_id=42` when they agree. A client repairing a live gap may
also request `until_sequence=49`; the gateway returns the contiguous durable
range through that cursor and must not skip an unpublished artifact event.

Every frame has both SSE `id:` and JSON `sequence`:

```text
id: 43
event: token
data: {"workflow_run_id":"00000000-0000-0000-0000-000000000301","sequence":43,"event_type":"token","payload":{"content":"...","step_attempt_id":"00000000-0000-0000-0000-000000000302","provider_call_id":"00000000-0000-0000-0000-000000000303","stream_attempt":1}}
```

Canonical `EventEnvelope` fields:

| Field | Requirement |
| --- | --- |
| `workflow_run_id` | Required root UUID; equals the control API `run_id`. |
| `sequence` | Required positive, gap-free per-root monotonic integer. |
| `event_type` | One of the seven fixed external types. |
| `payload` | Typed event payload below. |
| `created_at` | Optional ISO 8601 event creation time. |
| `mode` | Optional `real` or `fixture`; when present it is the root execution mode. |
| `requested_provider` / `requested_model` | Optional root request identity. |
| `actual_provider` / `actual_model` | Optional actual identity for the event/call. |
| `step_attempt_id`, `agent_run_id`, `provider_call_id`, `stream_attempt` | Correlation IDs. They may also be repeated in `payload` during the migration window. |

The frontend deduplicates by `(workflow_run_id, sequence)`. On a live sequence
gap it fetches the missing durable range before rendering the later event. A
duplicate Redis publish may therefore be visible in transport logs but never
twice in the UI reducer.

## Typed Payloads

| Event | Required payload semantics |
| --- | --- |
| `progress` | Root or node state change. Node updates include `node_id`, optional agent/skill identity, node status, and optional percentage. |
| `evidence` | `{ "items": [EvidenceChunkDTO], "evidence_snapshot_ids": [...] }`; emitted after real retrieval/snapshot and before related tokens. |
| `token` | `content` plus `step_attempt_id`, `provider_call_id`, and `stream_attempt` for every provider stream. |
| `artifact` | Persisted artifact only: `resource_id`, `resource_type`, `title`, and optional object key. When `storage_status` is present it must be `active`; staging/orphaned/deleted objects are not externally published. |
| `trace` | Child execution trace with agent/skill, node/attempt correlation, and actual provider/model where relevant. Provider fallback is represented here, never as a new SSE type. |
| `done` | Terminal `succeeded` or `cancelled`, safe final-output reference, and optional quality score. |
| `error` | Error taxonomy code/message, optional `recoverable`, and terminal `failed` or `blocked` status when terminal. |

`done` and terminal `error` are mutually exclusive. Once either is committed,
the publisher and gateway must not emit later `token` or `artifact` events for
the root.

### Provider Stream Replacement

When a provider fails after visible text, the old and new provider text must not
be concatenated. The runtime terminates the old attempt, emits a `trace` payload
such as:

```json
{
  "step_attempt_id": "00000000-0000-0000-0000-000000000302",
  "provider_switch": {
    "from_provider": "xfyun",
    "to_provider": "deepseek",
    "reason": "PROVIDER_UNAVAILABLE",
    "replace_draft": true
  }
}
```

The next token stream has a new `provider_call_id` / `stream_attempt` and may
also set `replace_draft: true`. Clients discard the old step-attempt draft and
render only the replacement stream. Unknown or stale stream tokens remain in
the durable audit trail but are not appended to the visible draft.

## Product Adapter Compatibility

The following routes remain public compatibility adapters. They must create the
same root UUID through `WorkflowApplicationService`; they do not import a Skill,
create an in-memory queue, fabricate evidence/artifacts, or generate a random
unqueryable run ID.

| Product route | Workflow | Compatibility behavior |
| --- | --- | --- |
| `POST /api/v1/profile/chat` | `profile_build_v1` | SSE after root commit. |
| `POST /api/v1/courses/{id}/plan` | `course_plan_v1` | Short synchronous wait; on timeout returns `202`, `Location`, and `run_id`. |
| `POST /api/v1/courses/{id}/resources/generate` | `resource_generate_v1` | SSE after root commit. |
| `POST /api/v1/tutor/ask` | `tutor_routing_v1` | SSE after root commit. |
| `POST /api/v1/assessment/run` | `assessment_update_v1` | Short synchronous wait; on timeout returns `202`, `Location`, and `run_id`. |

For adapter SSE responses, `X-Workflow-Run-ID` and `Location` expose the root
immediately. If an intermediary cannot preserve those headers, the first
`progress` envelope must include `workflow_run_id`. Frontend applications use
the root control API and event endpoint for reconnect, replay, status, and
explicit cancel rather than treating the adapter connection as the run itself.

## Safety and Rollout

- Event payloads never contain credentials, full prompts, chain-of-thought,
  or unrestricted model text. Artifact/final output fields are controlled
  references or endpoint-safe DTO projections.
- `real` errors remain real errors. Client code does not replay fixture evidence
  or fixture output after network, provider, parse, quality, or persistence
  failure.
- Fixture replay is allowed only under explicit PresenterMode/fixture mode and
  is visibly segregated from real roots.
- During migration, clients tolerate legacy flat `event` / `event_id` frames
  only to replay retained history. New server emission uses this envelope.

## Wave 4-6 Additions

The existing seven event names remain exhaustive. New semantics are carried in
their typed payloads: `trace.provider_switch` and replacement token attempts,
QualityCheck defects/rework lineage, approval IDs, budget/policy errors,
typed `evidence_refs`, and typed `artifact_refs`. `artifact` remains visible
only after activation. Envelope mode and requested provider are root facts;
actual provider/model is an attempt fact and is never silently rewritten to a
fixture provider.

The client reducer stores cursors per root, deduplicates sequence tuples,
repairs live gaps with durable replay and replaces a displayed draft only when
the replacement trace/token flag is present. It must not concatenate draft text
across provider calls.
