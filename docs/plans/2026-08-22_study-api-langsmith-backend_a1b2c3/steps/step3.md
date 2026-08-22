# Step 3: Supabase schema and repository layer

## Goal

Add SQL migrations for Study Postgres on Supabase, database connection settings, and repository modules that read and write `SessionRecord`, configuration snapshots, canonical turns, observations, invitations, and audit rows. Repositories must enforce unique constraints from the backend proposal. This step does not wire HTTP routes to Postgres yet.

## Files to inspect

- `/workspace/docs/runbooks/setup/HOW_TO_SETUP_APP.md` (Supabase is hosted Postgres)
- `/workspace/strategy_planning/backend_proposal_2026_08_06.md` (minimum data model, unique constraints)
- `/workspace/supabase/config.toml` (if present)
- `/workspace/backend/app/models/session.py` (from Step 2)

## Files allowed to change (closed set)

- `/workspace/supabase/migrations/20260822100000_study_core_schema.sql`
- `/workspace/backend/app/db/__init__.py`
- `/workspace/backend/app/db/engine.py`
- `/workspace/backend/app/db/session.py`
- `/workspace/backend/app/repositories/__init__.py`
- `/workspace/backend/app/repositories/invitations.py`
- `/workspace/backend/app/repositories/sessions.py`
- `/workspace/backend/app/repositories/snapshots.py`
- `/workspace/backend/app/repositories/turns.py`
- `/workspace/backend/app/repositories/observations.py`
- `/workspace/backend/app/repositories/audit.py`
- `/workspace/backend/pyproject.toml` (add `sqlalchemy[asyncio]`, `asyncpg`, `alembic` or use raw SQL via asyncpg only)
- `/workspace/backend/tests/test_repositories.py`
- `/workspace/backend/tests/conftest.py` (postgres test fixture using `DATABASE_URL` or skip marker)

## Files forbidden to change

- `/workspace/backend/app/api/**`
- `/workspace/backend/app/services/sessions.py` (wired in Step 4)
- `/workspace/backend/app/sample_data/**`
- `/workspace/ui/**`
- `/workspace/backend/workers/**`

## Contracts / acceptance checks

Tables must include at least the columns from the backend proposal.

- `sessions` with `telemetry_thread_id` UUID, `study_id`, status, version, writer lease fields, consent fields nullable, timestamps
- `configuration_snapshots` immutable content
- `canonical_turns` with unique `(session_id, ordinal)`, unique `(session_id, client_event_id)` where not null, unique `(session_id, provider_item_id)` where not null
- `observations` allowlisted types
- `invitations` with token hash only, never raw token
- `audit_events` without transcript text copies

Repository behaviors are as follows.

- `create_invitation` stores hash and assigns UUID v7 `telemetry_thread_id`
- `insert_turn` raises conflict on duplicate id with different content hash
- `complete_session` method signature accepts observations list but implementation may be stub until Step 4

Enable row level security on tables exposed through the Supabase Data API if any table is API-visible. The Study API should use a direct connection string with an API-only database role, not the anon key.

## Tests to add

| Test | What it locks |
| --- | --- |
| `test_repositories.py::TestInvitationRepository::test_stores_hash_not_raw_token` | Invitation security |
| `test_repositories.py::TestTurnRepository::test_duplicate_provider_item_id_rejected` | One canonical turn per provider item |
| `test_repositories.py::TestSessionRepository::test_version_increment` | Monotonic session version |
| `test_repositories.py::TestSnapshotRepository::test_snapshot_immutable` | No update path on published snapshot |

Tests may skip when `DATABASE_URL` is unset. CI should set a test database URL when available.

## Exact commands to run and expected output

```bash
cd /workspace
supabase db lint 2>/dev/null || echo "lint optional if CLI linked"
```

```bash
cd /workspace/backend
uv sync
DATABASE_URL="${DATABASE_URL:-}" uv run pytest tests/test_repositories.py -q
```

When `DATABASE_URL` is set, you should see all repository tests pass. When it is unset, tests should skip with an explicit skip reason and exit code 0.

```bash
cd /workspace/backend
uv run pytest tests/ -q
```

You should see Step 1 and Step 2 tests still pass with no regression.

## Out of scope for this step

- HTTP route wiring to repositories
- OpenAI, Realtime, LangSmith
- UI or Vercel env changes
- Staff membership tables (stub `study_id` constant in repositories is fine)

## Dependencies

- Step 1 complete (models and config).

## Parallelization

This step may run in parallel with Step 2 after Step 1. Do not modify files in the Step 2 closed set.

## What must pass / fail before the step is complete

| Check | Must pass | Must fail |
| --- | --- | --- |
| Migration SQL applies cleanly on empty Supabase database | Tables and indexes exist | Migration errors on apply |
| Repository insert duplicate provider item | IntegrityError or domain conflict | Second row inserted |
| Step 2 API tests without `STORAGE_MODE=postgres` | Still pass on memory | Regression in participant API |
