# Agent Run API Contract v0.1

> Status: **partial-real** — Agent-Run-1 provides a fixed Harness-backed
> fixture workflow with in-memory run state and buffered SSE. It does not add
> a `workflow_runs` table or claim a fixture execution is a real LLM run.

## 1. Scope

This API controls **workflow runs**, not agent definitions. SecureHub keeps the
same nine fixed business agents:

`policy_interpreter` · `hot_analyst` · `job_analyst` ·
`competition_advisor` · `career_planner` · `topic_explorer` ·
`doc_archivist` · `task_orchestrator` · `outcome_evaluator`.

Clients cannot create, delete, rename, or dynamically compose agents through
this API. Agent-Run-1 supports exactly one sequential workflow:

```text
course_learning_minimal
  -> career_planner.BuildLearningPersona
  -> task_orchestrator.GenerateLearningPath
  -> doc_archivist.GenerateCourseDoc
  -> competition_advisor.GenerateQuiz
  -> outcome_evaluator.QualityCheck
```

Each node runs through the existing Harness with evidence retrieval, the
evidence floor, safety/quality processing, and child trace logging hooks.

## 2. Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/agents/manifest` | Return the fixed nine-agent manifest only. |
| `POST` | `/api/v1/workflow-runs` | Start `course_learning_minimal`. |
| `GET` | `/api/v1/workflow-runs/{run_id}` | Read current run and child-node state. |
| `GET` | `/api/v1/workflow-runs/{run_id}/events` | Consume buffered `text/event-stream` events. |
| `POST` | `/api/v1/workflow-runs/{run_id}/cancel` | Request cooperative cancellation. |

### 2.1 `GET /agents/manifest`

```json
{
  "total": 9,
  "agents": [
    {
      "name": "career_planner",
      "role_description": "...",
      "capability_vector": [0.0],
      "tools": ["rag.retrieve", "llm.xfyun"],
      "risk_level": "high",
      "skills": ["BuildLearningPersona"]
    }
  ]
}
```

### 2.2 `POST /workflow-runs`

Agent-Run-1 accepts explicit fixture execution. `real` is recognized as a
mode request but currently returns `503 PROVIDER_UNAVAILABLE` rather than
silently falling back to fixture.

```json
{
  "workflow": "course_learning_minimal",
  "user_id": "00000000-0000-0000-0000-000000000001",
  "course_id": "course-websec",
  "topic": "SQL 注入",
  "goal": "为初学者生成 SQL 注入学习路径和入门资源",
  "mode": "fixture",
  "provider": "fixture",
  "stream": true
}
```

Successful creation returns `202 Accepted`:

```json
{
  "run_id": "00000000-0000-0000-0000-000000000701",
  "workflow": "course_learning_minimal",
  "status": "queued",
  "events_url": "/api/v1/workflow-runs/00000000-0000-0000-0000-000000000701/events",
  "cancel_url": "/api/v1/workflow-runs/00000000-0000-0000-0000-000000000701/cancel",
  "mode": "fixture",
  "provider": "fixture",
  "model": "fixture-canned"
}
```

### 2.3 `GET /workflow-runs/{run_id}`

The response exposes root state and child trace metadata. Fixture child traces
use `persistence="registry"`; a future real mode must use
`persistence="agent_runs"` only after the child record is written.

```json
{
  "run_id": "00000000-0000-0000-0000-000000000701",
  "workflow": "course_learning_minimal",
  "status": "succeeded",
  "mode": "fixture",
  "provider": "fixture",
  "model": "fixture-canned",
  "cancel_requested": false,
  "child_run_count": 5,
  "child_runs": [
    {
      "node_id": "build_learning_persona",
      "agent_name": "career_planner",
      "skill_name": "BuildLearningPersona",
      "status": "succeeded",
      "persistence": "registry"
    }
  ]
}
```

## 3. State Machine

```text
queued -> running -> succeeded
                 -> failed
                 -> blocked
                 -> cancelling -> cancelled
```

Child node states are `pending`, `running`, `succeeded`, `failed`, `skipped`,
and `cancelled`. A cancelled run preserves completed child traces, marks a
currently active child `cancelled`, and marks not-yet-started children
`skipped`.

## 4. SSE

`GET /workflow-runs/{run_id}/events` returns `text/event-stream`. The event
set is fixed and must remain exactly:

```text
progress / evidence / token / artifact / trace / done / error
```

| Event | Required payload fields |
|---|---|
| `progress` | `workflow_run_id`, `node_id`, `agent_name`, `skill_name`, `status`, `percentage`, `mode`, `provider` |
| `evidence` | `workflow_run_id`, `node_id`, `agent_name`, `skill_name`, `chunks: EvidenceChunkDTO[]`; each chunk follows `evidence-contract.md` v1.2 and has no free `metadata` fallback |
| `token` | `workflow_run_id`, `node_id`, `agent_name`, `skill_name`, `content`, `mode`, `provider` |
| `artifact` | `workflow_run_id`, `node_id`, `agent_name`, `skill_name`, `resource_id`, `resource_type`, `object_key`, `title` |
| `trace` | `workflow_run_id`, `node_id`, `agent_run_id`, `agent_name`, `skill_name`, `status`, `duration_ms`, `quality_score` |
| `done` | `workflow_run_id`, `status`, `final_output_ref`, `child_run_count`, `quality_score` |
| `error` | `workflow_run_id`, `code`, `message`, `recoverable` |

Fixture execution emits `progress`, `evidence`, `trace`, and terminal `done`
events. It intentionally does not pretend to stream real `token` output or
persist a real `artifact`. A future real generation mode must emit `token` and
`artifact` only while its cancellation token remains unset.

## 5. Mode, Provider, and Fallback Labels

| Label | Meaning | Agent-Run-1 behavior |
|---|---|---|
| `fixture` | Deterministic Harness-injected evidence and LLM output; no provider call and no durable child `agent_runs` claim | Supported. Always returns `mode="fixture"`, `provider="fixture"`, `model="fixture-canned"`. **Fixture must never be labeled `real`.** |
| `real` | A configured LLM provider plus real RAG evidence floor and durable `agent_runs` logging | Reserved for Agent-Run-2. This endpoint rejects it explicitly; it never silently becomes fixture. |
| `fallback` | A declared provider fallback after a real-path failure | Not emitted by Agent-Run-1. If enabled later, it must be explicit in every status/SSE payload and never presented as `real`. |

## 6. Cancellation

`POST /workflow-runs/{run_id}/cancel` sets a cooperative cancellation token.
It returns `cancelling` immediately for active runs and does not kill a process
or terminate a thread. The runner checks the token before every node and before
any future token/artifact emission. The final status is queryable through the
status endpoint and the event stream finishes with `done` and
`status="cancelled"`.

Error codes are `RUN_NOT_FOUND`, `RUN_NOT_ACTIVE`, `INVALID_WORKFLOW`,
`INSUFFICIENT_EVIDENCE`, `PROVIDER_UNAVAILABLE`, `QUALITY_REJECTED`, and
`RUN_CANCELLED` when their corresponding runtime path is enabled.

## 7. Persistence Boundary

The active RunRegistry is process-local and deliberately has no restart
recovery. Each run owns one buffered event queue for its SSE consumer.
Agent-Run-1 does not add a migration. Fixture traces satisfy the development/test
observability contract only; they are not evidence of a real `agent_runs` write.
Before real mode is enabled, every real child skill must write `agent_runs` with
a stable `workflow_run_id` in its summaries, then report
`persistence="agent_runs"`.
