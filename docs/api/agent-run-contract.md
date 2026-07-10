# Agent Run API Contract v0.3

## Scope

This API controls instances of the fixed `course_learning_minimal` workflow. It
does not dynamically create, delete, rename, or register agents. The manifest
always exposes the same nine business agents; Harness, RAG, storage, registry,
and SSE are cross-cutting infrastructure, not agents.

The fixed workflow order is:

```text
career_planner.BuildLearningPersona
  -> task_orchestrator.GenerateLearningPath
  -> doc_archivist.GenerateCourseDoc
  -> competition_advisor.GenerateQuiz
  -> outcome_evaluator.QualityCheck
```

## Endpoints

### `GET /api/v1/agents/manifest`

Returns the fixed nine-agent manifest.

```json
{
  "total": 9,
  "agents": [{"name": "career_planner", "skills": ["BuildLearningPersona"]}]
}
```

### `POST /api/v1/workflow-runs`

Starts only `course_learning_minimal` and returns `202 Accepted`.

```json
{
  "workflow": "course_learning_minimal",
  "user_id": "uuid",
  "course_id": "course-websec",
  "topic": "SQL 注入",
  "goal": "生成证据驱动学习闭环",
  "mode": "fixture",
  "provider": "fixture",
  "stream": true
}
```

The response contains `run_id`, `events_url`, `cancel_url`, `status`, `mode`,
`provider`, and `model`.

`mode=real` requires the explicit pair `provider=deepseek`. Other providers
return `422 INVALID_PROVIDER`. Before creating a real run, the server checks:

- `AGENT_RUN_REAL_ENABLED=true`; otherwise `503 REAL_MODE_DISABLED`.
- `user_id` is a UUID and the database contains that user plus all five fixed
  `(agent_name, skill_name)` seed pairs; invalid UUIDs return
  `422 INVALID_USER_ID`, while database or seed failures return
  `503 REAL_PREREQUISITES_UNAVAILABLE`.
- an actual DeepSeek provider can be constructed; a development fixture fallback
  is rejected as `503 PROVIDER_UNAVAILABLE`.
- active real runs are below `AGENT_RUN_REAL_MAX_CONCURRENCY`; otherwise
  `429 REAL_CONCURRENCY_LIMIT`.

The safe repository default is `AGENT_RUN_REAL_ENABLED=false` and real
concurrency `1`. `AGENT_RUN_REAL_MAX_TOKENS` bounds one provider call. Set
these non-secret fields in the server process environment; do not place any
secret in requests or source files.

The database/seed preflight runs before constructing the DeepSeek provider and
before creating an in-memory run. It verifies only identity and fixed seed
prerequisites; dynamic RAG evidence remains a workflow-time check and can still
produce `INSUFFICIENT_EVIDENCE` without a provider call.

### `GET /api/v1/workflow-runs/{run_id}`

Returns root status and five child traces. A child trace includes
`agent_name`, `skill_name`, `status`, `agent_run_id`, `persistence`, timing,
quality, and evidence count. `persistence="registry"` means non-durable
fixture trace; `persistence="agent_runs"` is emitted only after its database
row has been committed.

### `GET /api/v1/workflow-runs/{run_id}/events`

Returns `text/event-stream`. Each payload has a positive, per-run monotonically
increasing `event_id`; SSE also emits the same value in the standard `id:`
field. Resume after a delivered event with either:

```text
Last-Event-ID: 42
```

or:

```text
GET .../events?after_event_id=42
```

When both are supplied they must match. The endpoint replays retained events
strictly after the cursor, then continues with a private subscriber queue.
Two active subscribers receive the same events; one reader never destructively
consumes another reader's queue.

Events are held in a bounded in-process history
(`AGENT_RUN_EVENT_HISTORY_LIMIT`, default `2048`) and terminal, unsubscribed
runs are lazily pruned by registry cleanup after
`AGENT_RUN_COMPLETED_TTL_SECONDS` (default `3600`). A completed run can be
replayed in full while its history remains retained.
Slow subscribers can detect a retained-history gap with `event_id`. This is a
single-process facility: a process restart does not restore runs or events.

### `POST /api/v1/workflow-runs/{run_id}/cancel`

