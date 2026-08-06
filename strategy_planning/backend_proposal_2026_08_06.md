# Backend proposal

## Recommendation

The first version should be a focused FastAPI study backend on Railway that owns session validation, conversation configuration, transcript persistence, completion, and OpenAI Realtime credentials. The frontend on Vercel should never hold the OpenAI API key, never invent study assignment data, and never be the authoritative store for research records.

The backend should expose a small HTTP API that matches the participant journey: open a session, start the conversation, receive final transcript turns, create short lived realtime credentials for voice mode, record connection events, and complete the session. Early phases can return fixed sample data and no-op writes so the frontend can integrate against real routes before OpenAI, Postgres, or LangSmith are wired in.

Voice should be a mode on the same session, not a separate product surface. Text turns and voice turns share the same transcript model. Railway remains the source of truth for what was said, when the session started and ended, and which study configuration the participant received.

## Design principles

### Keep study control on the server

Railway should own the system instructions, assigned issue, AI position, voice choice, time limits, prompt versions, avatar versions, and allowed tools. The browser should receive only the configuration needed to render the session. A participant must not be able to change the AI position or system instructions through browser requests.

### Prefer small, explicit endpoints

Each endpoint should map to one participant action or one researcher need. Avoid a single chat endpoint that mixes session lifecycle, media credentials, and research logging. Explicit routes make no-op stubs, tests, and later persistence easier to reason about.

### Make persistence idempotent

Participants refresh pages, retry failed saves, and reconnect after network drops. Creating a turn, reporting a connection event, or completing a session should be safe to retry. Stable IDs and upsert semantics matter more than clever request reduction.

### Separate temporary UI state from research records

Partial transcriptions, input levels, and local timers belong in the browser. Railway should save final turns with stable turn IDs, speaker labels, timestamps, and ordering. LangSmith should receive approved trace data, not become the only copy of the study record.

### Protect secrets and participant data

The OpenAI API key stays on Railway. Short lived Realtime client secrets should be scoped to one configured session. Audio check audio should not be uploaded. Raw conversation audio recording should remain off until consent, retention, encryption, and deletion rules are approved.

## Participant journey mapped to the API

### 1. Open the assigned session

The participant follows a unique study link. The frontend calls the backend to validate the link and load the assigned issue, AI persona, study wave, and session rules.

```http
GET /v1/sessions/{session_id}
```

For the backend prototype, this can return fixed sample session data for known IDs and a clear unavailable response for everything else.

### 2. Read the introduction

No separate endpoint is required. The introduction page uses the session payload from step 1.

### 3. Meet the AI participant

The AI display name, avatar URL, short introduction, and assigned position come from the same session payload. The public response must not include the full system prompt.

### 4. Check audio

The audio check stays in the browser. The backend should not receive audio check media. If the participant switches mode, the frontend can update the preferred interaction mode on the session.

```http
PATCH /v1/sessions/{session_id}
```

### 5. Start the discussion

When the participant enters the conversation screen, the frontend starts or resumes the session. The backend records the start timestamp, marks the session active, and returns the opening AI message configuration if the protocol requires the AI to speak first.

```http
POST /v1/sessions/{session_id}/start
```

For voice mode, the frontend then requests a short lived OpenAI Realtime client secret.

```http
POST /v1/sessions/{session_id}/realtime/session
```

### 6. Continue the discussion

Final participant and AI turns are saved as they become stable. Connection and mode changes are recorded as events. Partial voice transcripts stay local until finalized.

```http
POST /v1/sessions/{session_id}/turns
POST /v1/sessions/{session_id}/events
GET  /v1/sessions/{session_id}/transcript
```

Text mode can also use a message endpoint that accepts a participant message and returns a stubbed or later real AI reply. Voice mode uses OpenAI Realtime in the browser and posts final turns back to Railway.

```http
POST /v1/sessions/{session_id}/messages
```

### 7. End the discussion

The participant can end early, or the backend can mark the session ready for closing when the assigned time expires. Completion should ask for confirmation in the UI, then call a dedicated complete endpoint.

```http
POST /v1/sessions/{session_id}/complete
```

### 8. Confirm completion

The completion page reads the final session status and next study instruction from the session resource. If saving failed earlier, the frontend retries turn and completion writes while keeping local state.

```http
GET /v1/sessions/{session_id}
```

## API surface

All routes use a `/v1` prefix. Responses use JSON. Errors use a consistent problem shape.

### Health

| Method | Path | Purpose | Phase 1 behavior |
| --- | --- | --- | --- |
| `GET` | `/health` | Liveness for Railway and local checks | Return `{ "status": "ok" }` |
| `GET` | `/ready` | Readiness once dependencies exist | Return ok even if DB and OpenAI are not wired yet |

