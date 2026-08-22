# Issue Discussion Platform — Backend

FastAPI Study API for participant sessions, staff routes, and internal worker ingest.

## Environment variables

Copy `backend/.env.example` to a gitignored `.env` file. See [Study API environment](../docs/runbooks/deploy/STUDY_API_ENV.md) for Railway and Vercel host tables.

| Variable | Purpose |
| --- | --- |
| `STORAGE_MODE` | `memory` (default) for sample contracts, or `postgres` for durable storage |
| `DATABASE_URL` | Supabase Postgres connection string; required when `STORAGE_MODE=postgres` |
| `OPENAI_API_KEY` | OpenAI text and Realtime (server only) |
| `INTERNAL_WORKER_TOKEN` | Shared secret for internal realtime item ingest |
| `PARTICIPANT_UI_ORIGINS` | Comma-separated browser origins (documented name; runtime may read `CORS_ALLOWED_ORIGINS`) |
| `PARTICIPANT_COOKIE_SECRET` | Signs participant capability cookies (documented name; runtime may read `CAPABILITY_SIGNING_SECRET`) |
| `INVITATION_TOKEN_PEPPER` | Pepper for invitation token hashes |
| `SUPABASE_URL` | Supabase project URL for staff auth |
| `SUPABASE_JWT_SECRET` | Verify forwarded Supabase staff JWTs on `/v1/staff/*` |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only Supabase admin key |
| `STUDY_API_ROLE` | `api` enables Postgres checks on `/ready` |
| `RAILWAY_GIT_COMMIT_SHA` | Optional deploy commit SHA on `GET /health` |
| `TRACE_EXPORT_ENABLED` | Default **`false`**; application switch for LangSmith export |
| `LANGSMITH_TRACING` | Default **`false`**; LangSmith SDK tracing |
| `LANGSMITH_API_KEY` | Optional until tracing is approved |
| `LANGSMITH_PROJECT` | Environment-specific LangSmith project name |
| `LANGSMITH_WORKSPACE_ID` | Optional; only if your LangSmith key requires it |

## Local development

```bash
cd backend
uv sync
uv run fastapi dev app/main.py --port 8000
```

In-memory sample mode needs no `DATABASE_URL`. Point the UI at `http://127.0.0.1:8000` with `NEXT_PUBLIC_STUDY_API_ORIGIN`.

## Tests

```bash
cd backend
uv run pytest -q
```

Deployed integration smoke (skips without `SMOKE_BASE_URL`):

```bash
uv run pytest tests/test_integration_smoke.py -q
```

Operator shell smoke:

```bash
bash /workspace/scripts/smoke_study_api.sh
```

## Deploy

Railway `api` service: see [How to set up the app](../docs/runbooks/setup/HOW_TO_SETUP_APP.md#railway-api) and [Study API environment](../docs/runbooks/deploy/STUDY_API_ENV.md).
