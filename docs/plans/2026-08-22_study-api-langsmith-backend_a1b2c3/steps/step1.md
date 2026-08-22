# Step 1: Backend foundation and shared contracts

## Goal

Create the FastAPI package layout, shared configuration, error envelope, health and readiness endpoints, and pytest harness so every later slice imports the same types and test fixtures. This step does not implement participant business logic. It only establishes the skeleton that Step 2 will fill.

## Files to inspect

- `/workspace/backend/app/main.py`
- `/workspace/backend/pyproject.toml`
- `/workspace/backend/tests/test_health.py`
- `/workspace/backend/railway.toml`
- `/workspace/strategy_planning/backend_proposal_2026_08_06.md` (error model, enums, health table)
- `/workspace/.agents/skills/fastapi/SKILL.md`

## Files allowed to change (closed set)

- `/workspace/backend/app/main.py`
- `/workspace/backend/app/__init__.py`
- `/workspace/backend/app/api/__init__.py`
- `/workspace/backend/app/api/router.py`
- `/workspace/backend/app/api/health.py`
- `/workspace/backend/app/core/__init__.py`
- `/workspace/backend/app/core/config.py`
- `/workspace/backend/app/core/errors.py`
- `/workspace/backend/app/models/__init__.py`
- `/workspace/backend/app/models/enums.py`
- `/workspace/backend/app/models/errors.py`
- `/workspace/backend/pyproject.toml`
- `/workspace/backend/tests/conftest.py`
- `/workspace/backend/tests/test_health.py`
- `/workspace/backend/tests/test_errors.py`
- `/workspace/backend/README.md` (create if missing, env var names only)

## Files forbidden to change

- `/workspace/ui/**`
- `/workspace/supabase/**`
- `/workspace/strategy_planning/**`
- `/workspace/docs/plans/**` (except this step file if fixing typos only)
- Any file under `/workspace/backend/app/services/`, `/workspace/backend/app/sample_data/`, `/workspace/backend/workers/`

## Contracts / acceptance checks

- `GET /health` returns JSON with `status` equal to `ok` and optional `commit` from `RAILWAY_GIT_COMMIT_SHA` when set.
- `GET /ready` returns `status` `ok` when `STORAGE_MODE=memory` (default for local dev). When `STORAGE_MODE=postgres` and `DATABASE_URL` is missing, `/ready` returns a non-200 or `status` `degraded` per the health module docstring.
- All public error responses use the frozen `ApiError` shape: `request_id`, `error_code`, `message`, `retryable`, optional `retry_after_seconds`, `session_status`, `current_version`.
- Pydantic public input models use `extra="forbid"` via a shared `FrozenModel` base.
- Enums in `app/models/enums.py` match the backend proposal: `SessionStatus`, `InteractionMode`, `Speaker`, `TurnOrigin`, `ConnectionState`, `ObservationType`, `GenerationOperationStatus`.

## Tests to add

| Test module | Test class / name | What it locks |
| --- | --- | --- |
| `test_health.py` | `TestHealthEndpoint::test_health_returns_ok` | Liveness JSON shape |
| `test_health.py` | `TestReadyEndpoint::test_ready_ok_in_memory_mode` | Sample contracts readiness without Postgres |
| `test_health.py` | `TestReadyEndpoint::test_ready_requires_database_url_in_postgres_mode` | Readiness gate for durable mode |
| `test_errors.py` | `TestApiErrorShape::test_validation_error_maps_to_400` | Shared error envelope on invalid body |
| `test_errors.py` | `TestApiErrorShape::test_unknown_fields_rejected` | `extra=forbid` on a sample FrozenModel |

## Exact commands to run and expected output

```bash
cd /workspace/backend
uv sync
uv run pytest tests/test_health.py tests/test_errors.py -q
```

You should see all tests pass with exit code 0, and the output should end with a line like `5 passed`.

```bash
cd /workspace/backend
uv run fastapi dev app/main.py --port 8000 &
sleep 2
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/ready
kill %1 2>/dev/null || true
```

You should see the first curl print JSON containing `"status":"ok"`. The second curl should print JSON with `"status":"ok"` when `STORAGE_MODE` is unset or `memory`.

## Out of scope for this step

- Participant routes
- Database drivers or migrations
- OpenAI, LangSmith, or Supabase Auth verification
- CORS, cookies, or CSRF
- UI changes

## Dependencies

None. This is the first step in the plan.

## Shared file ownership in this step

This step is the sole owner of the initial versions of `/workspace/backend/pyproject.toml`, `/workspace/backend/tests/conftest.py`, and `/workspace/backend/app/api/router.py`. Later steps may append to these files only in their own turn. See the shared file ownership table in `plan.md`.

## Parallelization

This step runs first. Step 2 starts only after Step 1 is complete.

## What must pass / fail before the step is complete

| Check | Must pass | Must fail |
| --- | --- | --- |
| `uv run pytest tests/test_health.py tests/test_errors.py` | All tests pass | Any failure |
| Import `app.main:app` | No ImportError | Missing module errors |
| `GET /health` | HTTP 200 | HTTP 5xx |
| Adding a forbidden field to a FrozenModel in a test request | HTTP 400 with `validation_error` | Silent acceptance of unknown fields |
