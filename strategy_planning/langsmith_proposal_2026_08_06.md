# LangSmith proposal

## Recommendation

Use LangSmith as the observability layer for study conversations, not as the system of record. Railway remains the authoritative store for sessions, final transcript turns, completion status, and study configuration. LangSmith should receive approved conversation traces so researchers and engineers can inspect what happened, measure AI latency and cost, and debug model behavior across study waves.

For the first LangSmith integration, track only:

* Conversation transcripts grouped by study session
* General AI metrics, especially time to first token (TTFT), total latency, token usage, and cost

Out of scope for this proposal:

* Automated evaluators
* Annotation queues
* Datasets built for offline scoring
* Experiments and A/B comparison tables
* Human feedback scoring workflows in LangSmith

Those tools can come later once the conversation path is stable and the research team knows which measures they want to score.

## Design principles

### Railway owns truth, LangSmith owns visibility

If a turn is saved once in Postgres and twice in a retry, Railway must remain correct. LangSmith traces can be best effort and eventually consistent, but they should not become the only place a transcript lives. If LangSmith is down, session completion should still succeed.

### One study session is one LangSmith thread

Use the study `session_id` as the LangSmith `thread_id` metadata on every run in that conversation. That lets researchers open the Threads view and see the full participant and AI exchange, with aggregated latency, tokens, and cost for the session.

Propagate `thread_id` to parent and child runs. Without it on child LLM runs, thread level token and cost totals will be wrong.

### Trace final turns, not browser noise

Do not send microphone levels, partial ASR text, audio check media, or raw WebRTC packets to LangSmith. Send final transcript turns, AI generation spans, and the timing or usage fields needed for TTFT and cost.

### Prefer structured LLM runs

Where possible, log AI replies as `run_type="llm"` with message shaped inputs and outputs, `ls_provider`, `ls_model_name`, and `usage_metadata`. That is what unlocks LangSmith cost display and useful playground style inspection later, even if we are not using experiments yet.

### Keep secrets and PII controls explicit

LangSmith API keys stay on Railway. The browser never talks to LangSmith directly. Decide before production whether system prompts are included in traces, whether participant text is retained in LangSmith for the full retention window, and which study wave metadata is safe to attach.

## How LangSmith fits the architecture

```text
Participant browser (Vercel)
  |  session API, final turns, voice events
  v
Railway FastAPI
  |  authoritative session + transcript store
  |  mint OpenAI Realtime secrets
  |  emit approved traces
  v
LangSmith project
  Threads: one per session_id
  Runs: session / turn / llm spans
  Metrics: TTFT, latency, tokens, cost
```

### Text mode

Railway can mediate the model call.

1. UI posts `POST /v1/sessions/{session_id}/messages`
2. Railway saves the participant turn
3. Railway calls OpenAI through a traced client
4. Railway saves the AI turn
5. LangSmith receives a nested trace automatically or through the tracing service

This path should use `langsmith.wrappers.wrap_openai` for Chat Completions style calls, or an equivalent `@traceable(run_type="llm")` span if the call path is custom.

### Voice mode

The browser talks to OpenAI Realtime over WebRTC. Railway does not see token streams in real time.

1. UI posts final turns and optional generation metrics to Railway
2. Railway upserts transcript turns
3. Railway reconstructs LangSmith runs for each AI turn
4. Railway attaches usage and TTFT when the client or OpenAI usage events provide them

Voice tracing is therefore turn based reconstruction, not live stream wrapping. That is acceptable for study transcript review and aggregate AI metrics. It is not a substitute for raw audio retention.

## Trace model

### Thread

| Field | Value |
| --- | --- |
| LangSmith thread key | `metadata.thread_id` |
| Value | study `session_id` |
| Also useful | `metadata.session_id` set to the same value for compatibility |

### Recommended run tree

```text
session (chain)                         # created on session start, closed on complete
  turn:{sequence} (chain)               # one per conversational exchange when useful
    participant_turn (chain)            # optional; useful for ordering and mode tags
    ai_turn (llm)                       # AI generation with usage, cost, TTFT
  connection_event (chain)              # sparse; only notable failures or reconnects
```

Keep the first version simple:

* One root `session` run opened at start and ended at complete
* One child `ai_turn` LLM run for each final AI transcript turn
* Participant text included as the input messages on the AI turn, or as a sibling chain run if that makes the Threads Messages view clearer

Do not create a LangSmith run for every mute toggle or audio level update.

### Metadata on every run

Attach the same study metadata to parent and child runs:

```python
{
    "thread_id": "<session_id>",
    "session_id": "<session_id>",
    "study_wave": "2026-fall-wave-1",
    "issue_id": "campus-speech",
    "prompt_version": "issue-v1",
    "avatar_version": "persona-a-v1",
    "voice_version": "alloy-v1",
    "interaction_mode": "voice",  # or "text"
    "ai_position": "oppose",
    "openai_realtime_model": "<model-id>",
}
```

