# Step 6: Voice control plane and internal ingest

## Goal

Implement server-mediated OpenAI Realtime setup. The browser posts SDP to `POST /v1/participant-session/realtime/calls`. The Study API returns an SDP answer only, persists the OpenAI call id from the provider `Location` header, and enqueues control handoff. Add internal route `POST /internal/v1/realtime/calls/{openai_call_id}/items` authenticated with a Railway service credential, not participant cookies. Provide a worker module that can run as a separate process for staging sideband ingest.

## Files to inspect

- `/workspace/strategy_planning/backend_proposal_2026_08_06.md` (Realtime section, internal ingest route, client event allowlist)
- `/workspace/strategy_planning/langsmith_proposal_2026_08_06.md` (voice trace_kind values)
- `/workspace/backend/app/api/realtime.py` (replace fake SDP from Step 2/4)

## Files allowed to change (closed set)

- `/workspace/backend/app/services/realtime.py`
- `/workspace/backend/app/integrations/openai_realtime.py`
- `/workspace/backend/app/api/realtime.py`
- `/workspace/backend/app/api/internal/__init__.py`
- `/workspace/backend/app/api/internal/realtime_items.py`
- `/workspace/backend/app/api/router.py` (mount internal router)
- `/workspace/backend/app/models/realtime.py` (extend if needed)
- `/workspace/backend/app/repositories/realtime_calls.py`
- `/workspace/supabase/migrations/20260822120000_realtime_calls.sql`
- `/workspace/backend/workers/__init__.py`
- `/workspace/backend/workers/realtime_control.py`
- `/workspace/backend/pyproject.toml` (httpx if needed)
- `/workspace/backend/tests/test_realtime.py`
- `/workspace/backend/tests/test_internal_realtime_items.py`
- `/workspace/backend/tests/conftest.py` (worker auth header fixture)

## Files forbidden to change

- `/workspace/backend/app/services/generation.py`
- `/workspace/backend/app/services/tracing.py`
- `/workspace/backend/app/services/export.py`
- `/workspace/backend/app/integrations/openai_client.py` (text client, Step 5)
- `/workspace/ui/**`

## Contracts / acceptance checks

Participant route requirements are as follows.

- `POST /v1/participant-session/realtime/calls` requires writer lease, consent gate when snapshot requires consent, `Idempotency-Key`, `expected_version`.
- Response body contains `sdp_answer` and `expires_at` only. No `client_secret`, call id, or API key.
- New setup invalidates prior active call id for same session (single concurrent call).
- Rate limit constants from backend proposal enforced in service layer (return 429 when exceeded in tests).

Internal route requirements are as follows.

- `POST /internal/v1/realtime/calls/{openai_call_id}/items` requires header `X-Worker-Token` matching `WORKER_SERVICE_TOKEN` env var.
- Maps `provider_item_id` to one canonical AI turn. Duplicate provider item returns existing turn id.
- Participant cookie on internal route must fail with 401 or 403.

Worker requirements are as follows.

- `backend/workers/realtime_control.py` exposes entrypoint documented in README. Staging may use mock provider events in tests.

Opening turn requirements are as follows.

- Realtime session config must include snapshot opening as already-spoken context when `ai_speaks_first` true. Do not request a duplicate automatic first model response.

## Tests to add

| Test | What it locks |
| --- | --- |
| `test_realtime.py::TestRealtimeSetup::test_response_has_no_call_id` | Secret leakage |
| `test_realtime.py::TestRealtimeSetup::test_completed_session_blocks_setup` | Lifecycle guard |
| `test_internal_realtime_items.py::TestInternalIngest::test_maps_provider_item_to_turn` | Canonical ingest |
| `test_internal_realtime_items.py::TestInternalIngest::test_rejects_participant_cookie` | Auth boundary |
| `test_internal_realtime_items.py::TestInternalIngest::test_duplicate_provider_item_idempotent` | One turn per item |

## Exact commands to run and expected output

```bash
cd /workspace/backend
uv sync
WORKER_SERVICE_TOKEN=test-token OPENAI_API_KEY=mock uv run pytest tests/test_realtime.py tests/test_internal_realtime_items.py -q
```

You should see all tests pass with mocked OpenAI Realtime HTTP.

```bash
cd /workspace/backend
uv run pytest tests/ -q
```

You should see the full test suite pass.

## Out of scope for this step

- LangSmith export of voice traces (Step 7)
- Browser WebRTC in UI (Step 9)
- Raw audio storage
- Full sideband WebSocket production hardening beyond staging stub

## Dependencies

- Step 4 complete (durable sessions and turns).

## Parallelization

This step may run in parallel with Steps 5, 7, and 8 after Step 4. It does not edit generation or tracing modules.

## What must pass / fail before the step is complete

| Check | Must pass | Must fail |
| --- | --- | --- |
| Realtime setup response JSON keys | `sdp_answer`, `expires_at` only | `call_id`, `client_secret` |
| Internal ingest without worker token | 401 or 403 | 200 |
| Browser POST to internal items URL | Rejected | Turn created |
