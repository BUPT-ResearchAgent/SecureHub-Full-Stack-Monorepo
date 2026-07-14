# Status: real

# Provider Credential Pool

## Status

`real` on `dev`: the personal-center "模型与密钥" tab uses the authenticated
Provider Credentials API for DeepSeek and XFYUN only.

## Security Contract

- `provider_credentials` is separate from `user_profiles` and stores AES-256-GCM ciphertext only.
- Set `PROVIDER_CREDENTIAL_MASTER_KEY` to a 32-byte URL-safe Base64 value in the server's secret manager. It is intentionally absent from `.env.example`.
- Generate a new value outside the repository with:

  ```powershell
  python -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
  ```

- List, logs, errors, SSE, outbox, `agent_runs`, provider journal and browser persistence never contain a plaintext key.
- Only authenticated users can manage credentials. Browser requests have no `user_id`; ownership is derived from the JWT.
- PostgreSQL's partial unique index permits one active key per `(user_id, provider)`. Activation clears the previous selection and enables the target in one transaction.
- Root creation records a nullable `workflow_runs.credential_id`. A worker resolves that immutable ID immediately before the provider request. It never changes global Settings. No selected key keeps the existing server environment-variable fallback; deleting a selected credential leaves the ID intact and makes that root fail closed instead of falling back.

## API

| Method | Route | Result |
| --- | --- | --- |
| GET | `/api/v1/provider-credentials` | Current user's masked credential list |
| POST | `/api/v1/provider-credentials` | Encrypt and save a DeepSeek/XFYUN credential |
| POST | `/api/v1/provider-credentials/{id}/activate` | Transactionally select the active credential |
| POST | `/api/v1/provider-credentials/{id}/deactivate` | Disable the selected credential |
| POST | `/api/v1/provider-credentials/{id}/verify` | Perform a minimal provider call and store only its status/time |
| DELETE | `/api/v1/provider-credentials/{id}` | Delete an owned credential |

Every response exposes only `id`, provider, name, SHA-256 fingerprint, active state, verification status and verification time.

## Migration And Rollback

Apply:

```powershell
cd backend
uv run alembic upgrade head
```

This applies revisions `20260714_1050` and `20260714_1060`, creates `provider_credentials`, its owner/provider/name and active-key constraints, and adds nullable `workflow_runs.credential_id`. The second revision deliberately removes the foreign key so deletion cannot null an already-fixed root ID.

Before rollback, back up `provider_credentials`: downgrade destroys encrypted credentials and removes root provenance. Then run:

```powershell
cd backend
uv run alembic downgrade 20260712_1040
```

## Verification

Automated coverage verifies encryption-at-rest, two-user isolation, active-key switching, frozen root resolution and authentication. A live DeepSeek root requires a user to add and activate an actual DeepSeek key; no live key is supplied by this repository. With no XFYUN credential the page deliberately reports `未配置 · 未验证` and does not claim successful validation.
