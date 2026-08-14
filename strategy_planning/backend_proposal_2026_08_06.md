# Backend proposal

## Recommendation

The first version should be a FastAPI study backend on Railway. FastAPI is a Python library for building HTTP APIs. Railway should handle session validation, conversation configuration, transcript storage, session completion, and OpenAI Realtime credentials. OpenAI Realtime is OpenAI's live voice and text conversation API.

The Vercel frontend should not hold the OpenAI API key. It should not invent study assignment data. It should not be the place research records are kept.

The backend should expose a small HTTP API that follows the participant journey:

* Open a session.
* Start the conversation.
* Receive final transcript turns.
* Create Realtime credentials that expire quickly, for voice mode.
* Record connection events.
* Complete the session.

Early phases can return fixed sample data, and they can accept writes that only update memory. The frontend can then call real routes before OpenAI, Postgres, or LangSmith are added.

Voice should be a mode on the same session. Text turns and voice turns should use the same transcript model. Railway is the source of truth for what was said, when the session started and ended, and which study configuration the participant received.

## Design principles

### Keep study control on the server

Keep these fields on Railway:

* System instructions
* Assigned issue
* AI position
* Voice choice
* Time limits
* Prompt versions
* Avatar versions
* Allowed tools

The browser should receive only the configuration needed to show the session. A participant must not be able to change the AI position or system instructions through browser requests.

### Prefer small, explicit endpoints

Each endpoint should map to one participant action or one researcher need. Do not put session lifecycle, media credentials, and research logging on one chat endpoint. Small routes are easier to test. They are also easier to return sample data from, and easier to persist later.

### Make writes safe to retry

Participants refresh pages, retry failed saves, and reconnect after network drops. Creating a turn should be safe to retry. Reporting a connection event should be safe to retry. Completing a session should be safe to retry.

Use stable IDs. If a turn with the same `turn_id` already exists, update it instead of inserting a second copy. Writes that are safe to retry are more important than fewer requests.

### Separate temporary UI state from research records

Keep partial transcriptions, input levels, and local timers in the browser. Save final turns on Railway with stable turn IDs, speaker labels, timestamps, and ordering. Send approved trace data to LangSmith. Do not treat LangSmith as the only copy of the study record.

### Protect secrets and participant data

Keep the OpenAI API key on Railway. A Realtime client secret should expire quickly, and it should apply to one configured session only. Do not upload audio from the audio check. Do not record raw conversation audio yet. Record it only after the study team approves consent, retention, encryption, and deletion rules.

## Participant journey mapped to the API

### 1. Open the assigned session

The participant follows a unique study link. The frontend calls the backend to validate the link and load the assigned issue, AI persona, study wave, and session rules.

```http
GET /v1/sessions/{session_id}
```

For the backend prototype, known IDs can return fixed sample session data. Unknown IDs should return a clear unavailable response.

### 2. Read the introduction

The introduction page does not need its own endpoint. It uses the session payload from step 1.

### 3. Meet the AI participant

The same session payload includes the AI display name, avatar URL, short introduction, and assigned position. The public response must not include the full system prompt.

### 4. Check audio

The audio check stays in the browser. The backend should not receive audio check media. If the participant switches mode, the frontend can update the preferred interaction mode on the session.

```http
PATCH /v1/sessions/{session_id}
```

### 5. Start the discussion

When the participant enters the conversation screen, the frontend starts or resumes the session. The backend should record the start timestamp and mark the session active. If the protocol requires the AI to speak first, the response should include the opening AI message configuration.

```http
POST /v1/sessions/{session_id}/start
```

For voice mode, the frontend then requests an OpenAI Realtime client secret that expires quickly.

```http
POST /v1/sessions/{session_id}/realtime/session
```

### 6. Continue the discussion

Save final participant and AI turns when the text is stable. Record connection changes and mode changes as events. Keep partial voice transcripts in the browser until they are final.

```http
POST /v1/sessions/{session_id}/turns
POST /v1/sessions/{session_id}/events
GET  /v1/sessions/{session_id}/transcript
```