### Sessions

| Method | Path | Purpose | Phase 1 behavior |
| --- | --- | --- | --- |
| `GET` | `/v1/sessions/{session_id}` | Load session config and status for the participant UI | Return sample session or `404` / `410` unavailable |
| `PATCH` | `/v1/sessions/{session_id}` | Update allowed participant preferences such as mode | Accept body, mutate in-memory sample, return updated session |
| `POST` | `/v1/sessions/{session_id}/start` | Mark session started and return opening state | Set status to `active`, return opening AI turn stub |
| `POST` | `/v1/sessions/{session_id}/complete` | Idempotently complete the session | Set status to `completed`, return next instruction |
| `GET` | `/v1/sessions/{session_id}/transcript` | Fetch ordered final turns | Return scripted sample transcript |

### Conversation

| Method | Path | Purpose | Phase 1 behavior |
| --- | --- | --- | --- |
| `POST` | `/v1/sessions/{session_id}/messages` | Accept a text turn and return an AI reply | Append both turns in memory; return a scripted AI reply |
| `POST` | `/v1/sessions/{session_id}/turns` | Upsert one or more final transcript turns | Accept payload, store in memory, ignore duplicates by `turn_id` |
| `POST` | `/v1/sessions/{session_id}/events` | Record connection, mode, mute, interrupt, and error events | Accept payload and acknowledge without durable storage |

### Realtime voice

| Method | Path | Purpose | Phase 1 behavior |
| --- | --- | --- | --- |
| `POST` | `/v1/sessions/{session_id}/realtime/session` | Create a short lived OpenAI Realtime client secret | Return a clearly fake stub secret and expires_at, or `501` until Phase 3 |
| `POST` | `/v1/sessions/{session_id}/realtime/refresh` | Rotate the client secret for an active session | Same no-op stub behavior as create |

### Internal researcher routes later

Do not expose researcher search or administration on the participant API. A later protected route group can cover study wave setup, session minting, transcript export, and prompt version inspection. Keep that out of the first backend build.

```text
/v1/admin/...   deferred
```

## Data models

Use Pydantic v2 models as the public contract. Even when endpoints are no-ops, request and response bodies should validate. Internal persistence models can diverge later, but the API shapes below should stay stable enough for the Vercel client.

### Shared enums and primitives

```python
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class SessionStatus(StrEnum):
    pending = "pending"
    active = "active"
    completing = "completing"
    completed = "completed"
    expired = "expired"
    unavailable = "unavailable"
    paused = "paused"


class InteractionMode(StrEnum):
    voice = "voice"
    text = "text"


class Speaker(StrEnum):
    participant = "participant"
    ai = "ai"
    system = "system"


class ConnectionState(StrEnum):
    idle = "idle"
    listening = "listening"
    thinking = "thinking"
    speaking = "speaking"
    muted = "muted"
    reconnecting = "reconnecting"
    disconnected = "disconnected"
    finished = "finished"


class SessionEventType(StrEnum):
    session_opened = "session_opened"
    session_started = "session_started"
    mode_changed = "mode_changed"
    microphone_permission = "microphone_permission"
    muted = "muted"
    unmuted = "unmuted"
    interrupted_ai = "interrupted_ai"
    connection_lost = "connection_lost"
    connection_restored = "connection_restored"
    realtime_connected = "realtime_connected"
    realtime_failed = "realtime_failed"
    safety_triggered = "safety_triggered"
    session_completed = "session_completed"
    client_reported_problem = "client_reported_problem"
```

### Public session configuration

The participant UI needs enough data to render introduction, avatar, issue, and controls. It must not receive the full system prompt.

```python
class IssueConfig(BaseModel):
    issue_id: str
    title: str
    summary: str


class AiPersonaPublic(BaseModel):
    display_name: str
    label: str = "AI participant"
    short_introduction: str
    avatar_url: HttpUrl
    avatar_version: str
    voice_name: str | None = None
    voice_version: str | None = None
    assigned_position: str


class SessionRules(BaseModel):
    target_duration_seconds: int = Field(ge=60, le=3600)
    warn_remaining_seconds: int = Field(default=60, ge=0)
    allow_interrupt: bool = True
    allow_text_fallback: bool = True
    ai_speaks_first: bool = True
    show_exact_remaining_time: bool = False
    allow_resume: bool = True


class SessionPublic(BaseModel):
    session_id: UUID
    status: SessionStatus
    study_wave: str
    issue: IssueConfig
    ai_persona: AiPersonaPublic
    prompt_version: str
    rules: SessionRules
    preferred_mode: InteractionMode = InteractionMode.voice
    started_at: datetime | None = None
    ends_at: datetime | None = None
    completed_at: datetime | None = None
    next_instruction: str | None = None
```

