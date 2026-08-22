# Step 10: Deploy, environment docs, and integration smoke

## Goal

Document all required environment variable names for Railway, Vercel, and local dev without secret values in git. Deploy the Study API to the existing Railway `api` service. Update runbooks. Add an integration smoke test script or pytest module that hits `/health` and one authenticated participant path. Confirm `TRACE_EXPORT_ENABLED` is false in production documentation.

## Files to inspect

- `/workspace/docs/runbooks/setup/HOW_TO_SETUP_APP.md`
- `/workspace/docs/runbooks/HOW_TO_RUN_APP.md`
- `/workspace/backend/railway.toml`
- `/workspace/backend/README.md`
- `/workspace/INSTRUCTIONS_TO_BUILD_BACKEND.md`

## Files allowed to change (closed set)

- `/workspace/backend/README.md`
- `/workspace/backend/.env.example`
- `/workspace/ui/.env.example`
- `/workspace/docs/runbooks/setup/HOW_TO_SETUP_APP.md` (env var table only, no secret values)
- `/workspace/docs/runbooks/HOW_TO_RUN_APP.md` (local dev with Study API URL)
- `/workspace/docs/runbooks/deploy/STUDY_API_ENV.md` (create)
- `/workspace/backend/tests/test_integration_smoke.py`
- `/workspace/scripts/smoke_study_api.sh` (create)
- `/workspace/backend/railway.toml` (start command or healthcheck only if required)

## Files forbidden to change

- `/workspace/backend/app/api/**` (behavior frozen unless smoke reveals bug, then fix in owning step file)
- `/workspace/ui/src/**` (except `.env.example` already listed)
- `/workspace/supabase/migrations/**`
- `/workspace/strategy_planning/**`

## Contracts / acceptance checks

Environment variable names are documented below. Values are never committed.

| Variable | Host | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | Railway API | Study Postgres connection string |
| `STORAGE_MODE` | Railway API | `postgres` in production |
| `OPENAI_API_KEY` | Railway API | Text and Realtime |
| `INTERNAL_WORKER_TOKEN` | Railway API and worker | Internal ingest auth |
| `TRACE_EXPORT_ENABLED` | Railway API | Default `false` in prod docs |
| `LANGSMITH_TRACING` | Railway API | Default `false` in prod docs |
| `LANGSMITH_API_KEY` | Railway API | Optional until tracing approved |
| `LANGSMITH_PROJECT` | Railway API | Environment-specific project name |
| `PARTICIPANT_UI_ORIGINS` | Railway API | Vercel production, preview, and localhost origins |
| `PARTICIPANT_COOKIE_SECRET` | Railway API | Sign participant capability cookies |
| `INVITATION_TOKEN_PEPPER` | Railway API | Hash invitations |
| `NEXT_PUBLIC_STUDY_API_ORIGIN` | Vercel UI | Public Study API origin the browser calls |
| `NEXT_PUBLIC_SUPABASE_URL` | Vercel UI | Staff auth later |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Vercel UI | Staff auth later |

Variable names match `strategy_planning/CREDENTIALS_AND_SETUP.md`. Do not commit secret values.

Deploy checks are as follows.

- `GET https://api-production-198a.up.railway.app/health` returns `status` ok (or current Railway URL from runbook).
- `GET /ready` returns ok when `STORAGE_MODE=postgres` and database reachable.
- Smoke script exchanges sample invitation token and calls `GET /v1/participant-session` with returned cookie in CI when secrets are available, or skips with message.

Production defaults documented in the runbook are as follows.

- `TRACE_EXPORT_ENABLED=false`
- `LANGSMITH_TRACING=false`
- LangSmith tracing off until written retention policy attached
- No LangGraph services

## Tests to add

| Test | What it locks |
| --- | --- |
| `test_integration_smoke.py::TestHealthEndpoints::test_health_ok` | Liveness |
| `test_integration_smoke.py::TestParticipantSmoke::test_exchange_and_read_session` | End-to-end contract when `SMOKE_BASE_URL` set |
| `scripts/smoke_study_api.sh` | Operator runnable smoke |

## Exact commands to run and expected output

```bash
cd /workspace/backend
uv run pytest tests/ -q
```

You should see all backend tests pass.

```bash
cd /workspace/backend
uv run pytest tests/test_integration_smoke.py -q
```

You should see tests pass or skip with a reason when `SMOKE_BASE_URL` is unset.

```bash
bash /workspace/scripts/smoke_study_api.sh
```

When run against a deployed API with env vars set, you should see output that prints `OK health`, `OK exchange`, and `OK session read`, with exit code 0.

Railway deploy is run by the orchestrator, not necessarily by this subagent.

```bash
cd /workspace
railway up ./backend --path-as-root --service api --environment production --detach -m "Study API full implementation"
```

You should see the command return a deployment id without error. The dashboard should show building then active.

```bash
curl -s https://api-production-198a.up.railway.app/health
```

You should see JSON with `"status":"ok"`.

## Out of scope for this step

- Enabling LangSmith in production
- Creating production invitation batches
- Staff admin product
- Supabase Auth login UI unless already merged separately

## Dependencies

- Steps 1 through 9 complete or explicitly waived with human approval.
- Integration check after Step 8 must be complete before Step 9 started.

## Parallelization

This step runs last after Step 9. No parallel work after this step for the same release.

## What must pass / fail before the step is complete

| Check | Must pass | Must fail |
| --- | --- | --- |
| Full `uv run pytest tests/` | All tests pass | Any failure |
| Production `/health` | 200 ok | 5xx after deploy |
| `.env.example` files in git | Variable names only | Secret values committed |
| Runbook states Supabase as Postgres | Yes | Railway Postgres as primary |