Text mode can also use a message endpoint that accepts a participant message and returns a sample AI reply, and later a real AI reply. Voice mode uses OpenAI Realtime in the browser and posts final turns back to Railway.

```http
POST /v1/sessions/{session_id}/messages
```

### 7. End the discussion

The participant can end early. The backend can also mark the session ready for closing when the assigned time expires. The UI should ask for confirmation, then call a dedicated complete endpoint.

```http
POST /v1/sessions/{session_id}/complete
```

### 8. Confirm completion

The completion page reads the final session status and next study instruction from the session resource. If saving failed earlier, the frontend retries turn and completion writes while keeping local state.

```http
GET /v1/sessions/{session_id}
```

## HTTP routes

All routes use a `/v1` prefix. Responses are JSON. Errors use one shared error shape.

### Health

| Method | Path | Purpose | Phase 1 behavior |
| --- | --- | --- | --- |
| `GET` | `/health` | Show that the process is running, for Railway and local checks | Return `{ "status": "ok" }` |
| `GET` | `/ready` | Show that the app can take traffic once dependencies exist | Return ok even if DB and OpenAI are not added yet |

### Sessions

| Method | Path | Purpose | Phase 1 behavior |
| --- | --- | --- | --- |
| `GET` | `/v1/sessions/{session_id}` | Load session config and status for the participant UI | Return sample session or `404` / `410` unavailable |
| `PATCH` | `/v1/sessions/{session_id}` | Update allowed participant preferences such as mode | Accept body, update the in-memory sample, return updated session |
| `POST` | `/v1/sessions/{session_id}/start` | Mark session started and return opening state | Set status to `active`, return opening AI turn sample |
| `POST` | `/v1/sessions/{session_id}/complete` | Complete the session in a way that is safe to retry | Set status to `completed`, return next instruction |
| `GET` | `/v1/sessions/{session_id}/transcript` | Fetch ordered final turns | Return scripted sample transcript |

### Conversation

| Method | Path | Purpose | Phase 1 behavior |
| --- | --- | --- | --- |
| `POST` | `/v1/sessions/{session_id}/messages` | Accept a text turn and return an AI reply | Append both turns in memory; return a scripted AI reply |
| `POST` | `/v1/sessions/{session_id}/turns` | Create or update one or more final transcript turns | Accept payload, store in memory, update an existing turn when `turn_id` matches |
| `POST` | `/v1/sessions/{session_id}/events` | Record connection, mode, mute, interrupt, and error events | Accept payload and acknowledge without durable storage |

### Realtime voice

| Method | Path | Purpose | Phase 1 behavior |
| --- | --- | --- | --- |
| `POST` | `/v1/sessions/{session_id}/realtime/session` | Create an OpenAI Realtime client secret that expires quickly | Return a fake secret and expires_at, or `501` until Phase 3 |
| `POST` | `/v1/sessions/{session_id}/realtime/refresh` | Rotate the client secret for an active session | Same sample behavior as create |

### Internal researcher routes later

Do not put researcher search or administration on the participant API. Leave researcher routes out of the first backend build. A later protected route group can cover:

* Study wave setup
* Session creation
* Transcript export
* Prompt version inspection

```text
/v1/admin/...   deferred
```

## Data models

Use Pydantic v2 models as the public contract. Pydantic is the library FastAPI uses to validate request and response bodies. Even when an endpoint only updates memory, the request and response bodies should still validate. Internal storage models can change later. The API shapes in this section should stay stable enough for the Vercel client.

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

The participant UI needs enough data to show the introduction, avatar, issue, and controls. It must not receive the full system prompt.

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

Keep server-only fields in a separate model that Railway services use. Never return the internal fields to the browser.

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
    # Do not include the full system prompt if the browser can connect without it.
    # If OpenAI requires session configuration on the server, set that configuration
    # on Railway when creating the secret, and return only the fields the browser
    # needs to connect.
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

A useful source layout is:

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

