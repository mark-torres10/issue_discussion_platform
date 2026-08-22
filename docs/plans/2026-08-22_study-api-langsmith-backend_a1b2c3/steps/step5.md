# Step 5: Server-mediated text generation

## Goal

Replace scripted AI replies in `POST /v1/participant-session/messages` with server-owned OpenAI Chat Completions calls. Model the generation as an operation with states `accepted`, `running`, `succeeded`, and `failed`. Retry with the same `Idempotency-Key` and request hash must return the stored operation and turns without a second model call. Keep the OpenAI API key on the server only.

## Files to inspect

- `/workspace/strategy_planning/backend_proposal_2026_08_06.md` (text path, generation operations)
- `/workspace/strategy_planning/langsmith_proposal_2026_08_06.md` (instrumented text generation, wrap_openai note for Step 7)
- `/workspace/backend/app/api/messages.py`
- `/workspace/backend/app/services/sessions.py`

## Files allowed to change (closed set)

- `/workspace/backend/app/services/generation.py`
- `/workspace/backend/app/integrations/__init__.py`
- `/workspace/backend/app/integrations/openai_client.py`
- `/workspace/backend/app/models/generation.py`
- `/workspace/backend/app/api/messages.py`
- `/workspace/backend/app/repositories/generation_operations.py` (new table via migration file `/workspace/supabase/migrations/20260822110000_generation_operations.sql` only if this step owns it. Otherwise use existing sessions DB session in same migration addendum)
- `/workspace/backend/pyproject.toml` (add `openai` package; sole `pyproject.toml` owner in this step)
- `/workspace/backend/tests/test_generation.py`
- `/workspace/backend/tests/test_messages.py` (extend for live vs mock)
- `/workspace/backend/tests/conftest.py` (mock OpenAI client fixture; sole `conftest.py` owner in this step)

## Files forbidden to change

- `/workspace/backend/app/services/realtime.py`
- `/workspace/backend/app/services/tracing.py`
- `/workspace/backend/app/services/export.py`
- `/workspace/backend/workers/**`
- `/workspace/backend/app/api/participant_session.py` (except import path if required)
- `/workspace/ui/**`

If a schema change is required, only add `/workspace/supabase/migrations/20260822110000_generation_operations.sql` in this step closed set. Do not edit the Step 3 migration file.

## Contracts / acceptance checks

- `POST /v1/participant-session/messages` creates participant turn, runs generation, creates AI turn with `origin=study_api_text`.
- Response includes `operation_id`, `operation_status`, `participant_turn`, `ai_turn`, `status`, `version`.
- Same idempotency key and body hash returns identical response without second OpenAI call (mock asserts call count).
- OpenAI failure returns `503 generation_failed` when retryable flag set per error table.
- `OPENAI_API_KEY` read from environment only. Missing key in test uses mock client.
- Reject the message when the snapshot model does not match the configured model.

## Tests to add

| Test | What it locks |
| --- | --- |
| `test_generation.py::TestGenerationOperation::test_idempotent_retry_skips_model` | Idempotency |
| `test_generation.py::TestGenerationOperation::test_operation_state_transitions` | accepted to succeeded |
| `test_messages.py::TestMessagesEndpoint::test_creates_ai_turn_server_side` | No browser AI creation |
| `test_messages.py::TestMessagesEndpoint::test_openai_failure_returns_503` | Error mapping |

## Exact commands to run and expected output

```bash
cd /workspace/backend
uv sync
OPENAI_API_KEY=mock uv run pytest tests/test_generation.py tests/test_messages.py -q
```

You should see all tests pass using the mocked OpenAI client.

```bash
cd /workspace/backend
uv run pytest tests/ -q
```

You should see the full test suite pass. Step 6 and Step 7 tests may not exist yet.

## Out of scope for this step

- LangSmith `wrap_openai` wiring (Step 7 adds tracing wrapper around the client factory)
- Voice Realtime
- UI wiring
- Staff routes

## Dependencies

- Step 4 complete (durable turns and sessions).

## Shared file ownership in this step

This step owns `/workspace/backend/pyproject.toml` and `/workspace/backend/tests/conftest.py` for its turn. Do not edit `router.py` in this step.

## Parallelization

This step runs after Step 4. Step 6 starts only after Step 5 is complete.

## What must pass / fail before the step is complete

| Check | Must pass | Must fail |
| --- | --- | --- |
| Duplicate idempotency key on messages | Same AI text returned | Second OpenAI request in mock |
| POST messages without capability cookie | 401 | 200 |
| AI turn origin in database | `study_api_text` | `client_observation` |
