# Study API environment variables

Names only. Store values in a password manager and in the Railway or Vercel dashboards. Do not commit secrets to git.

Full account setup: `strategy_planning/CREDENTIALS_AND_SETUP.md` (not edited by deploy docs).

## Postgres

Study Postgres is the **hosted Supabase Postgres** project linked from [How to set up the app](../setup/HOW_TO_SETUP_APP.md#supabase-database). Railway `api` connects with `DATABASE_URL` (private connection string from Supabase). Do not use a separate Railway Postgres service as the system of record unless the team explicitly approves a second database.

Set `STORAGE_MODE=postgres` in production.

## Railway — Study API (`api` service)

| Variable | Required | Default (documented) | Purpose |
| --- | --- | --- | --- |
| `DATABASE_URL` | Yes (postgres mode) | — | Supabase Postgres connection string |
| `STORAGE_MODE` | Yes | `postgres` in production | `memory` for local sample contracts; `postgres` for durable storage |
| `OPENAI_API_KEY` | Yes (text/voice) | — | OpenAI text and Realtime; server only |
| `INTERNAL_WORKER_TOKEN` | Yes (with worker) | — | Shared secret for `POST /internal/v1/realtime/calls/{id}/items` |
| `PARTICIPANT_UI_ORIGINS` | Yes | — | Comma-separated browser origins (Vercel prod, preview, localhost) |
| `PARTICIPANT_COOKIE_SECRET` | Yes | — | Signs the HTTP-only participant capability cookie |
| `INVITATION_TOKEN_PEPPER` | Yes (postgres invitations) | — | Pepper for invitation token hashes |
| `SUPABASE_URL` | Staff routes | — | Supabase project URL |
| `SUPABASE_JWT_SECRET` | Staff routes | — | Verify forwarded staff JWTs on `/v1/staff/*` |
| `SUPABASE_SERVICE_ROLE_KEY` | Staff routes | — | Server-only Supabase admin operations |
| `STUDY_API_ROLE` | Recommended | `api` | Enables Postgres readiness on `/ready` |
| `RAILWAY_GIT_COMMIT_SHA` | No | set by Railway | Exposed on `GET /health` as `commit` |
| `TRACE_EXPORT_ENABLED` | No | **`false`** | Application switch for LangSmith export after records commit |
| `LANGSMITH_TRACING` | No | **`false`** | LangSmith SDK tracing; keep off until policy approval |
| `LANGSMITH_API_KEY` | When tracing on | — | LangSmith API key |
| `LANGSMITH_PROJECT` | When tracing on | env-specific | e.g. `issue-discussion-prod` |
| `LANGSMITH_WORKSPACE_ID` | Sometimes | — | Only if your LangSmith key type requires it |

### Runtime name mapping (until unified)

Set both names to the same value in Railway until a release removes the legacy names:

| Documented name | Current runtime name |
| --- | --- |
| `PARTICIPANT_UI_ORIGINS` | `CORS_ALLOWED_ORIGINS` |
| `PARTICIPANT_COOKIE_SECRET` | `CAPABILITY_SIGNING_SECRET` |

## Vercel — participant UI (`ui/`)

| Variable | Required | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_STUDY_API_ORIGIN` | Yes (wired UI) | Public Study API origin the browser calls |
| `NEXT_PUBLIC_SUPABASE_URL` | Staff login | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Staff login | Supabase publishable (anon) key |

Never set on Vercel: `OPENAI_API_KEY`, `DATABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `LANGSMITH_API_KEY`, `INTERNAL_WORKER_TOKEN`, or any participant cookie secret.

## Production tracing defaults

Keep these off until a written trace retention policy is attached:

- `TRACE_EXPORT_ENABLED=false`
- `LANGSMITH_TRACING=false`

No LangGraph services run in this stack. LangSmith receives derived traces only after study records commit, and only when `TRACE_EXPORT_ENABLED` is explicitly enabled.

## Smoke checks

### Automated

```bash
# Optional: override production URL
export SMOKE_BASE_URL=https://api-production-198a.up.railway.app
# Required for exchange on deployed postgres (not the in-memory sample token)
export SMOKE_INVITATION_TOKEN=

bash /workspace/scripts/smoke_study_api.sh
```

Expected lines when the API is healthy and the token is valid: `OK health`, `OK exchange`, `OK session read` (exit code 0).

Pytest integration smoke (skips when `SMOKE_BASE_URL` is unset):

```bash
cd backend
uv run pytest tests/test_integration_smoke.py -q
```

### Manual (no Railway CLI or smoke secrets)

1. Open [https://api-production-198a.up.railway.app/health](https://api-production-198a.up.railway.app/health). Expect JSON with `"status":"ok"`.
2. Open [https://api-production-198a.up.railway.app/ready](https://api-production-198a.up.railway.app/ready). With `STORAGE_MODE=postgres` and a reachable Supabase database, expect `"status":"ok"`. Otherwise expect `503` with a database reason.
3. Exchange a known invitation token:

   ```bash
   curl -s -c /tmp/study-cookies.txt -X POST \
     "$SMOKE_BASE_URL/v1/participant-access/exchange" \
     -H 'Content-Type: application/json' \
     -d '{"invitation_token":"YOUR_TOKEN"}'
   ```

4. Read the session with the capability cookie:

   ```bash
   curl -s -b /tmp/study-cookies.txt "$SMOKE_BASE_URL/v1/participant-session"
   ```

Expect `200` and a JSON body with `status` and `writer_role`.

## Deploy (orchestrator / operator)

From the repo root, when Railway CLI is linked:

```bash
railway up ./backend --path-as-root --service api --environment production --detach -m "Study API full implementation"
```

If the CLI is unavailable, push to `main` (GitHub-connected deploy) or upload from the [Railway dashboard](https://railway.com/project/dbbb5f8f-5e8d-4ec9-85d5-ed44f0bb8474).

Public API: [https://api-production-198a.up.railway.app](https://api-production-198a.up.railway.app)
