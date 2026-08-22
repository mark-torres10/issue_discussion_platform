# Issue Discussion Platform — Backend

FastAPI service for the Study API.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `STORAGE_MODE` | `memory` (default) for sample contracts, or `postgres` for durable storage |
| `DATABASE_URL` | Postgres connection string; required when `STORAGE_MODE=postgres` |
| `RAILWAY_GIT_COMMIT_SHA` | Optional deploy commit SHA exposed on `GET /health` |
| `SUPABASE_JWT_SECRET` | Shared secret for verifying forwarded Supabase staff JWTs on `/v1/staff/*` routes |

## Local development

```bash
cd backend
uv sync
uv run fastapi dev app/main.py --port 8000
```

## Tests

```bash
cd backend
uv run pytest -q
```