### Internal session configuration

Keep server only fields in a separate model used by Railway services, never returned to the browser.

```python
class SessionInternal(SessionPublic):
    system_instructions: str
    openai_realtime_model: str
    langsmith_project: str | None = None
    assignment_seed: str | None = None
```

### Transcript turns

```python
class TranscriptTurn(BaseModel):
    turn_id: UUID
    session_id: UUID
    speaker: Speaker
    sequence: int = Field(ge=0)
    text: str
    source_mode: InteractionMode
    created_at: datetime
    client_created_at: datetime | None = None
    interrupted: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)


class TranscriptTurnCreate(BaseModel):
    turn_id: UUID
    speaker: Speaker
    sequence: int = Field(ge=0)
    text: str
    source_mode: InteractionMode
    client_created_at: datetime | None = None
    interrupted: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)


class TranscriptTurnBatchCreate(BaseModel):
    turns: list[TranscriptTurnCreate] = Field(min_length=1)


class TranscriptResponse(BaseModel):
    session_id: UUID
    turns: list[TranscriptTurn]
```

### Messages for text mode

```python
class MessageCreate(BaseModel):
    client_message_id: UUID
    text: str = Field(min_length=1, max_length=8000)
    client_created_at: datetime | None = None


class MessageResponse(BaseModel):
    participant_turn: TranscriptTurn
    ai_turn: TranscriptTurn
    status: SessionStatus
```

### Session lifecycle requests

```python
class SessionUpdate(BaseModel):
    preferred_mode: InteractionMode | None = None


class SessionStartRequest(BaseModel):
    preferred_mode: InteractionMode = InteractionMode.voice
    client_started_at: datetime | None = None


class SessionStartResponse(BaseModel):
    session: SessionPublic
    opening_turn: TranscriptTurn | None = None


class SessionCompleteRequest(BaseModel):
    reason: str = "participant_ended"
    client_completed_at: datetime | None = None
    final_turns: list[TranscriptTurnCreate] = Field(default_factory=list)


class SessionCompleteResponse(BaseModel):
    session: SessionPublic
    saved_turn_count: int
```

### Events

```python
class SessionEventCreate(BaseModel):
    event_id: UUID
    event_type: SessionEventType
    occurred_at: datetime
    connection_state: ConnectionState | None = None
    detail: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class SessionEvent(SessionEventCreate):
    session_id: UUID
    received_at: datetime


class SessionEventAck(BaseModel):
    accepted: bool = True
    event_id: UUID
```

### Realtime credentials

```python
class RealtimeSessionCreateRequest(BaseModel):
    preferred_mode: InteractionMode = InteractionMode.voice


class RealtimeSessionResponse(BaseModel):
    session_id: UUID
    client_secret: str
    expires_at: datetime
    realtime_model: str
    voice_name: str | None = None
    # Never include the full system prompt here if the browser can avoid it.
    # If OpenAI requires server-side session configuration, configure it on Railway
    # when minting the secret and return only browser connection fields.
```

### Error shape

```python
class ApiError(BaseModel):
    error: str
    message: str
    session_status: SessionStatus | None = None
    retryable: bool = False
```

Common error codes:

* `session_not_found`
* `session_unavailable`
* `session_already_completed`
* `session_not_started`
* `invalid_turn_sequence`
* `realtime_unavailable`
* `validation_error`
* `internal_error`

## Recommended backend setup

Use FastAPI with Python 3.12+, Pydantic v2, and `uv` for dependency management. Deploy the API service to Railway. Keep OpenAI and LangSmith credentials in Railway environment variables.

A practical source structure would be:

```text
backend/
  app/
    main.py
    api/
      router.py
      health.py
      sessions.py
      turns.py
      messages.py
      events.py
      realtime.py
    models/
      enums.py
      session.py
      transcript.py
      events.py
      realtime.py
      errors.py
    services/
      sessions.py
      transcripts.py
      realtime.py
      tracing.py
    sample_data/
      sessions.py
      transcripts.py
    core/
      config.py
      dependencies.py
  tests/
    test_health.py
    test_sessions.py
    test_turns.py
    test_messages.py
  pyproject.toml
  README.md
```

Phase 1 can keep session and transcript state in process memory behind service interfaces. Phase 2 can add Postgres without changing route shapes. Phase 3 can implement OpenAI Realtime minting and LangSmith tracing behind the same service boundaries.

