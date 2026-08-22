# Step 8: Research export hooks and staff JWT stub

## Goal

Add versioned research export types and a minimal staff-only export endpoint that reads committed canonical data from Study Postgres. Verify a forwarded Supabase JWT in the `Authorization` header with a stub verifier (JWKS or shared secret config) and deny by default without study membership row. This step does not build a staff admin UI. It only proves export hooks and auth boundary for later researcher tools.

## Files to inspect

- `/workspace/strategy_planning/backend_proposal_2026_08_06.md` (staff role matrix, research export milestone)
- `/workspace/strategy_planning/supabase_auth_proposal_2026_08_05.md` (JWT forward pattern)
- `/workspace/strategy_planning/langsmith_proposal_2026_08_06.md` (export manifest, interrupted AI field choice)

## Files allowed to change (closed set)

- `/workspace/backend/app/services/export.py`
- `/workspace/backend/app/models/export.py`
- `/workspace/backend/app/api/staff/__init__.py`
- `/workspace/backend/app/api/staff/export.py`
- `/workspace/backend/app/api/router.py` (mount `/v1/staff` group; sole `router.py` owner in this step)
- `/workspace/backend/app/core/staff_auth.py`
- `/workspace/backend/app/repositories/staff_membership.py`
- `/workspace/supabase/migrations/20260822140000_staff_membership.sql`
- `/workspace/backend/tests/test_export.py`
- `/workspace/backend/tests/test_staff_auth.py`
- `/workspace/backend/README.md` (document `SUPABASE_JWT_SECRET` or JWKS URL name only)

## Files forbidden to change

- `/workspace/backend/app/services/tracing.py`
- `/workspace/backend/app/services/generation.py`
- `/workspace/backend/app/services/realtime.py`
- `/workspace/backend/app/api/participant_*.py`
- `/workspace/ui/**`
- `/workspace/backend/workers/**`

## Contracts / acceptance checks

- `GET /v1/staff/sessions/{session_id}/export` returns JSON export manifest with schema version, `configuration_snapshot_id`, ordered turns with chosen `display_text` field per manifest, consent fields when present, and `telemetry_thread_id` for cross-reference (not for public participant use).
- Missing or invalid JWT returns 401. Valid JWT without membership returns 403 `staff_forbidden`.
- Participant capability cookie on staff route returns 401 or 403.
- Export reads only committed rows. Incomplete sessions may export with `status` field but must not invent turns.
- Manifest records which interrupted-AI text field is exported (`display_text` default per backend proposal).
- No transcript text in audit log rows created by export action.

Staff role matrix for this step uses a stub membership table.

| Action | Enforced in this step |
| --- | --- |
| Export transcript | `researcher` and `study_admin` only |
| Create invitation | not implemented (403) |
| Delete | not implemented (403) |

## Tests to add

| Test | What it locks |
| --- | --- |
| `test_staff_auth.py::TestJwtVerifier::test_rejects_missing_authorization` | Auth required |
| `test_staff_auth.py::TestJwtVerifier::test_rejects_participant_cookie` | Participant cookie rejected |
| `test_export.py::TestSessionExport::test_export_contains_canonical_turns` | Export reads Postgres rows |
| `test_export.py::TestSessionExport::test_export_denied_without_membership` | Deny without membership |
| `test_export.py::TestExportManifest::test_manifest_version_present` | Manifest has version field |

## Exact commands to run and expected output

```bash
cd /workspace/backend
uv sync
uv run pytest tests/test_export.py tests/test_staff_auth.py -q
```

You should see all tests pass with the test JWT fixture.

```bash
cd /workspace/backend
uv run pytest tests/ -q
```

You should see the full test suite pass.

## Out of scope for this step

- Next.js `/login` or `/app` staff UI (optional separate auth slice)
- LangSmith dataset upload
- Full invitation creation admin API
- Participant route changes

## Dependencies

- Step 4 complete (committed sessions and turns in Postgres).

## Shared file ownership in this step

This step owns `/workspace/backend/app/api/router.py` for its turn. Do not edit `pyproject.toml` or `conftest.py` in this step.

## Parallelization

This step runs after Step 7. Run the integration check after Step 8 before starting Step 9.

## What must pass / fail before the step is complete

| Check | Must pass | Must fail |
| --- | --- | --- |
| Export with valid researcher JWT and membership | 200 with manifest | 403 |
| Export with no JWT | 401 | 200 |
| Export inventing AI turn not in database | Not applicable | Extra turn in JSON |
