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