## Voice architecture from the backend

The production connection flow should be:

1. The participant starts voice mode in the Vercel UI.
2. The UI calls `POST /v1/sessions/{session_id}/start`.
3. The UI calls `POST /v1/sessions/{session_id}/realtime/session`.
4. Railway validates the study session and creates a short lived OpenAI client secret for a server configured realtime session.
5. The browser uses the short lived secret to establish a WebRTC connection with OpenAI.
6. The browser sends and receives structured conversation events through the WebRTC data channel.
7. The UI posts final transcript turns and session events to Railway.
8. Railway stores the authoritative study record and sends approved trace data to LangSmith.

Railway should configure the realtime session with the assigned instructions, voice, and model. The standard OpenAI API key must stay on Railway. The short lived client secret should be scoped to one configured realtime session.

Do not assume LangSmith stores raw voice recordings. LangSmith can trace model calls, events, and transcript data. Raw audio retention is a separate research and storage decision.

## Backend prototype phases

### Phase 1. Contract and no-op API

Build the FastAPI app with health routes, Pydantic models, and all participant endpoints listed above. Use in-memory sample sessions and scripted transcripts. Writes should validate input and update memory, but should not call OpenAI, Postgres, or LangSmith.

The first review should answer:

* Do the routes cover the UI participant journey?
* Are the public models enough for the Vercel pages without leaking system prompts?
* Are turn and completion writes idempotent in the stub?
* Can the frontend replace mocks with real HTTP calls against local Railway or `fastapi dev`?

### Phase 2. Persistence and session rules

Add durable storage for sessions, turns, events, and completion state. Enforce status transitions, resume rules, duplicate turn protection, and unavailable states for expired or completed links.

The phase should include tests for refresh during a session, duplicate complete requests, out of order turn delivery, and opening the same session twice.

### Phase 3. Realtime, OpenAI, and LangSmith

Mint real OpenAI Realtime client secrets from Railway. Persist final voice and text turns. Add reconnect and secret refresh behavior. Send approved traces to LangSmith without making LangSmith the only source of transcript truth.

The study team should run pilot sessions across Safari, Chrome, mobile Safari, and common campus network conditions before using the system with participants.

## Data and research controls

Each saved session should include a server generated session ID, study wave, assigned issue, assigned AI position, prompt version, avatar version, voice version, timestamps, connection events, transcript turns, and completion status.

Prompt, avatar, and voice versions should be fixed and recorded for each study wave. Changing any of them can change participant behavior, so the researchers need enough version data to identify which participants received each configuration.

The system should define what happens when:

* A participant refreshes the page.
* A connection drops during an AI response.
* The microphone permission is revoked.
* Transcription fails but audio continues.
* The participant leaves early.
* The participant opens the same session on two devices.
* The AI produces unsafe or irrelevant content.
* A complete request arrives with final turns already saved.
* A realtime secret expires while the session is still active.

Recommended defaults for the first backend implementation:

* Refresh reloads `GET /v1/sessions/{session_id}` and `GET /v1/sessions/{session_id}/transcript`.
* Duplicate `turn_id` values upsert rather than insert.
* Duplicate complete requests return the existing completed session.
* Two devices may load the same session, but only one active writer should be trusted once persistence exists; Phase 2 should choose an explicit rule.
* Safety pauses or ends should become session events plus a status change.

## Decisions needed before production backend work

The study team should decide:

1. Whether voice is required, preferred, or optional.
2. Whether raw participant or AI audio is recorded.
3. Whether participants can interrupt the AI.
4. Whether participants see exact remaining time.
5. Whether participants can edit a spoken transcript before it is saved.
6. Whether the AI always speaks first.
7. How the study assigns topics, positions, avatars, and voices.
8. Whether a participant can resume an interrupted session.
9. What safety rules end or pause a session.
10. What the completion page should ask the participant to do next.
11. Whether study links are opaque session IDs, signed tokens, or both.
12. How long realtime client secrets should live.
13. Which transcript fields are exported to LangSmith versus kept only in the study database.
14. Whether text mode uses Railway mediated model calls or the same OpenAI Realtime path with text only.

## Initial scope

The first backend build should include the FastAPI app skeleton, health checks, Pydantic request and response models, participant session routes, turn and event write routes, text message route, realtime credential route stubs, in-memory sample data, and basic route tests.

The first build should exclude Postgres, authentication for researchers, OpenAI calls, LangSmith, raw audio storage, scoring, admin APIs, and generated video. Excluding those systems keeps the first review focused on whether the API contract can support the UI flow and later study requirements.
