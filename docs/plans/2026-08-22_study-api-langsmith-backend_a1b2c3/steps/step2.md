# Step 2: Sample contracts with in-memory participant API

## Goal

Implement the full participant route table from the backend proposal against an in-memory store with scripted AI text replies and a fake Realtime SDP answer. Invitation exchange sets HTTP-only capability cookies and returns the public session view. The sample protocol does not require consent before start unless the loaded snapshot sets `consent_required=true`. No Postgres, no live OpenAI, no LangSmith.

## Files to inspect

- `/workspace/strategy_planning/backend_proposal_2026_08_06.md` (participant API table, session view models, lifecycle)
- `/workspace/strategy_planning/ui_proposal_2026_08_06.md` (participant journey, route mapping)
- `/workspace/ui/content/sessions/demo-campus-speech-001.yaml` (sample issue and persona for seed data)
- `/workspace/backend/app/main.py` (from Step 1)
- `/workspace/backend/app/models/enums.py`

## Files allowed to change (closed set)

- `/workspace/backend/app/api/participant_access.py`
- `/workspace/backend/app/api/participant_session.py`
- `/workspace/backend/app/api/messages.py`
- `/workspace/backend/app/api/observations.py`
- `/workspace/backend/app/api/realtime.py`
- `/workspace/backend/app/api/router.py` (register new routers only)
- `/workspace/backend/app/models/session.py`
- `/workspace/backend/app/models/transcript.py`
- `/workspace/backend/app/models/observations.py`
- `/workspace/backend/app/models/realtime.py`
- `/workspace/backend/app/services/__init__.py`
- `/workspace/backend/app/services/sessions.py`
- `/workspace/backend/app/services/transcripts.py`
- `/workspace/backend/app/services/capability.py`
- `/workspace/backend/app/core/csrf.py`
- `/workspace/backend/app/core/cors.py`
- `/workspace/backend/app/core/dependencies.py` (participant capability dependency only)
- `/workspace/backend/app/sample_data/__init__.py`
- `/workspace/backend/app/sample_data/sessions.py`
- `/workspace/backend/app/sample_data/invitations.py`
- `/workspace/backend/pyproject.toml` (add `itsdangerous` or equivalent for CSRF if needed)
- `/workspace/backend/tests/test_access.py`
- `/workspace/backend/tests/test_sessions.py`
- `/workspace/backend/tests/test_messages.py`
- `/workspace/backend/tests/test_observations.py`
- `/workspace/backend/tests/test_completion.py`
- `/workspace/backend/tests/test_realtime_sample.py`
- `/workspace/backend/tests/conftest.py` (participant client helpers only)

## Files forbidden to change

- `/workspace/backend/app/db/**`
- `/workspace/backend/app/repositories/**`
- `/workspace/backend/app/services/tracing.py`
- `/workspace/backend/app/services/generation.py`
- `/workspace/backend/app/services/realtime.py` (voice service, Step 6)
- `/workspace/backend/workers/**`
- `/workspace/supabase/**`
- `/workspace/ui/**`

## Contracts / acceptance checks

Routes in this step (all under `/v1` unless noted) are as follows.

| Method and path | Behavior in this step |
| --- | --- |
| `POST /v1/participant-access/exchange` | Validates known invitation token hash from sample data. Sets capability cookie (`HttpOnly`, `Secure`, `SameSite=None` when origins differ). Returns `ParticipantSessionView` without internal session id. Issues CSRF token in response header or body field documented in tests. Second exchange on same token yields read-only writer role. |
| `GET /v1/participant-session` | Returns public projection for cookie session. |
| `POST /v1/participant-session/consent` | Records consent when snapshot requires it. Idempotent per version. `withdrawn=true` blocks start. |
| `POST /v1/participant-session/start` | Moves `pending` to `active`. Returns opening turn when `ai_speaks_first` true in snapshot. Requires `Idempotency-Key` and `expected_version`. |
| `POST /v1/participant-session/messages` | Creates participant turn and scripted AI turn. Same idempotency key and hash returns stored response. |
| `POST /v1/participant-session/observations` | Accepts allowlisted observation types only. |
| `GET /v1/participant-session/transcript` | Server-ordered canonical projection. |
| `POST /v1/participant-session/complete` | Atomic in-memory completion: status `completed`, grace read for 24h, then `410` on writes. |
| `POST /v1/participant-session/pause` | `active` to `paused` when snapshot allows resume. |
| `POST /v1/participant-session/writer-lease/transfer` | Moves lease when transfer nonce valid. |
| `POST /v1/participant-session/realtime/calls` | Returns fake SDP answer string. Must not return call id or API key. |

Hard rules for this step are as follows.

- No public `POST /turns` or turn upsert.
- Browser cannot create `ai` or `system` turns through any public route.
- Sample demo protocol: `consent_required=false` on default snapshot so start works without consent POST.
- `telemetry_thread_id` as UUID v7 assigned at invitation creation in sample store.

## Tests to add

| Test module | What it locks |
| --- | --- |
| `test_access.py` | Unknown token unavailable, writer then read-only second device, cookie required on protected routes |
| `test_access.py` | CSRF rejected on state-changing POST without header |
| `test_sessions.py` | Start idempotency, version conflict returns 409, opening turn only when `ai_speaks_first` |
| `test_messages.py` | Scripted AI reply, duplicate idempotency key, turn conflict on same id different hash |
| `test_completion.py` | Complete transaction all-or-nothing, completed session blocks new messages, grace read works |
| `test_observations.py` | Unknown observation type rejected, batch size limit |
| `test_realtime_sample.py` | SDP answer only in response body |

## Exact commands to run and expected output

```bash
cd /workspace/backend
uv sync
uv run pytest tests/test_access.py tests/test_sessions.py tests/test_messages.py tests/test_completion.py tests/test_observations.py tests/test_realtime_sample.py -q
```

You should see all listed tests pass.

```bash
cd /workspace/backend
uv run pytest tests/ -q
```

You should see the full backend test suite pass, including Step 1 tests.

## Out of scope for this step

- Supabase migrations or SQL
- Live OpenAI or LangSmith
- Internal worker route `POST /internal/v1/realtime/calls/{openai_call_id}/items`
- Staff JWT routes (stub in Step 8)
- UI wiring

## Dependencies

- Step 1 must be complete (shared models, errors, health, config).

## Parallelization

This step may run in parallel with Step 3 after Step 1. Step 2 touches `backend/app/api/*` and in-memory services. Step 3 touches `supabase/migrations` and `backend/app/db/*` only. Do not start Step 4 until both Step 2 and Step 3 are merged or integrated.

## What must pass / fail before the step is complete

| Check | Must pass | Must fail |
| --- | --- | --- |
| Full participant contract test suite above | All tests pass | Any failing test |
| POST message with forged AI turn in body | Rejected as unknown field or ignored | AI turn created from browser payload |
| Complete then POST message | 409 `session_already_completed` | New canonical turn after complete |
| Exchange with invalid token | 404 `session_not_found` or `session_unavailable` | 200 with session view |