Phase 1 can keep session and transcript state in process memory, behind functions that the routes call. Phase 2 can add Postgres without changing the route shapes. Phase 3 can create OpenAI Realtime credentials and send LangSmith traces using those same functions.

## Voice architecture from the backend

The production connection flow should be:

1. The participant starts voice mode in the Vercel UI.
2. The UI calls `POST /v1/sessions/{session_id}/start`.
3. The UI calls `POST /v1/sessions/{session_id}/realtime/session`.
4. Railway validates the study session and creates an OpenAI client secret that expires quickly, for a realtime session that Railway configured.
5. The browser uses the secret to establish a WebRTC connection with OpenAI. WebRTC is the browser API for live audio and data.
6. The browser sends and receives structured conversation events through the WebRTC data channel.
7. The UI posts final transcript turns and session events to Railway.
8. Railway stores the study record and sends approved trace data to LangSmith.

Railway should configure the realtime session with the assigned instructions, voice, and model. The standard OpenAI API key must stay on Railway. The client secret that expires quickly should apply to one configured realtime session only.

Do not assume LangSmith stores raw voice recordings. LangSmith can trace model calls, events, and transcript data. Whether to keep raw audio is a separate research and storage decision.

## Backend prototype phases

### Phase 1. Routes and sample data

Build the FastAPI app with health routes, Pydantic models, and all participant endpoints listed above. Use in-memory sample sessions and scripted transcripts. Writes should validate input and update memory. Writes should not call OpenAI, Postgres, or LangSmith.

The first review should answer:

* Do the routes cover the UI participant journey?
* Are the public models enough for the Vercel pages without leaking system prompts?
* Are turn and completion writes safe to retry in the sample implementation?
* Can the frontend replace mocks with real HTTP calls against local Railway or `fastapi dev`?

### Phase 2. Persistence and session rules

Add durable storage for sessions, turns, events, and completion state. Enforce status transitions. Enforce resume rules. Reject duplicate turns. Return unavailable states for expired or completed links.

The phase should include tests for:

* Refresh during a session.
* Duplicate complete requests.
* Out of order turn delivery.
* Opening the same session twice.

### Phase 3. Realtime, OpenAI, and LangSmith

Create real OpenAI Realtime client secrets from Railway. Save final voice and text turns. Add reconnect and secret refresh behavior. Send approved traces to LangSmith, and keep the study transcript on Railway as well.

The study team should run pilot sessions across Safari, Chrome, mobile Safari, and common campus network conditions before using the system with participants.

## Data and research controls

Each saved session should include:

* A server generated session ID
* Study wave
* Assigned issue
* Assigned AI position
* Prompt version, avatar version, and voice version
* Timestamps
* Connection events
* Transcript turns
* Completion status

Prompt, avatar, and voice versions should be fixed and recorded for each study wave. Changing any of them can change participant behavior, so the researchers need enough version data to identify which participants received each configuration.

The study team should define what happens when:

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
* Duplicate `turn_id` values update the existing turn rather than insert a second copy.
* Duplicate complete requests return the existing completed session.
* Two devices may load the same session, but only one active writer should be trusted once persistence exists. Phase 2 should choose an explicit rule.
* Safety pauses or ends should be stored as session events, and they should change the session status.

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
11. Whether study links are unguessable session IDs, signed tokens, or both.
12. How long realtime client secrets should live.
13. Which transcript fields are exported to LangSmith versus kept only in the study database.
14. Whether text mode sends model calls through Railway, or uses the same OpenAI Realtime path with text only.

## Initial scope

The first backend build should include:

* The FastAPI app skeleton
* Health checks
* Pydantic request and response models
* Participant session routes
* Turn and event write routes
* The text message route
* Realtime credential routes that return sample data
* In-memory sample data
* Basic route tests

The first build should exclude:

* Postgres
* Authentication for researchers
* OpenAI calls
* LangSmith
* Raw audio storage
* Scoring
* Admin APIs
* Generated video

The first review should check whether the API contract can support the UI flow and later study requirements.
