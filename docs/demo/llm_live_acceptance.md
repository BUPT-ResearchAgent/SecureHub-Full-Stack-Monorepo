# P0.5 LLM Live Test Acceptance

Status: real

## Test Layers

| Layer | Command | API Cost |
| --- | --- | --- |
| Ordinary CI | `uv run pytest -m "not llm_live" -q` | No, fixture only |
| Manual live test | `ENABLE_LLM_LIVE_TESTS=true uv run pytest -m llm_live` | Yes, requires `DEEPSEEK_API_KEY` or `XFYUN_API_KEY` |

Live tests are a manual demo-freeze gate. They are not part of ordinary CI and must not be reported as passed unless a real provider key was present during the run.

## Manual Commands

DeepSeek:

```powershell
cd backend
$env:ENABLE_LLM_LIVE_TESTS="true"
$env:LLM_PROVIDER="deepseek"
$env:DEEPSEEK_API_KEY="***"
$env:MAX_LLM_CALLS_PER_USER_PER_DAY="5"
$env:MAX_TOKENS_PER_REQUEST="1600"
$env:LLM_TIMEOUT_SECONDS="45"
$env:LLM_DAILY_BUDGET_CNY="1.0"
uv run pytest -m llm_live -q
```

讯飞星火:

```powershell
cd backend
$env:ENABLE_LLM_LIVE_TESTS="true"
$env:LLM_PROVIDER="xfyun"
$env:XFYUN_API_KEY="***"
$env:XFYUN_APP_ID="***"
$env:XFYUN_API_SECRET="***"
$env:MAX_LLM_CALLS_PER_USER_PER_DAY="5"
$env:MAX_TOKENS_PER_REQUEST="1600"
$env:LLM_TIMEOUT_SECONDS="45"
$env:LLM_DAILY_BUDGET_CNY="1.0"
uv run pytest -m llm_live -q
```

No-key verification:

```powershell
cd backend
$env:ENABLE_LLM_LIVE_TESTS="false"
uv run pytest tests/llm_live/test_p0_real_llm.py -q
```

Expected result without keys: tests are skipped. Report wording must be "门禁完成，真实调用待有 key 后验证", not "live LLM passed".

## Minimum Live Test Set

| Case | Resource Type | Evidence Required | Persistence |
| --- | --- | --- | --- |
| SQL injection learning path | `learning_path` | >= 3 chunks | `agent_runs` + `generated_resources` |
| SQL injection course doc | `course_doc` | >= 3 chunks | `agent_runs` + `generated_resources` |
| SQL injection quiz set | `quiz_set` | >= 3 chunks | `agent_runs` + `generated_resources` |
| SQL injection tutor QA | `tutor_answer` | >= 3 chunks | `agent_runs` + `generated_resources` |
| Insufficient evidence refusal | none | < 3 chunks | no LLM call, no generated resource |

## Quality Gate

| Check | Required Result |
| --- | --- |
| References evidence | Output includes an evidence marker such as `[E1]` |
| Does not fabricate sources | Output must cite a retrieved `source_url` |
| Contains `source_url` | At least one retrieved source URL appears in output |
| Writes `agent_runs` | Success cases write `status=success` with evidence IDs |
| Writes `generated_resources` | Success cases write one resource row |
| Records provider / model / token | `agent_runs.token_usage` includes provider, model, prompt, completion, total |
| Records cost estimate | `agent_runs.token_usage.cost_estimate` and resource metadata include CNY estimate |

## Cost And Rate Guardrails

| Env Var | Default | Meaning |
| --- | --- | --- |
| `ENABLE_LLM_LIVE_TESTS` | `false` | Live tests are disabled unless explicitly true |
| `MAX_LLM_CALLS_PER_USER_PER_DAY` | `5` | Max live calls in the P0.5 matrix |
| `MAX_TOKENS_PER_REQUEST` | `1600` | Prompt + completion estimate ceiling |
| `LLM_TIMEOUT_SECONDS` | `45` | Per-call timeout |
| `LLM_DAILY_BUDGET_CNY` | `1.0` | Estimated live-test budget ceiling |

## Fixture Fallback When Live Fails

Use fixture mode only for development, CI, and rehearsal when the owner has not approved API spend or provider keys are unavailable:

```powershell
cd backend
$env:ENABLE_LLM_LIVE_TESTS="false"
$env:LLM_PROVIDER="fixture"
uv run pytest -m "not llm_live" -q
```

If a live run fails because of 401, 429, timeout, or provider outage:

1. Keep the failed live output in the run log.
2. Re-run the ordinary fixture suite to verify non-LLM regressions.
3. Mark the live gate as pending with the provider error, budget state, and retry owner.
4. Do not edit tests or fixtures to simulate a live pass.