Optional tags:

```text
study-wave:2026-fall-wave-1
mode:voice
status:completed
```

### Transcript payload shape

For AI LLM runs, prefer OpenAI style messages so LangSmith renders conversations cleanly:

```python
inputs = {
    "messages": [
        {"role": "system", "content": "<approved prompt excerpt or omitted>"},
        {"role": "user", "content": "<final participant turn text>"},
    ]
}

outputs = {
    "messages": [
        {"role": "assistant", "content": "<final AI turn text>"},
    ]
}
```

If the research protocol does not allow storing full system instructions in LangSmith, send a prompt version string instead of the raw prompt and keep the full prompt only in Railway.

### Turn identifiers

Include Railway turn IDs in metadata so traces can be reconciled with the database:

```python
{
    "participant_turn_id": "<uuid>",
    "ai_turn_id": "<uuid>",
    "sequence": 4,
    "source_mode": "voice",
    "interrupted": false,
}
```

Idempotent tracing should key off `ai_turn_id`. Retrying a turn save must not create duplicate LLM runs for the same turn.

## AI metrics in scope

### Time to first token (TTFT)

TTFT is the time from the start of an AI generation span to the first output token or first audible AI audio chunk, depending on mode.

| Mode | How to capture |
| --- | --- |
| Text, Railway mediated, streaming | Use `@traceable` or `wrap_openai` streaming so LangSmith can populate TTFT automatically. With `RunTree`, emit a `new_token` event on the first chunk. |
| Voice, browser Realtime | Browser records `generation_started_at` and `first_audio_at` or `first_transcript_token_at`, then posts them with the final AI turn. Railway writes an LLM run and adds a `new_token` event at the first token timestamp. |

Recommended client fields for voice metric posts:

```python
class AiGenerationMetrics(BaseModel):
    turn_id: UUID
    generation_started_at: datetime
    first_token_at: datetime | None = None
    completed_at: datetime | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    provider: str = "openai"
    model_name: str
```

If first token time is missing, still log the LLM run with start and end times. Total latency remains useful even when TTFT is unavailable.

### Cost and tokens

For automatic or manual cost tracking, each AI LLM run should include:

* `metadata.ls_provider` = `"openai"`
* `metadata.ls_model_name` = the realtime or chat model ID actually used
* `usage_metadata` with at least `input_tokens` and `output_tokens`

Example:

```python
from langsmith import get_current_run_tree

run = get_current_run_tree()
if run is not None:
    run.set(
        usage_metadata={
            "input_tokens": 1200,
            "output_tokens": 180,
            "total_tokens": 1380,
        }
    )
```

If OpenAI Realtime usage events are available to the client or through a server side usage lookup, pass those counts to Railway with the turn. If not, log transcript only and leave token fields empty until a reliable usage source exists. Do not invent token counts.

Configure model pricing in LangSmith when the selected OpenAI models are not priced automatically. For non standard realtime billing, Railway may set `input_cost`, `output_cost`, and `total_cost` directly on `usage_metadata` once the study team agrees on the calculation.

### Other useful metrics without expanding scope

These are in scope as ordinary run fields, not as a separate eval product:

* Total AI turn latency
* Session duration
* Error rate on realtime connect, turn save, and completion
* Mode mix: voice vs text turns per session

Do not add custom LangSmith feedback scores yet.

## Wiring into the FastAPI backend

Add a tracing service behind an interface so Phase 1 and Phase 2 can no-op.

```text
backend/app/services/tracing.py
```

Suggested methods:

```python
class StudyTracingService(Protocol):
    def on_session_started(self, session: SessionInternal) -> None: ...
    def on_turns_saved(self, session_id: UUID, turns: list[TranscriptTurn]) -> None: ...
    def on_ai_generation(
        self,
        session: SessionInternal,
        participant_turn: TranscriptTurn | None,
        ai_turn: TranscriptTurn,
        metrics: AiGenerationMetrics | None = None,
    ) -> None: ...
    def on_session_completed(self, session: SessionInternal) -> None: ...
    def on_session_event(self, session_id: UUID, event: SessionEvent) -> None: ...
```

### Environment

