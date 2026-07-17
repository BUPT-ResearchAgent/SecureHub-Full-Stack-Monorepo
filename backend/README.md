# SecureHub Backend

This directory contains the FastAPI backend scaffold for SecureHub.

## Stack

- FastAPI for HTTP APIs
- Uvicorn for local ASGI serving
- pydantic-settings for environment-based configuration
- pytest and FastAPI TestClient for tests
- uv for Python dependency management

## Layout

```text
app/
├─ main.py              # FastAPI app factory and middleware setup
├─ api/                 # Versioned API routers
├─ core/                # Configuration and logging
├─ schemas/             # Pydantic request/response models
├─ services/            # Business orchestration layer
├─ repositories/        # Persistence adapters, added when needed
├─ models/              # Domain or database models, added when needed
└─ deps.py              # Shared FastAPI dependencies
tests/                  # Backend tests
```

## Run

```bash
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

API docs are available at `http://127.0.0.1:8000/docs`.

## Database schema prerequisite

Before starting the API against an existing PostgreSQL database, inspect and
align its Alembic revision from this `backend/` directory:

```powershell
uv run alembic current
uv run alembic upgrade head
```

Run the upgrade only after taking the appropriate database backup and review.
In particular, a `503` response with `REQUEST_AUDIT_REDACTION_FAILED` during
`OPTIONS /api/v1/auth/*` indicates that the API-risk audit tables are not
available to the running application; bring the schema to `head` rather than
disabling the security middleware.

## Demo education relationships

The course, users, and schema must already exist before seeding the real
`WEBSEC-101` teaching relationships:

```powershell
uv run python -m app.db.seeds.seed_education_domain
```

The command is idempotent. It grants only
`demo-course-teacher@securehub.local` the active `owner` assignment for
`WEBSEC-101`, then seeds that teacher's class, the demo student's enrollment,
and its group membership. It deliberately does **not** grant every demo
teacher this course; teachers may govern only courses for which they have an
explicit `course_teacher_assignments` record. Run this command when a teacher
page reports that the current teacher lacks `WEBSEC-101` authorization.

## Controlled WEBSEC-101 showcase course seed

`app.db.seeds.seed_showcase_course` is an explicit, idempotent profile for a
local development database, competition rehearsal, or an explicitly
authorised test database. It writes ordinary course, enrollment, quiz,
assessment, resource, AgentRun/Evidence, and governance records so existing
APIs and permissions consume them normally. It is not a startup seed, is
disabled when `APP_ENV` is `production`, `prod`, or `release`, and must never
be run against production by default.

The `websec-101-showcase-v7` profile includes 32 fictional course aliases and
one existing demo-course learner. Its fixed teaching material and external
references remain labelled as `curated-demo` / `external-preview`; they are
not a claim of live model generation, platform-owned video content, or real
student records.

Before using it, work from this `backend/` directory, run `uv sync --frozen`,
and set `DATABASE_URL` through an approved local/test environment mechanism.
It must point to an explicitly authorised PostgreSQL database whose schema has
already been reviewed and upgraded to the current Alembic head. Do not put a
production URL or credentials in shell history, documentation, or Git.

### Windows PowerShell

```powershell
# Run only after DATABASE_URL targets an authorised local/demo/test database.
uv sync --frozen
uv run alembic upgrade head

# Create or reconcile only the controlled profile.
$env:SECUREHUB_ALLOW_SHOWCASE_SEED='1'
uv run python -m app.db.seeds.seed_showcase_course seed

# Check manifest counts, quality-gated items, relationship chains, and state coverage.
uv run python -m app.db.seeds.seed_showcase_course verify
```

### macOS/Linux shell

```bash
# Run only after DATABASE_URL targets an authorised local/demo/test database.
uv sync --frozen
uv run alembic upgrade head

SECUREHUB_ALLOW_SHOWCASE_SEED=1 uv run python -m app.db.seeds.seed_showcase_course seed
SECUREHUB_ALLOW_SHOWCASE_SEED=1 uv run python -m app.db.seeds.seed_showcase_course verify
```

`verify` must report `valid: True` before a rehearsal. It checks the manifest,
quality-gated items, relationship chains, and coverage states; it does not
substitute for PostgreSQL migration or browser end-to-end checks.

### Upgrade an existing v5/v6 showcase database to v7

For an ordinary upgrade of an already authorised local, competition-demo, or
test PostgreSQL database, run `seed` and then `verify` again from this
`backend/` directory. **Do not run `reset` for this upgrade.** The seed
reconciles its controlled profile by stable IDs and does not use a reset to
remove unrelated workspace data.

```powershell
$env:SECUREHUB_ALLOW_SHOWCASE_SEED='1'
uv run python -m app.db.seeds.seed_showcase_course seed
uv run python -m app.db.seeds.seed_showcase_course verify
```

```bash
export SECUREHUB_ALLOW_SHOWCASE_SEED=1
uv run python -m app.db.seeds.seed_showcase_course seed
uv run python -m app.db.seeds.seed_showcase_course verify
```

v7 adds persistent, frozen 36-question comprehensive-assessment items, an
open submission, personal resources/Evidence, and an `assessment_demo_draft`
for `demo-student@securehub.local`. The course-page “fill all 36 questions”
control only pre-fills that editable draft. A learner must still submit it
explicitly; assessment feedback and the `outcome_evaluator` capability update
remain subject to the real API, Evidence, Provider, and QualityCheck path.
No default score or fixed radar chart is used as a substitute.

The executed Windows local controlled-database run returned
`manifest: websec-101-showcase-v7`, `valid: True`,
`demo_assessment_questions: 36`, and `demo_assessment_drafts: 1`. This is
seed/relationship evidence only; it is not Provider, browser E2E, or
production acceptance. On macOS/Linux, execute the same `seed` and `verify`
commands in the authorised target environment before recording that platform
as validated.

### Profile-scoped reset

Reset is deliberately separate and must never be run in production. After
reviewing the target database, it removes only stable IDs owned by this
profile; the base WEBSEC-101 seed and unrelated workspace data remain.

```powershell
$env:SECUREHUB_ALLOW_SHOWCASE_SEED='1'
uv run python -m app.db.seeds.seed_showcase_course reset
```

```bash
SECUREHUB_ALLOW_SHOWCASE_SEED=1 uv run python -m app.db.seeds.seed_showcase_course reset
```

The command path is intentionally cross-platform: the module is launched by
`uv run python -m ...`, and its bundled lecture is resolved from the project
root with `pathlib`. Windows is the currently executed environment; macOS and
Linux are supported command paths that still require `seed` plus `verify` in
their target environment before they can be called validated there.

## Local password-policy demo accounts

The normal student presentation account,
`demo-student@securehub.local / SecureHub@2026`, is seeded as compliant with
the active password-policy version and should log in normally.  To demonstrate
the deliberate remediation journey in a local development database, enter the
separate account `demo-password-remediation@securehub.local / demo123`
manually.  Its seed state is explicitly policy version `0`; the login endpoint
will reject it until the user supplies a new compliant password through the
password-remediation form.  Do not use this local-only fixture outside a
development/demo environment.

## Test

```bash
uv run pytest
```

## API Prefix

All versioned APIs are mounted under:

```text
/api/v1
```

Current starter endpoints:

```text
GET /api/v1/health
GET /api/v1/system/ping
GET /api/v1/placeholder/modules
```
