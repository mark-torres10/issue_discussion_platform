# Step 7: LangSmith tracing hooks with export disabled

## Goal

Add `StudyTracingService` with hook methods called after session start, text generation commit, voice ingest commit, session complete, and connection failure. Default exporter is a no-op when `TRACE_EXPORT_ENABLED=false`. When flag is true in tests only, build `conversation_turn` root traces with allowlisted envelope fields and UUID v7 run ids persisted for idempotent retry. Never send internal session id, invitation token, or capability cookie values to LangSmith. Opening snapshot text is not exported as a generation trace.

## Files to inspect

- `/workspace/strategy_planning/langsmith_proposal_2026_08_06.md` (trace model, envelope, feature flag, endpoint touchpoints)
- `/workspace/backend/app/services/generation.py` (text hook call site from Step 5)
- `/workspace/backend/app/services/sessions.py` (hook on start and complete)
- `/workspace/backend/app/api/internal/realtime_items.py` (voice ingest commit path from Step 6)
- `/workspace/backend/workers/realtime_control.py` (worker voice events from Step 6)

## Files allowed to change (closed set)

- `/workspace/backend/app/services/tracing.py`
- `/workspace/backend/app/integrations/langsmith_exporter.py`
- `/workspace/backend/app/integrations/langsmith_envelope.py`
- `/workspace/backend/app/models/tracing.py`
- `/workspace/backend/app/repositories/trace_runs.py`
- `/workspace/supabase/migrations/20260822130000_trace_runs.sql`
- `/workspace/backend/app/core/config.py` (`TRACE_EXPORT_ENABLED`, `LANGSMITH_*` var names documented)
- `/workspace/backend/app/services/generation.py` (sole owner of text generation tracing hook call sites in this step)
- `/workspace/backend/app/services/sessions.py` (add hook calls on start and complete only)
- `/workspace/backend/app/services/realtime.py` (add hook on connection failure only)
- `/workspace/backend/app/api/internal/realtime_items.py` (add hook after voice turn commit from ingest)
- `/workspace/backend/workers/realtime_control.py` (add hook on provider-observed voice events when worker commits or forwards ingest)
- `/workspace/backend/pyproject.toml` (add `langsmith` package; sole `pyproject.toml` owner in this step)
- `/workspace/backend/tests/test_tracing.py`
- `/workspace/backend/tests/conftest.py` (fake langsmith client; sole `conftest.py` owner in this step)

## Files forbidden to change

- `/workspace/backend/app/api/**` except `/workspace/backend/app/api/internal/realtime_items.py` for ingest hook call sites only
- `/workspace/backend/app/services/export.py`
- `/workspace/ui/**`
- `/workspace/backend/app/integrations/openai_realtime.py`

## Contracts / acceptance checks

- `TRACE_EXPORT_ENABLED` defaults to `false` when unset.
- `on_generation_committed` called only after participant and AI turns are committed in Postgres for text mode.
- `on_voice_turn_committed` (or equivalent) called only after a canonical voice turn is committed from internal ingest or worker path.
- Envelope includes `telemetry_thread_id` as `metadata.thread_id`. Must not include internal `session_id`, invitation hash, or participant email.
- `trace_kind` values are `instrumented_text_generation`, `provider_observed_realtime_response`, and `client_reconstructed_voice_turn`.
- Opening turn from snapshot at start is not passed to `on_generation_committed`.
- LangSmith outage during export does not fail HTTP response (test with raising exporter).
- Persisted `langsmith_root_run_id` reused on retry export for same canonical turn.
- Redaction test: envelope builder rejects fields not on allowlist.

## Tests to add

| Test | What it locks |
| --- | --- |
| `test_tracing.py::TestNoopExporter::test_flag_off_sends_nothing` | No export when flag is off |
| `test_tracing.py::TestEnvelope::test_denies_session_id_in_metadata` | Rejects session id in metadata |
| `test_tracing.py::TestGenerationHook::test_commit_succeeds_when_langsmith_down` | HTTP succeeds when LangSmith is down |
| `test_tracing.py::TestRunIdPersistence::test_retry_reuses_root_run_id` | Idempotent export |
| `test_tracing.py::TestOpeningTurn::test_start_hook_does_not_create_conversation_turn_for_opening` | Opening turn is not a generation trace |
| `test_tracing.py::TestVoiceIngestHook::test_ingest_commit_triggers_voice_trace_kind` | Voice trace from ingest path |

## Exact commands to run and expected output

```bash
cd /workspace/backend
uv sync
TRACE_EXPORT_ENABLED=false uv run pytest tests/test_tracing.py -q
```

You should see all tracing tests pass.

```bash
cd /workspace/backend
TRACE_EXPORT_ENABLED=true LANGSMITH_API_KEY=mock LANGSMITH_PROJECT=issue-discussion-local uv run pytest tests/test_tracing.py -q
```

You should see export path tests pass with the mock LangSmith client.

```bash
cd /workspace/backend
uv run pytest tests/ -q
```

You should see the full test suite pass.

## Out of scope for this step

- Enabling tracing in Railway production (`TRACE_EXPORT_ENABLED` stays false in deploy docs until policy approval)
- Outbox worker for complete export guarantee
- UI LangSmith embeds
- `wrap_openai` in the production hot path may be added here only if it does not change Step 5 test contracts. Prefer a thin wrapper in the `openai_client.py` factory owned by Step 5.

## Dependencies

- Step 5 complete (text generation commit path and `generation.py` hook point exist).
- Step 6 complete (voice ingest paths in `realtime_items.py` and `realtime_control.py` exist).

## Shared file ownership in this step

This step owns `/workspace/backend/pyproject.toml` and `/workspace/backend/tests/conftest.py` for its turn. This step is the sole owner of tracing hook call sites in `generation.py`, `realtime_items.py`, and `realtime_control.py`.

## Parallelization

This step runs after Steps 5 and 6. Step 8 starts only after Step 7 is complete.

## What must pass / fail before the step is complete

| Check | Must pass | Must fail |
| --- | --- | --- |
| Default `TRACE_EXPORT_ENABLED` | No LangSmith HTTP calls in tests | Accidental export |
| Completion when exporter raises | HTTP 200 on complete | 500 on complete |
| Envelope with `session_id` key | Builder raises or strips before send | Raw session id in payload |
