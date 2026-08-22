# Step 4: Durable record wiring and completion transaction

## Goal

Switch participant services from in-memory storage to Supabase Postgres when `STORAGE_MODE=postgres`, while keeping memory mode for fast contract tests. Enforce the session state machine, writer lease with 30-minute renewal, optimistic versioning, immutable turns, idempotent commands, and a single-database-transaction completion path. The same contract test suite must pass in both storage modes.

## Files to inspect

- `/workspace/backend/app/services/sessions.py` (Step 2 in-memory)
- `/workspace/backend/app/repositories/*.py` (Step 3)
- `/workspace/strategy_planning/backend_proposal_2026_08_06.md` (completion section, concurrency, grace period)

## Files allowed to change (closed set)

- `/workspace/backend/app/services/sessions.py`
- `/workspace/backend/app/services/transcripts.py`
- `/workspace/backend/app/services/capability.py`
- `/workspace/backend/app/core/dependencies.py` (storage backend selection)
- `/workspace/backend/app/core/config.py` (`STORAGE_MODE`, `DATABASE_URL`)
- `/workspace/backend/app/api/participant_access.py` (wire to durable invitations only)
- `/workspace/backend/app/api/participant_session.py`
- `/workspace/backend/app/api/messages.py` (persistence only, still scripted AI)
- `/workspace/backend/app/api/observations.py`
- `/workspace/backend/app/api/realtime.py` (persist call row only, still fake SDP)
- `/workspace/backend/tests/test_completion.py` (extend for postgres parametrization)
- `/workspace/backend/tests/test_sessions.py`
- `/workspace/backend/tests/test_concurrency.py` (new)
- `/workspace/backend/tests/conftest.py` (parametrize `storage_mode`)

## Files forbidden to change

- `/workspace/supabase/migrations/**` (unless a critical constraint fix. Prefer a new migration file owned by the Step 3 owner in a follow-up)
- `/workspace/backend/app/services/generation.py`
- `/workspace/backend/app/services/realtime.py`
- `/workspace/backend/app/services/tracing.py`
- `/workspace/backend/app/services/export.py`
- `/workspace/backend/workers/**`
- `/workspace/ui/**`

## Contracts / acceptance checks

- `STORAGE_MODE=memory` runs Step 2 behavior unchanged.
- `STORAGE_MODE=postgres` uses repositories for all participant writes and reads.
- Completion transaction follows the backend proposal. Validate lease and version, insert recovery observations, reject hash conflicts, set `completed_at`, increment version, and revoke writer lease. Do not persist a `completing` status.
- Completed session readable via `GET /v1/participant-session` for 24 hours after `completed_at`. Writes return `409 session_already_completed`. After grace, `GET` may return `410 session_unavailable`.
- Simultaneous complete requests from two workers produce one `completed` row (test with threaded clients or duplicate async calls).
- `telemetry_thread_id` persisted at invitation and never exposed in `ParticipantSessionView`.

## Tests to add

| Test | What it locks |
| --- | --- |
| `test_concurrency.py::TestWriterLease::test_stale_writer_gets_409` | Writer conflict |
| `test_concurrency.py::TestCompletionRace::test_double_complete_single_transition` | One completion |
| `test_completion.py` (parametrize memory/postgres) | Atomic completion |
| `test_sessions.py` (parametrize) | State transitions pending/active/paused/completed/expired |

## Exact commands to run and expected output

```bash
cd /workspace/backend
STORAGE_MODE=memory uv run pytest tests/test_sessions.py tests/test_completion.py tests/test_concurrency.py -q
```

You should see all tests pass.

```bash
cd /workspace/backend
STORAGE_MODE=postgres DATABASE_URL="$DATABASE_URL" uv run pytest tests/test_sessions.py tests/test_completion.py tests/test_concurrency.py -q
```

When `DATABASE_URL` is set, you should see all tests pass against Postgres. When it is unset, postgres parametrized cases should skip.

```bash
cd /workspace/backend
uv run pytest tests/ -q
```

You should see the full test suite pass.

## Out of scope for this step

- Live OpenAI text (Step 5)
- Real Realtime SDP (Step 6)
- LangSmith hooks (Step 7)
- UI changes

## Dependencies

- Step 2 complete (participant routes and contract tests).
- Step 3 complete (migrations and repositories).

## Parallelization

This step runs sequentially after Steps 2 and 3. Steps 5, 6, 7, and 8 may run in parallel after Step 4 if each step stays within its closed file set.

## What must pass / fail before the step is complete

| Check | Must pass | Must fail |
| --- | --- | --- |
| Contract tests in memory and postgres modes | All tests pass when DB URL is present | Silent data loss on complete |
| Complete with invalid `expected_version` | 409 `version_conflict` | Partial completion row |
| Read transcript after complete within grace | 200 with turns | 410 during grace period |