Set these on Railway only:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=issue-discussion-platform
LANGSMITH_WORKSPACE_ID=...   # if using workspace scoped keys
```

Use separate LangSmith projects for local, staging, and production study waves if possible. Example:

* `issue-discussion-local`
* `issue-discussion-staging`
* `issue-discussion-prod-2026-fall`

### Endpoint touchpoints

| Backend action | LangSmith action |
| --- | --- |
| `POST /v1/sessions/{id}/start` | Open or upsert root session run with thread metadata |
| `POST /v1/sessions/{id}/messages` | Trace mediated text generation; log participant and AI turns |
| `POST /v1/sessions/{id}/turns` | Upsert transcript linked runs for voice final turns |
| `POST /v1/sessions/{id}/events` | Log sparse high signal events only |
| `POST /v1/sessions/{id}/complete` | End root session run; attach completion reason and turn count |
| `POST /v1/sessions/{id}/realtime/session` | Do not send the client secret to LangSmith; optionally log that a realtime credential was minted |

If voice metrics arrive with turns, either extend `TranscriptTurnCreate.metadata` or add an optional `generation_metrics` field on the turns batch request. Keep the public participant API small.

### Failure policy

Tracing failures must not fail the participant session.

* Catch and log LangSmith export errors
* Retry transient failures in the background if easy
* Never block `complete` on LangSmith availability
* Never return LangSmith IDs as a required participant response field in Phase 1

## What researchers will see

In the LangSmith project:

1. **Threads** filtered by study wave or issue metadata
2. A single thread per participant session, opened by `session_id`
3. Message or turn views of the disagreement conversation
4. Per AI turn latency and TTFT when first token events exist
5. Token and cost totals per turn and rolled up per thread when usage metadata is present
6. Tags and metadata to separate prompt versions, avatars, voices, and modes

This supports the original research need to log what the AI said turn by turn and control for it later, without building an evaluation harness yet. Scoring how participants disagree can remain an offline research process using Railway exports, with LangSmith as the operational transcript and metrics viewer.

## LangSmith phases

These phases align with the UI and backend proposals. LangSmith work belongs mainly with backend Phase 3, but the contract can be stubbed earlier.

### Phase 1. Tracer contract only

Implement `StudyTracingService` as a no-op. Keep LangSmith env vars unset in local UI work. Prove that session, turn, and completion hooks exist without sending data off box.

Review questions:

* Are the hook points correct for start, turns, messages, and complete?
* Is `session_id` available everywhere we will need `thread_id`?
* Can tracing be disabled with one config flag?

### Phase 2. Durable sessions, still no production traces

When Postgres lands, store enough fields to support later reconciliation: turn IDs, timestamps, mode, model name, and optional generation metrics. Continue no-op or local dry run logging.

Review questions:

* Can we reconstruct a thread from Railway data alone?
* Are generation metric fields validated even before LangSmith is enabled?

### Phase 3. Live transcript and metrics tracing

Enable LangSmith in staging, then production.

1. Create the LangSmith project and API key on Railway
2. Trace text mode with wrapped OpenAI or explicit LLM runs
3. Reconstruct voice mode AI turns as LLM runs with transcript text
4. Propagate `thread_id` and study metadata on all runs
5. Populate TTFT through streaming wrappers or `new_token` events
6. Populate tokens and cost through `usage_metadata` when available
7. Verify Threads, latency, and cost views with pilot sessions

Pilot checklist:

* Text only session appears as one thread with ordered turns
* Voice session transcript appears without raw audio
* Duplicate turn posts do not duplicate LLM runs
* Completion works when LangSmith is unreachable
* Cost shows for at least the text path
* TTFT shows for streaming text and for voice when client timestamps are present

## Data handling and research controls

Before enabling production tracing, the study team should confirm:

1. Whether full system prompts are stored in LangSmith or only prompt versions
2. Whether participant transcripts in LangSmith share the same retention period as Railway
3. Who on the research team has LangSmith project access
4. Whether local and staging traces may contain synthetic only data
5. Whether interrupted AI speech is stored as partial text, final text, or both
6. Whether cost estimates are good enough for engineering monitoring, or need exact billing reconciliation

Defaults for the first integration:

* Store final turn text only
* Store prompt version always; store full prompt only if approved
* Store no raw audio in LangSmith
* Store no audio check data
* Treat cost as an engineering and pilot metric, not a formal study outcome

## Decisions needed

1. Exact LangSmith project naming for local, staging, and each study wave
2. Whether `thread_id` equals the public session UUID or a separate internal UUID
3. Whether voice TTFT is defined as first audio packet or first transcript token
4. Whether OpenAI Realtime usage is available reliably enough to estimate cost in voice mode
5. Whether system instructions appear in LangSmith inputs
6. Retention and access policy for transcript text in LangSmith
7. Whether sparse connection events are traced in Phase 3 or deferred

## Initial scope

The first LangSmith build should include:

* A Railway tracing service interface
* Thread grouping by study session
* Transcript linked AI turn runs
* Metadata for study wave, issue, prompt, avatar, voice, and mode
* TTFT support for mediated streaming text and client reported voice timings
* Token and cost fields when usage is available
* Safe failure behavior that never blocks participants

The first LangSmith build should exclude:

* Automated evaluators
* Annotation queues
* Experiments
* Dataset upload workflows
* Feedback score collection in the participant UI
* Raw audio or video in traces
* Researcher facing LangSmith embeds inside the Next.js app

Excluding evaluation product surfaces keeps the first integration focused on the two jobs that matter now: see the conversation, and see whether the AI path is fast and expensive.