Requests cooperative cancellation. Active runs become `cancelling` immediately
and converge to `cancelled`; terminal runs return `409 RUN_NOT_ACTIVE`. The
workflow never kills a process or force-terminates a thread. It checks the
cancellation token before each node and before forwarding each streamed token.
Completed child traces remain, the current node becomes `cancelled`, and
unstarted nodes become `skipped`. After cancellation no new `token` or
`artifact` event is forwarded.

## State Machine

```text
queued -> running -> succeeded
                  -> failed
                  -> blocked
queued/running -> cancelling -> cancelled
```

`blocked` is used for evidence-floor refusal and business quality rejection.
All terminal states remain queryable through the status endpoint until
in-memory TTL cleanup.

## SSE Payloads

The event vocabulary is fixed to exactly seven types:

| Event | Meaning |
| --- | --- |
| `progress` | node lifecycle and percentage |
| `evidence` | normalized retrieved evidence cards |
| `token` | streamed real DeepSeek token fragment |
| `artifact` | only a successfully persisted generated resource |
| `trace` | child execution trace with `agent_run_id` |
| `done` | successful or cancelled workflow terminal state |
| `error` | explicit failed or blocked terminal/error state |

`event_id` is a payload field and SSE cursor, not an eighth event type. All
workflow events carry `workflow_run_id`, `mode`, `provider`, and `model`; node
events additionally carry `node_id`, `agent_name`, and `skill_name`.

Current Agent-Run-2 does not persist `generated_resources`, so it correctly
emits no `artifact` events. A future implementation may emit one only after the
resource database write succeeds.

## Execution Labels

| Label | Provider / model | Persistence | Meaning |
| --- | --- | --- | --- |
| `fixture` | `fixture` / `fixture-canned` | `registry` | deterministic Harness fixtures for tests and demos |
| `real` | `deepseek` / configured actual model | `agent_runs` | strict RAG + DeepSeek + verified child persistence |
| `fallback` | explicit fallback identity | depends on implementation | reserved; Agent-Run-2 does not auto-fallback |

A fixture can never be labelled `real`. A real failure remains a `real` failure
with an explicit error code; it never silently changes to fixture, XFYun, or
another provider.

## Strict Real Path

For every real child node:

1. The strict adapter directly calls `app.rag.retriever.retrieve()`.
2. Fewer than three chunks raises `INSUFFICIENT_EVIDENCE` before the LLM call.
3. The adapter calls only `get_llm_provider("deepseek")` and rejects any
   fixture-provider result.
4. DeepSeek receives a JSON-only instruction. Invalid JSON or schema output is
   `LLM_OUTPUT_INVALID`; provider failure is `PROVIDER_UNAVAILABLE`.
5. Retrieved `evidence_chunk_ids` overwrite any IDs claimed by model output.
6. Harness quality checks run, then `ctx.log_run(...)` persists the supplied
   child `agent_run_id` through `AgentRunService`.
7. The persistence callback injects `input_summary.workflow_run_id`, resolves
   real `users`, `agents`, and `agent_skills` rows, commits the row, and only
   then records `persistence="agent_runs"` and emits the success trace.

If persistence cannot be verified, the root run fails with
`AGENT_RUN_PERSIST_FAILED`; it cannot report `succeeded`.

## Quality Verdict

`outcome_evaluator.QualityCheck` is both a fifth child skill and the root
quality gate. Its execution status and its business verdict are intentionally
separate:

- If the child executes, parses, passes Harness checks, and persists normally,
  its child trace and `agent_runs` row remain `success`.
- If that successful child output has `accept is not True`, the root run becomes
  `blocked`, status returns `error.code="QUALITY_REJECTED"`, and SSE emits a
  terminal `error`. It must not emit `done.status="succeeded"`.
- If the child itself fails RAG, provider, JSON, or persistence handling, the
  normal `INSUFFICIENT_EVIDENCE`, `PROVIDER_UNAVAILABLE`,
  `LLM_OUTPUT_INVALID`, or `AGENT_RUN_PERSIST_FAILED` path applies instead of
  `QUALITY_REJECTED`.

## Known Limits

- No `workflow_runs` table, Redis, migration, restart recovery, or distributed
  coordination is introduced in this version.
- Cancellation cannot guarantee that an already-issued remote HTTP request is
  instantly aborted, but later stream chunks are not forwarded and a cancelled
  root run is never rewritten as `succeeded`.
- Real live smoke is manual only. CI uses fixture or fake providers and must not
  send DeepSeek requests.
