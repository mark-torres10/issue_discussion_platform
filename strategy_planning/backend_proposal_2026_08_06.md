# Backend proposal

## Recommendation

The first shipped Study API should be a FastAPI service on Railway. FastAPI is a Python library for building HTTP APIs. Railway is the host that runs the Study API and workers. Study Postgres is the private database that stores the study record. The Study API should validate participant access, apply session rules, store transcripts, complete sessions, mediate text generation, and set up OpenAI Realtime. OpenAI Realtime is OpenAI's live voice and text conversation API.

The Vercel frontend should not hold the OpenAI API key. The frontend should not invent study assignment data. The frontend should not be the place research records are kept.

LangSmith should receive a derived projection of approved traces after records are committed. LangSmith is not the study record. Supabase Auth proves staff identity only. Participant access does not use Supabase Auth.

Voice is a mode on the same session. Text turns and voice turns use the same canonical transcript model. "Voice" in the first integration means approved configuration, interruption state, and approved timing and usage fields. The first integration does not record raw conversation audio.

## Named components

Name each part of the system in plans, logs, and runbooks.

| Component | Owns | Must not own |
| --- | --- | --- |
| Participant UI | Microphone permission, local audio state, temporary partial text, and client observations | Study assignment, canonical AI turns, model credentials, completion truth, or research exports |
| Study API | Capability validation, lifecycle rules, concurrency control, text generation commands, Realtime setup, and staff authorization | Long running LangSmith delivery inside a participant request |
| Study Postgres | Sessions, immutable configuration snapshots, canonical turns, revisions, events, completion, audit records, and any selected delivery state | Model trace rendering |
| Railway | Process hosting for the Study API and workers | Data ownership |
| Realtime control worker | Authenticated call ID handoff, sideband monitoring, provider event ingestion, tool handling, and provider identifier mapping | Participant identity or study analysis |
| Trace export worker, if complete export is required later | Redacted LangSmith projection, retries, persisted run IDs, and reconciliation | Authoritative transcript mutation |
| LangSmith | Derived traces, thread views, latency, usage, cost, and later experiments | Participant access control, canonical transcripts, consent truth, or completion state |
| Supabase Auth | Staff identity and sessions | Participant link access, or Study API authorization decisions by itself |

v1 may treat the product as one study. `study_id` still exists on sessions, snapshots, exports, and audit records. The Study API still checks membership for every staff object lookup.

## Design principles

### Keep study control on the Study API

Keep the following fields in Study Postgres and apply them only through the Study API:

* System instructions, or a content hash and immutable object reference
* Assigned issue
* AI position
* Voice choice
* Time limits
* Prompt versions
* Avatar versions
* Allowed tools
* Configuration snapshot contents listed later in the document

The browser should receive only the configuration needed to show the session. A participant must not be able to change the AI position or system instructions through browser requests.

### Prefer small, explicit endpoints

Each participant endpoint should map to one command or one read. Do not put session lifecycle, media setup, and research logging on one chat endpoint. Small routes are easier to test. They are also easier to return sample data from, and easier to persist later.

### Make writes safe to retry without mutation

Participants refresh pages, retry failed saves, and reconnect after network drops. Creating a turn should be safe to retry. Reporting an observation should be safe to retry. Completing a session should be safe to retry.

Canonical turns are immutable. If a turn with the same `turn_id` and the same content hash already exists, return the stored turn. If the same `turn_id` arrives with different immutable content, return `409 turn_conflict`. Corrections are new revision records.

### Separate temporary UI state from research records

Keep partial transcriptions, input levels, and local timers in the browser. Save canonical turns in Study Postgres with stable turn IDs, speaker labels, server timestamps, and server order. Send approved trace data to LangSmith only from committed records. Do not treat LangSmith as the only copy of the study record.

### Protect secrets and participant data

Keep the OpenAI API key on the Study API host. The browser receives an SDP answer for Realtime, never the standard API key and never the OpenAI call ID. Do not upload audio from the audio check. Do not record raw conversation audio in v1.

### Commands are not observations

The public models must separate commands from observations. The browser may send participant text and allowlisted client observations. The browser may not create AI turns, system turns, token counts, or canonical order. Provider usage, model identity, and server timing use trusted server or provider fields.

## Shared milestones

Work is described with named milestones, not numbered phases. The same names should appear in UI, Auth, and LangSmith plans.

| Milestone | Meaning for the Study API |
| --- | --- |
| Sample contracts | Routes and contracts are frozen. Sample or in-memory data is allowed. |
| Durable record | Study Postgres is authoritative. The same contract suite passes against memory and Postgres. |
| Voice control | Server-mediated Realtime plus the sideband worker run in staging. |
| Approved tracing | A trace policy version is approved. An export worker is optional. |
| Research export | Versioned study exports exist. Later LangSmith datasets may be built from those exports. |

## Participant access

Participant access is a capability, not a public `session_id`. Supabase Auth is not used on participant routes.

### Invitation token

Each invitation has a random, single-purpose link token that is separate from the internal `session_id`. Store only a hash of the token. Do not store the raw token. Keep the internal `session_id` out of public URLs, browser history fields the Study API controls, and LangSmith metadata.

### Exchange

`POST /v1/participant-access/exchange` accepts the invitation token once for a writer capability. A later presentation of the same invitation token, until the session is completed, expired, or revoked, may issue only a read-only capability. The exchange sets a short-lived HTTP-only participant capability cookie and returns `ParticipantSessionView`. The internal `session_id` is not placed in the public path.

### Capability cookie

The capability is required on every participant read and write, including Realtime setup. Scope the capability to one session and a small set of allowed actions. Rotate or revoke the capability when the session is completed, expired, or invalidated.

Cookie settings:

* `HttpOnly`
* `Secure`
* `SameSite=None` when the Vercel origin and the Study API origin differ, because the browser must send the cookie on cross-site credentialed requests
* `Path` limited to participant routes
* Lifetime of 2 hours, or until session completion if completion is earlier
* `Max-Age` and `Expires` aligned with that lifetime

The Vercel site and the Study API are expected to be different sites, so `SameSite=Lax` would drop the cookie on most API calls.

### CORS

Allow only the configured Vercel origin. Allow credentials. Do not use `*`. Reject requests whose `Origin` is missing or not on the allowlist for state-changing methods.

### CSRF

CORS is not a CSRF control. CSRF is a browser attack that sends a request using the user's cookies. For cookie-based participant capabilities, require both of the following:

* Strict `Origin` (and `Referer` when `Origin` is absent) matching the allowlist
* A CSRF token issued at exchange, required on every state-changing participant request in a header such as `X-CSRF-Token`. The CSRF token is readable by the UI. The capability cookie is not.

### Replay

A used invitation token must not mint a second writer capability. A stolen capability cookie is valid until expiry or revocation. Rate limit exchange so token guessing is slow.

### Second device

The first successful writer exchange receives the writer lease. A second device that exchanges the invitation token receives a read-only capability. The second device may load the public session view and transcript. The second device may not start generation, complete the session, or set up Realtime until an explicit writer transfer succeeds. A stale writer that still holds an expired or superseded lease receives `409 writer_conflict`.

### Rate limits on access

Rate limit token exchange, Realtime setup, messages, observations, and completion per invitation hash, per capability, and per IP. Return `429` with `retry_after_seconds`.

## Concurrency

The plan chooses one active writer lease with explicit transfer. Other designs exist, such as optimistic versions alone or row locks alone. v1 uses a lease plus `expected_version` on lifecycle writes.

Lease rules:

* The Study API issues `writer_lease_id` at writer exchange or at start if the exchange did not yet start the session. The lease lasts 30 minutes from last successful write, and it is renewed on each accepted write.
* Write commands require a current lease and a matching `expected_version` where listed.
* A stale writer receives `409 writer_conflict` with `current_version` and no mutation.
* Transfer is `POST /v1/participant-session/writer-lease/transfer`. The current writer posts a one-time transfer nonce that the Study API issued to the read-only device. Staff with membership can also transfer. Transfer moves the lease to a device that already holds a valid read-only capability for the same session.
* After transfer, the old lease cannot write.

Database tests must run simultaneous start, message, voice ingestion, refresh, and completion requests from separate API instances.

## Session state

`unavailable` is an API projection, not a persisted session status, unless staff explicitly quarantine a session. Quarantine, if added later, is a separate persisted flag or status. The v1 persisted statuses are `pending`, `active`, `paused`, `completed`, and `expired`.

`completing` is not a status the UI should poll. The complete command moves `active` or `paused` to `completed` in one transaction. If a crash happens inside that transaction, the session remains `active` or `paused` and the client retries complete.

A completed session stays readable to the same participant capability for 24 hours after `completed_at`. Completion rotates the writer lease so new writes fail, and it keeps a read-only capability on the same cookie until the grace period ends. The completed projection includes status, completion time, and next instruction. Conversation writes and new Realtime setup are blocked after completion. Return `410` only after the grace period or after explicit revocation. A completed session is not projected as unavailable during the grace period.

Each session has a monotonic `version`. Lifecycle writes require `expected_version`.

### State transitions

```text
pending -> active
pending -> expired
active -> paused
paused -> active
active -> completed
paused -> completed
active -> expired
paused -> expired
```

| From | To | Actor | Preconditions | Transaction | Idempotency | Allowed writes after | HTTP result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pending | active | Participant start command with writer lease | Capability valid, consent gate passed when required, `expected_version` matches | Set `started_at`, increment version, issue or confirm lease, return stored opening content when `ai_speaks_first` is true | Same `Idempotency-Key` and hash return the stored start response | Messages, observations, Realtime setup, complete | `200` |
| pending | expired | Study API time job or staff | `ends_at` or invitation expiry passed while still pending | Set `expired`, increment version, revoke writer writes | Repeat returns the expired projection | Reads only | `200` for staff job, participant reads may be `410` after grace |
| active | paused | Participant, safety rule, or staff | Writer lease for participant pause | Set paused, increment version | Same key returns stored pause | Observations, resume start, complete | `200` |
| paused | active | Participant resume with writer lease | `allow_resume` on snapshot, lease valid | Set active, increment version | Same key returns stored resume | Same as active | `200` |
| active or paused | completed | Complete command | Lease, `expected_version`, immutable turn rules | See completion section. Completing is not a stored intermediate status. | Same key and hash return stored complete response | Reads for the 24 hour grace period | `200` |
| active or paused | expired | Time job | Assigned duration or hard stop reached without complete | Set expired, increment version, revoke writes | Repeat is a no-op | Reads for grace period | Job `200` |

A missing session, a revoked invitation, or a read after grace period is projected as unavailable through `404` or `410`. Do not persist `unavailable` for those cases.

## Participant journey mapped to the API

### Open the assigned session

The participant follows a unique study link that contains the invitation token, not the internal `session_id`. The UI calls exchange, then reads the participant session view.

```http
POST /v1/participant-access/exchange
GET  /v1/participant-session
```

For Sample contracts, known invitation hashes can return fixed sample session data. Unknown tokens return an unavailable projection.

### Read the introduction

The introduction page does not need its own endpoint. The page uses `ParticipantSessionView`.

### Meet the AI participant

The same view includes the AI display name, avatar URL, short introduction, and assigned position. The public response must not include the full system prompt.

### Check audio

The audio check stays in the browser. The Study API should not receive audio check media. Preferred mode is sent on start. A later constrained mode command may exist for an active writer. A general public session upsert must not exist.

### Start the discussion

When the participant enters the conversation screen, the UI calls start. The Study API records the start timestamp and marks the session active.

If the configuration snapshot has `ai_speaks_first` true, start returns stored opening content from the snapshot so the UI can render it immediately. Start does not imply that OpenAI Realtime will generate a duplicate opening turn. If `ai_speaks_first` is false, start returns no opening AI turn.

```http
POST /v1/participant-session/start
```

For voice mode, the UI then sends the browser SDP to the Realtime setup route.

```http
POST /v1/participant-session/realtime/calls
```

### Continue the discussion

Save canonical turns only through trusted paths. Record browser connection changes as observations. Keep partial voice transcripts in the browser until a provider item is final or a recovery observation is accepted under the narrow schema.

```http
POST /v1/participant-session/messages
POST /v1/participant-session/observations
GET  /v1/participant-session/transcript
```

Text mode uses `POST /v1/participant-session/messages`. The Study API creates the participant turn, calls the model, and creates the AI turn. Voice mode uses server-mediated Realtime. Final AI voice text is stored from provider events on the sideband path, not from a public turn upsert.

### End the discussion

The participant can end early. The Study API can also move the session toward closing when the assigned time expires. The UI should ask for confirmation, then call complete.

```http
POST /v1/participant-session/complete
```

### Confirm completion

The completion page reads the completed projection and next study instruction from `GET /v1/participant-session` during the grace period. If saving failed earlier, the UI retries complete with the same `Idempotency-Key` while keeping local state.

## Participant API

All participant routes use a `/v1` prefix. Responses are JSON. Errors use one shared error shape. Public input models reject unknown fields.

The browser does not choose a `session_id` on every request. The capability cookie selects the session.

| Method and path | Input | Authority and retry rule |
| --- | --- | --- |
| `POST /v1/participant-access/exchange` | One-time invitation token | Validates the token hash, sets the participant capability cookie, and returns the participant session view |
| `GET /v1/participant-session` | Participant capability | Returns only the public projection for the capability's session |
| `POST /v1/participant-session/consent` | Consent version, allowed data classes, permitted modes, `Idempotency-Key`, expected version | Records required consent when the protocol requires it. Idempotent for the same version. Withdrawal uses the same route with `withdrawn=true`. |
| `POST /v1/participant-session/start` | Preferred mode, `Idempotency-Key`, and expected session version | Creates one lifecycle transition. When `ai_speaks_first` is true, returns stored opening content from the snapshot. |
| `POST /v1/participant-session/messages` | Participant text, client message ID, and `Idempotency-Key` | Creates participant text and one backend-owned AI generation operation |
| `POST /v1/participant-session/realtime/calls` | Browser SDP, `Idempotency-Key`, and expected session version | Creates one server-configured Realtime call, persists the call ID from the provider `Location` header, queues the control handoff, and returns only the SDP answer |
| `POST /v1/participant-session/observations` | Versioned allowlisted browser observations | Records client observations without turning them into canonical provider facts |
| `GET /v1/participant-session/transcript` | Participant capability and optional cursor | Returns the canonical participant projection in server order |
| `POST /v1/participant-session/complete` | Completion reason, final participant recovery observations, `Idempotency-Key`, and expected session version | Atomically records valid final data and completion |
| `POST /v1/participant-session/pause` | `Idempotency-Key` and expected session version | Moves an active writer session to `paused` when the snapshot allows resume. Paused is still a valid session, not an unavailable projection. |
| `POST /v1/participant-session/writer-lease/transfer` | Transfer nonce from the read-only device, `Idempotency-Key`, expected version | Moves the writer lease. The prior lease cannot write afterward. |

The public API must not expose a general `/turns` upsert. `POST /messages` is the text generation command.

Voice provider items are ingested on an internal worker route, not by the browser:

```http
POST /internal/v1/realtime/calls/{openai_call_id}/items
```

That internal route requires a Railway service credential, not a participant cookie. The worker posts provider-identified final items. The Study API maps each `provider_item_id` to one canonical turn. Browser recovery observations stay on `POST /v1/participant-session/observations` and on the complete request, and they never become canonical AI text unless a matching provider item exists.

Staff APIs use a separate route group. The Vercel UI server forwards the verified Supabase JWT in the `Authorization` header. The Study API verifies that JWT and then checks role and study membership. The browser does not call staff routes with a raw access token in application JavaScript.

### Health

| Method | Path | Purpose | Sample contracts behavior | Later roles |
| --- | --- | --- | --- | --- |
| `GET` | `/health` | Show that the process is running | Return `{ "status": "ok" }` | Same liveness meaning |
| `GET` | `/ready` | Show that the process can serve its configured role | Return ok even if Study Postgres is not configured | Database and worker roles must probe their dependencies |

### Staff routes later

Do not put researcher search or administration on the participant API. Leave researcher routes out of Sample contracts. A later protected route group can cover study wave setup, session creation, transcript export, prompt inspection, corrections, and deletion. Every staff lookup checks `study_id` membership. Require recent authentication for transcript export, role changes, and deletion.

```text
/v1/staff/...   deferred
```

Staff cookie handling lives in the Auth plan. The Study API verifies the forwarded Supabase JWT and server-controlled role claims. The Study API does not treat a browser-supplied user id string as proof.

Staff actions by role, deny by default:

| Action | operator | researcher | study_admin |
| --- | --- | --- | --- |
| Create invitation and session | no | no | yes |
| Read transcript for current `study_id` | yes | yes | yes |
| Export transcript | no | yes, with recent auth | yes, with recent auth |
| Create a correction revision | no | yes | yes |
| Delete or tombstone | no | no | yes, with recent auth |
| Publish a configuration snapshot | no | no | yes |
| Transfer a writer lease | no | no | yes |

v1 may have one `study_id`. Membership rows still name that `study_id`.

## Provenance and turns

Canonical turns are immutable. The Study API assigns canonical order (`ordinal`). Client timestamps are optional evidence, not the canonical order.

Every stored turn includes `origin`, `provider_item_id` when the provider supplied one, `recorded_at`, `content_hash`, and a schema version. Derived traces, when exported, should carry `trace_kind` values such as `instrumented_text_generation`, `provider_observed_realtime_response`, and `client_reconstructed_voice_turn`. A client reconstruction is not a complete model call.

### Who may create which record

* The text message route accepts participant text only. The Study API creates the participant turn, calls the model, and creates the AI turn.
* The browser cannot create a system turn.
* The Study API creates canonical AI turn IDs, or maps a provider conversation item ID to one canonical turn.
* Browser observations use a separate model and are marked as untrusted observations. Examples include first audio heard, local connection state, and microphone permission.
* Provider usage, model identity, and server timing use trusted server or provider fields.
* Arbitrary `metadata` and `detail` dictionaries are replaced with versioned, allowlisted event payloads that have size limits.

### Idempotency for turns

* The same ID and same content hash returns the existing turn.
* The same ID and different immutable content returns `409 turn_conflict`.
* A correction creates a new revision record with an actor, reason, and link to the prior revision.
* Unique constraints cover session plus client event ID, provider item ID, and canonical ordinal where applicable.

Batch recovery writes must be atomic, have a maximum size, and reject the whole batch if one item is invalid.

### Text generation operations

Model text generation as an operation with `accepted`, `running`, `succeeded`, and `failed` states. A retry with the same `Idempotency-Key` and request hash returns the same operation and AI response instead of calling the model again. The Study API mediates text generation, so trace hooks and timing can be frozen for the text path.

### Opening turn

The configuration snapshot decides who speaks first. If `ai_speaks_first` is true, start returns stored opening content from the snapshot so the UI can render it immediately. The stored opening is also the canonical first AI turn when start commits. Realtime setup must include that opening as already-said context when a voice call starts, and must not request an automatic first model response that would duplicate it. If `ai_speaks_first` is false, no opening AI turn is returned or stored at start.

### Interrupted AI turns

Generated text, delivered text, and display text are separate facts.

* `generated_text` is provider generated content.
* `delivered_text` is content delivered before interruption.
* `display_text` is the transcript text shown to the participant.
* Store interruption time and provider item ID.
* A participant approved correction is a revision, not an overwrite.

The research export field for "what the AI said" is chosen in a versioned export manifest. The Study API stores all three text fields regardless of which field a later export selects.

### Voice meaning

The first integration records transcript text, voice configuration, interruption state, and approved timing and usage fields. The first integration does not record raw audio.

## Realtime

The chosen control strategy is server-mediated unified WebRTC setup plus a sideband control worker. WebRTC is the browser API for live audio. SDP is the session description used to start WebRTC. A sideband connection is a second, server-owned connection to the same OpenAI Realtime call.

A sideband connection improves provider event capture and keeps tool execution on the server. A sideband connection does not make the browser unable to send `session.update`. If immutable session configuration is required, the worker must detect unauthorized `session.updated` events, invalidate or quarantine the session, and mark the records.

### Setup flow

1. The participant starts voice mode in the Vercel UI after start succeeds.
2. The UI posts the browser SDP to `POST /v1/participant-session/realtime/calls` with the capability cookie, CSRF token, `Idempotency-Key`, and `expected_version`.
3. The Study API validates the capability, writer lease, consent gate, and snapshot.
4. The Study API submits the SDP with the server-owned session configuration to OpenAI. The trusted request sets `OpenAI-Safety-Identifier` to a privacy-preserving value that is not the invitation token and not the internal `session_id`.
5. The Study API captures the `Location` header, extracts the OpenAI call ID, persists the call ID in Study Postgres, and securely enqueues a control handoff to the sideband worker.
6. The browser receives the SDP answer only. The browser never receives the call ID or the standard API key.
7. The browser sends and receives audio through WebRTC. The browser may send only the listed client events.
8. The worker appends final provider events to durable storage, acknowledges persisted provider item IDs, and exposes a reconciliation cursor.
9. The browser may retry missing client observations. The browser is not the only holder of a final AI turn.

Crash recovery must not depend on IndexedDB unless encryption, expiry, cleanup, and consent are defined first. v1 prefers provider events in Study Postgres.

### Client events the application intends to send

The browser may send only the following Realtime client events:

* `input_audio_buffer.append`
* `input_audio_buffer.commit`
* `input_audio_buffer.clear`
* `response.cancel` when the snapshot allows interrupt

The browser must not send `session.update`. The browser must not send tool results. Unexpected client events, including `session.update`, are unauthorized.

### Unauthorized session updates

The sideband worker watches for `session.updated`. If the update does not match the configuration snapshot, the worker records an audit event, marks the session records, and invalidates the call and the writer capability. Staff review is required before those records enter a research export.

### Tools

Tool calls are handled on the Study API or the control worker using the snapshot tool manifest. The browser does not execute tools. Tool names and versions are part of the snapshot.

### Prior secret or call invalidation

A new Realtime setup for the same session invalidates the prior call ID when a prior call still exists. Reconnect and refresh must not create a second canonical conversation. The worker maps provider item IDs onto existing canonical turns.

### Sideband failure while audio continues

If the sideband connection fails while audio continues, the Study API records `realtime_sideband_disconnected`, keeps the participant UI in a reconnecting or degraded state, and does not treat the in-browser audio as the only copy of a final AI turn. Reconciliation later reports provider item gaps instead of silently treating an incomplete transcript as complete. The UI may send recovery observations, which remain untrusted until matched to a provider item.

### Durable provider ingest

A sideband socket is not a durability guarantee by itself. The Study API and control worker should:

* Append final provider events to Study Postgres
* Acknowledge persisted provider item IDs to the worker cursor
* Expose a reconciliation cursor on an internal staff or worker API
* Distinguish provider usage from browser observations

### Voice timing observations

Record the following separately. Do not subtract unrelated browser and server wall clocks.

* `server_generation_started_at`
* `provider_first_output_at`
* `client_first_audio_observed_ms`
* `client_first_transcript_observed_ms`
* `generation_completed_at`
* `metric_source`
* `clock_basis`

Mark browser values as client observed. Prefer provider events from the sideband connection for canonical operational metrics. Do not use browser supplied token counts or cost as authoritative.

## Text path

The Study API mediates text generation. The UI posts participant text to `POST /v1/participant-session/messages`. The Study API stores the participant turn, calls OpenAI on the server, stores the AI turn, and returns both public projections. Timing and traces for text mode are therefore server-owned. The path is chosen now so LangSmith hooks do not stay undecided.

## LangSmith delivery

The default delivery guarantee is true best effort. Participant requests never wait for LangSmith. Gaps are accepted. The Study API must not claim that every eligible turn appears in LangSmith under best effort.

Build any trace only from committed canonical records. Do not use the internal `session_id` as a public LangSmith identifier. A separate UUID version 7 telemetry thread ID is stored in Study Postgres and may be exported later under an approved policy.

LangSmith failure must not fail session completion. Production tracing stays disabled until an approved trace policy version is attached to the session.

If complete export is later required, an outbox is mandatory. The outbox is not part of the default best-effort contract.

An application feature flag selects a no-operation exporter or, later, an outbox worker. Do not assume `LANGSMITH_TRACING=false` disables every SDK path. Direct run posting can still send data.

Operational connection events may use a separate allowlist and sampling rule. Approved transcript traces, when a complete export policy exists, may need full coverage for reconciliation. Cap runs per session, payload size, daily export volume, and failed outbox retention when an outbox exists. Export can be stopped without stopping the Study API.

## Consent

Consent is a protocol and research ethics gate. Microphone permission is not research consent.

When the approved protocol requires formal consent, the UI posts `POST /v1/participant-session/consent` before start. Store the consent version, timestamp, allowed data classes (`consent_profile`), and permitted interaction modes. Block start, OpenAI transmission, transcript persistence, and LangSmith export when required consent is absent or withdrawn.

Withdrawal posts the same route with `withdrawn=true`. Withdrawal revokes the writer lease, blocks new Realtime setup, and records a tombstone on later trace export. Existing canonical turns stay until a deletion request under the approved retention policy.

When the protocol does not require stored consent, do not require consent columns to be filled, and do not block start for a missing consent version.

## Completion

Completion is one database transaction that:

1. Validates `expected_version` and the writer lease.
2. Inserts any missing final participant recovery observations under the normal provenance rules.
3. Rejects an existing ID whose immutable payload has a different content hash.
4. Records the completion reason and server completion time.
5. Changes the session state from `active` or `paused` to `completed`. Do not persist `completing`.
6. Writes any durable trace delivery record required by the selected guarantee. Best effort writes none that the request must wait on.

A repeated request with the same `Idempotency-Key` and the same request hash returns the stored response. The same key with a different request hash returns `409`. Complete must not accept a list of client-authored AI turns.

## Errors

Public errors use a single body. Do not return internal exception text.

```python
class ApiError(BaseModel):
    request_id: str
    error_code: str
    message: str
    retryable: bool = False
    retry_after_seconds: int | None = None
    session_status: str | None = None
    current_version: int | None = None
```

| error_code | HTTP | retryable |
| --- | --- | --- |
| `validation_error` | 400 | no |
| `csrf_rejected` | 403 | no |
| `capability_missing` | 401 | no |
| `capability_invalid` | 401 | no |
| `consent_required` | 403 | no |
| `staff_forbidden` | 403 | no |
| `session_not_found` | 404 | no |
| `session_unavailable` | 404 or 410 | no |
| `session_not_started` | 409 | no |
| `session_already_completed` | 409 | no |
| `turn_conflict` | 409 | no |
| `version_conflict` | 409 | yes, after re-read |
| `writer_conflict` | 409 | no, until transfer |
| `idempotency_conflict` | 409 | no |
| `payload_too_large` | 413 | no |
| `rate_limited` | 429 | yes |
| `realtime_unavailable` | 503 | yes |
| `generation_failed` | 503 | yes when marked |
| `internal_error` | 500 | no |

`session_unavailable` is the projection for missing, revoked, or post-grace links. `410` is used after grace or revocation. `404` is used when no session should be acknowledged.

## Limits and abuse controls

Set the following limits in v1. Oversized recovery batches are rejected as a whole.

| Limit | v1 value |
| --- | --- |
| JSON request body | 256 KiB |
| Participant message text | 8000 characters |
| Observation batch size | 20 items |
| Observation payload text | 2000 characters per field |
| Transcript page size | 200 turns |
| Realtime setups per session | 10 successful setups |
| Concurrent Realtime calls per session | 1 |
| Text generations per session | 200 |
| Session duration | snapshot `target_duration_seconds`, hard stop at 3600 seconds |
| Model allowlist | snapshot model only |
| Per session spend alert | configured on the host, emergency cutoff then text fallback if the snapshot allows text |
| Reconnect rate | 10 Realtime setup attempts per 5 minutes per capability |
| Token exchange | 10 attempts per 15 minutes per IP |
| Messages | 30 per 5 minutes per capability |
| Observations | 60 per 5 minutes per capability |
| Complete | 10 per 15 minutes per capability |

Preserve trusted provider usage details, including separate audio and text token classes when available. If exact research cost must be reproducible later, store the provider usage payload and pricing version in Study Postgres rather than relying on later LangSmith price changes.

## Readiness

Liveness (`GET /health`) reports that the process is running.

Readiness (`GET /ready`) reports whether the process can serve its configured role.

* Sample contracts / sample mode. `/ready` can be ok without Study Postgres.
* Database role. `/ready` must check required database configuration and a bounded connectivity probe.
* Worker role. `/ready` must check the selected queue or delivery store.

OpenAI and LangSmith outages appear in dependency health metrics. An OpenAI or LangSmith outage does not necessarily remove API readiness.

Replace qualitative review questions with measurable release gates. Record an owner and alert threshold for each gate.

| Gate | What is measured | Owner | Alert threshold |
| --- | --- | --- | --- |
| Session start | Start succeeds for a valid writer capability | Study API on-call | Error rate above 2 percent over 15 minutes |
| Acknowledged turn durability | Canonical turns remain after process restart | Study API on-call | Any lost acknowledged turn in staging restore drills |
| Completion success | Complete transaction commits or fails as a whole | Study API on-call | Error rate above 1 percent over 15 minutes |
| Realtime setup | SDP answer returned without leaking call ID or API key | Study API on-call | Setup error rate above 5 percent over 15 minutes |
| Generation latency | Text operation success and duration | Study API on-call | p95 above 8 seconds for text success |
| Reconnect success | Refresh does not duplicate canonical conversation | Study API on-call | Any duplicate canonical conversation in staging |
| Trace export lag | Only if an outbox exists later | Export worker on-call | Outbox age above 15 minutes |
| Duplicate rate | Conflicting IDs return `409` rather than overwrite | Study API on-call | Any silent overwrite in contract tests |
| Unreconciled session rate | Provider item gaps are visible | Study API on-call | Gap rate above 5 percent of voice sessions |
| Cost variance | Provider usage vs alert threshold | Study API on-call | Session spend above the snapshot budget |

## Persistence

Study Postgres is one private Postgres database owned by the Study API. Railway hosts the API. The Study API owns migrations. No Study table is exposed through a public data API. Staff access to transcripts goes through the Study API.

Run the same contract suite against memory and Postgres, including concurrent requests from separate API instances. Schema changes should be additive while old code may still run. Define deployment order, rollback criteria, and how old code behaves against the new schema. Do not dual write without a reconciliation and cutover plan.

Encrypted backups, point in time recovery (PITR), retention, restore ownership, and a tested restore procedure are required before production participant data. The restore owner is the Study API on-call. Rollback is allowed only for additive schema that old code can ignore. The recovery target is no more than 5 minutes of data loss (RPO) and a restore drill completed within 4 hours (RTO). Restore drills must verify transcript hashes, order, configuration snapshots, audit records, and outbox state when an outbox exists.

## Audit stream

Keep a server-generated audit stream separate from participant observations. Audit records cover staff access, transcript export, role and study membership changes, configuration publication, Realtime setup, consent, correction, retention changes, and deletion. Audit records name the actor, study, action, object, authorization result, request ID, timestamp, and object version. Audit records must not copy transcript text. Participant reported events stay in the observation tables.

## Observability outside LangSmith

Add structured application logs, request IDs, database metrics, Realtime connection metrics, outbox backlog when an outbox exists, and alerts. Define service objectives for message success, transcript durability, completion success, Realtime setup, and outbox delivery when enabled. Never put participant text, access tokens, Realtime secrets, or Supabase JWTs in application logs.

## Configuration snapshot

Version labels alone do not prove which configuration a participant received. Store an immutable configuration snapshot. The session references one snapshot ID that cannot be edited after assignment.

The snapshot includes:

* The exact system instructions, or their content hash and immutable object reference
* Model and provider identifiers
* Voice and audio settings
* Tool names and versions
* Turn detection and interruption settings
* Temperature and other generation settings when supported
* Safety policy version
* Issue, persona, assignment, and randomization inputs
* Application and schema versions
* Stored opening content used when `ai_speaks_first` is true

## Minimum data model

### Session

```text
session_id
participant_capability_hash
telemetry_thread_id
study_id
status
version
writer_lease_id
writer_lease_expires_at
configuration_snapshot_id
consent_version
consented_at
consent_profile
started_at
completed_at
completion_reason
created_at
updated_at
```

Consent fields may be null when the protocol does not require stored consent.

### Configuration snapshot

```text
configuration_snapshot_id
study_id
study_wave
protocol_version
issue_version
persona_version
prompt_content_hash
prompt_object_reference
opening_display_text
ai_speaks_first
model_provider
model_name
model_parameters_json
voice_config_json
tool_manifest_hash
safety_policy_version
assignment_seed_reference
application_version
created_at
```

### Canonical turn

```text
turn_id
session_id
ordinal
speaker
origin
verification_status
provider_item_id
provider_response_id
client_event_id
source_mode
generated_text
delivered_text
display_text
interrupted
content_hash
provider_created_at
client_observed_at
recorded_at
schema_version
```

### Outbox event when complete export is required later

```text
outbox_event_id
aggregate_type
aggregate_id
event_type
payload_version
trace_policy_version
payload
langsmith_root_run_id
langsmith_child_run_ids
delivery_status
attempt_count
next_attempt_at
last_error_code
created_at
delivered_at
```

Best effort v1 does not require the outbox table.

## Public, domain, and storage models

Define separate models and explicit mapping functions. Do not inherit a public view from a storage model.

* `SessionRecord` is the storage model.
* `SessionDomain` enforces lifecycle rules.
* `ParticipantSessionView` contains the public projection.
* `ResearcherSessionView` contains approved staff fields.
* `RealtimeSessionConfig` contains the exact provider configuration.

Set Pydantic models used for public input to reject unknown fields. Add maximum lengths and item counts to all text, event, and batch fields.

Pydantic is the library FastAPI uses to validate request and response bodies. Even when an endpoint only updates memory, the request and response bodies should still validate.

### Shared enums and primitives

```python
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionStatus(StrEnum):
    pending = "pending"
    active = "active"
    paused = "paused"
    completed = "completed"
    expired = "expired"


class InteractionMode(StrEnum):
    voice = "voice"
    text = "text"


class Speaker(StrEnum):
    participant = "participant"
    ai = "ai"
    system = "system"


class TurnOrigin(StrEnum):
    study_api_text = "study_api_text"
    snapshot_opening = "snapshot_opening"
    provider_realtime = "provider_realtime"
    client_observation = "client_observation"
    revision = "revision"


class ConnectionState(StrEnum):
    idle = "idle"
    listening = "listening"
    thinking = "thinking"
    speaking = "speaking"
    muted = "muted"
    reconnecting = "reconnecting"
    disconnected = "disconnected"
    finished = "finished"


class ObservationType(StrEnum):
    session_opened = "session_opened"
    microphone_permission = "microphone_permission"
    muted = "muted"
    unmuted = "unmuted"
    interrupted_ai = "interrupted_ai"
    connection_lost = "connection_lost"
    connection_restored = "connection_restored"
    first_audio_heard = "first_audio_heard"
    first_transcript_seen = "first_transcript_seen"
    client_reported_problem = "client_reported_problem"


class GenerationOperationStatus(StrEnum):
    accepted = "accepted"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
```

### Participant session view

The participant UI needs enough data to show the introduction, avatar, issue, and controls. The view must not include the full system prompt, `session_id`, invitation token, call ID, or API keys.

```python
class IssueConfig(FrozenModel):
    issue_id: str = Field(max_length=64)
    title: str = Field(max_length=200)
    summary: str = Field(max_length=2000)


class AiPersonaPublic(FrozenModel):
    display_name: str = Field(max_length=80)
    label: str = Field(default="AI participant", max_length=80)
    short_introduction: str = Field(max_length=500)
    avatar_url: HttpUrl
    avatar_version: str = Field(max_length=64)
    voice_name: str | None = Field(default=None, max_length=64)
    voice_version: str | None = Field(default=None, max_length=64)
    assigned_position: str = Field(max_length=200)


class SessionRulesPublic(FrozenModel):
    target_duration_seconds: int = Field(ge=60, le=3600)
    warn_remaining_seconds: int = Field(default=60, ge=0)
    allow_interrupt: bool = True
    allow_text_fallback: bool = True
    ai_speaks_first: bool = True
    show_exact_remaining_time: bool = False
    allow_resume: bool = True


class ParticipantSessionView(FrozenModel):
    status: SessionStatus
    version: int = Field(ge=1)
    writer_role: Literal["writer", "read_only"]
    study_wave: str = Field(max_length=64)
    issue: IssueConfig
    ai_persona: AiPersonaPublic
    prompt_version: str = Field(max_length=64)
    rules: SessionRulesPublic
    preferred_mode: InteractionMode = InteractionMode.voice
    started_at: datetime | None = None
    ends_at: datetime | None = None
    completed_at: datetime | None = None
    next_instruction: str | None = Field(default=None, max_length=500)
```

### Storage and domain (not returned to the browser)

```python
class SessionRecord(FrozenModel):
    session_id: UUID
    study_id: UUID
    participant_capability_hash: str
    telemetry_thread_id: UUID
    status: SessionStatus
    version: int
    writer_lease_id: UUID | None = None
    writer_lease_expires_at: datetime | None = None
    configuration_snapshot_id: UUID
    consent_version: str | None = None
    consented_at: datetime | None = None
    consent_profile: str | None = None
    consent_withdrawn_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    completion_reason: str | None = None


class RealtimeSessionConfig(FrozenModel):
    model: str
    voice: str | None = None
    instructions_hash: str
    tool_manifest_hash: str
    turn_detection_json: str
    safety_identifier: str
```

### Transcript projection

```python
class TranscriptTurnView(FrozenModel):
    turn_id: UUID
    speaker: Speaker
    ordinal: int = Field(ge=0)
    display_text: str = Field(max_length=16000)
    source_mode: InteractionMode
    interrupted: bool = False
    recorded_at: datetime


class TranscriptResponse(FrozenModel):
    version: int
    turns: list[TranscriptTurnView]
    cursor: str | None = None
```

### Messages for text mode

```python
class MessageCreate(FrozenModel):
    client_message_id: UUID
    text: str = Field(min_length=1, max_length=8000)
    client_created_at: datetime | None = None
    expected_version: int = Field(ge=1)


class MessageResponse(FrozenModel):
    operation_id: UUID
    operation_status: GenerationOperationStatus
    participant_turn: TranscriptTurnView
    ai_turn: TranscriptTurnView | None = None
    status: SessionStatus
    version: int
```

### Observations

```python
class ObservationCreate(FrozenModel):
    observation_id: UUID
    observation_type: ObservationType
    occurred_at: datetime
    connection_state: ConnectionState | None = None
    client_first_audio_observed_ms: int | None = Field(default=None, ge=0)
    client_first_transcript_observed_ms: int | None = Field(default=None, ge=0)


class ObservationAck(FrozenModel):
    accepted: bool = True
    observation_id: UUID
    untrusted: bool = True
```

### Session lifecycle requests

```python
class AccessExchangeRequest(FrozenModel):
    invitation_token: str = Field(min_length=32, max_length=256)


class SessionStartRequest(FrozenModel):
    preferred_mode: InteractionMode = InteractionMode.voice
    expected_version: int = Field(ge=1)
    client_started_at: datetime | None = None


class SessionStartResponse(FrozenModel):
    session: ParticipantSessionView
    opening_turn: TranscriptTurnView | None = None


class SessionCompleteRequest(FrozenModel):
    reason: str = Field(default="participant_ended", max_length=64)
    expected_version: int = Field(ge=1)
    client_completed_at: datetime | None = None
    recovery_observations: list[ObservationCreate] = Field(default_factory=list, max_length=20)


class SessionCompleteResponse(FrozenModel):
    session: ParticipantSessionView
    saved_turn_count: int


class ConsentRecordRequest(FrozenModel):
    consent_version: str = Field(min_length=1, max_length=64)
    consent_profile: str = Field(min_length=1, max_length=64)
    allowed_modes: list[InteractionMode] = Field(min_length=1, max_length=2)
    withdrawn: bool = False
    expected_version: int = Field(ge=1)


class SessionDomain:
    """Lifecycle rules live here, not on the public view.

    Methods such as start, pause, complete, and expire take a SessionRecord
    and return a new SessionRecord. They do not serialize to the browser.
    """


class ResearcherSessionView(FrozenModel):
    session_id: UUID
    study_id: UUID
    status: SessionStatus
    version: int
    configuration_snapshot_id: UUID
    telemetry_thread_id: UUID
    started_at: datetime | None = None
    completed_at: datetime | None = None
    completion_reason: str | None = None
    consent_version: str | None = None
    writer_lease_expires_at: datetime | None = None
```

`SessionCompleteRequest` does not include client-authored final AI turns. Recovery observations must use the same allowlisted observation model as `POST /v1/participant-session/observations`.

### Realtime setup

```python
class RealtimeCallCreateRequest(FrozenModel):
    sdp_offer: str = Field(min_length=1, max_length=100_000)
    expected_version: int = Field(ge=1)


class RealtimeCallCreateResponse(FrozenModel):
    sdp_answer: str
    expires_at: datetime
```

The response must not include `client_secret`, call ID, or the standard API key.

## Recommended backend setup

Use FastAPI with Python 3.12 or newer, Pydantic v2, and `uv` for dependency management. Deploy the Study API and workers to Railway. Keep OpenAI, LangSmith, and database credentials in host environment variables.

A useful source layout is:

```text
backend/
  app/
    main.py
    api/
      router.py
      health.py
      participant_access.py
      participant_session.py
      messages.py
      observations.py
      realtime.py
      staff.py
    models/
      enums.py
      session.py
      transcript.py
      observations.py
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
  workers/
    realtime_control.py
  tests/
    test_health.py
    test_access.py
    test_sessions.py
    test_messages.py
    test_completion.py
    test_realtime.py
  pyproject.toml
  README.md
```

Sample contracts can keep session and transcript state in process memory, behind functions that the routes call. Durable record adds Study Postgres without changing the public route shapes. Voice control adds server-mediated Realtime and the sideband worker using those same functions. Approved tracing may add a no-operation exporter or, later, an outbox worker.

## Sample contracts through research export

### Sample contracts

Build the FastAPI app with health routes, Pydantic models, and the participant endpoints listed above. Use in-memory sample sessions and scripted transcripts. Writes should validate input and update memory. Writes should not call OpenAI, Study Postgres, or LangSmith.

The first review should answer whether the frozen routes cover the UI participant journey, whether public models are enough without leaking system prompts, whether turn and completion writes follow the immutable retry rules, and whether the frontend can replace mocks with real HTTP calls against `fastapi dev`.

### Durable record

Add Study Postgres for sessions, snapshots, turns, observations, completion, leases, and audit records. Enforce status transitions. Enforce resume rules. Reject conflicting turns. Project unavailable states for expired or revoked links. Keep a completed projection readable for the grace period.

Tests should cover refresh during a session, duplicate complete requests, out of order recovery batches, two devices, and simultaneous writers.

### Voice control

Create real server-mediated Realtime calls from the Study API in staging. Persist the call ID. Run the sideband worker. Save voice and text canonical turns from trusted origins. Add reconnect without a second conversation. Do not send the call ID or standard API key to the browser.

The study team should run pilot sessions across Safari, Chrome, mobile Safari, and common campus network conditions before using the system with participants.

### Approved tracing

Keep production tracing off until policy, retention, access, and deletion are approved. Best effort export must not block participant requests. An export worker is optional.

### Research export

Ship versioned study exports from Study Postgres. Choose which interrupted-AI text field is exported in the export manifest. Later datasets should be built from those exports, not from a mutable LangSmith project view.

## Required contract tests

### Participant API

* A missing, expired, revoked, or wrong session capability cannot read or mutate a session.
* A completed session cannot mint a Realtime call or add a new canonical turn.
* The same idempotency key and request hash returns the same response.
* The same idempotency key with a different request hash returns a conflict.
* A stale writer lease cannot mutate the session.
* Two simultaneous start or completion requests produce one transition.
* Unknown input fields and oversized payloads are rejected.
* When the approved protocol requires consent, session start, Realtime setup, and tracing are blocked without the required consent version.
* Consent write with the same version is idempotent. Withdrawal blocks new Realtime setup.
* A staff member cannot read a session outside the staff member's current study membership.
* Internal voice ingest maps a duplicate provider item to one canonical turn.

### Transcript integrity

* A browser cannot create AI or system turns.
* A duplicate provider item maps to one canonical turn.
* A conflicting duplicate ID does not overwrite text.
* A completion transaction either saves all final records or saves none.
* An interruption preserves generated, delivered, and displayed text according to the protocol.

### Realtime

* The backend creates the provider session from an immutable configuration snapshot.
* The browser never receives the standard OpenAI API key or the call ID.
* A sideband disconnect is detected and recorded.
* Reconnect and call refresh do not create a second canonical conversation.
* Provider usage and browser observations remain distinguishable.
* Closing or crashing the browser at each point in final turn delivery does not lose an acknowledged provider item.
* Reconciliation reports provider item gaps instead of silently treating an incomplete transcript as complete.
* Unauthorized `session.updated` marks and invalidates the session.

### LangSmith (when an exporter exists)

* A database commit succeeds when LangSmith is unavailable.
* Under a complete export policy, every eligible committed AI turn produces one outbox event and one LangSmith run. Best effort tests must not require that every turn appears in LangSmith.
* Worker retries reuse the persisted run ID.
* Every run has the pseudonymous thread metadata, not the internal `session_id` as a public identifier.
* Redaction tests prove that tokens, emails, invitation values, and disallowed prompt fields are absent.

### Operations

* Readiness changes according to the configured service role and required dependencies.
* When durable export is enabled, outbox backlog and repeated export failure trigger alerts.
* A deletion test removes or tombstones the database record and deletes mapped LangSmith runs under the approved policy.
* Production configuration rejects synthetic defaults and local LangSmith projects.
* A database restore preserves transcript hashes, ordering, configuration snapshots, audit records, and pending outbox work.
* The current and previous supported UI versions pass the same API contract suite.

## Implementation order

1. Freeze the participant capability, state machine, concurrency, idempotency, provenance, and error contracts (Sample contracts).
2. Choose the Study Postgres location and write the schema and unique constraints (Durable record).
3. Implement the API against durable storage, including atomic completion and any trace delivery record required by the selected guarantee. Best effort writes no blocking outbox row.
4. Implement server-mediated Realtime setup and sideband ingestion in a staging environment (Voice control).
5. Approve the trace policy, retention, access, and deletion rules (Approved tracing).
6. Implement the selected LangSmith export path only after policy approval. Use one root trace per AI generation in the LangSmith plan. Keep delivery best effort unless an outbox is later required.
7. Run concurrency, failure injection, redaction, reconciliation, and browser pilot tests.
8. Build versioned research exports (Research export). Decide later whether to add LangSmith datasets and evaluators.

## Initial scope

Sample contracts should include:

* The FastAPI app skeleton
* Liveness and readiness checks
* Pydantic request and response models
* Participant access exchange and participant session routes
* Observation write routes
* The text message route with scripted AI replies
* Realtime call routes that return a sample SDP answer without a real call ID
* In-memory sample data
* Contract tests listed for the participant API that can run without Postgres

Sample contracts should exclude:

* Study Postgres
* Staff JWT verification
* Live OpenAI calls
* LangSmith export
* Raw audio storage
* Scoring
* Admin APIs
* Generated video

## Decisions with owners

| Decision | Why it blocks the design | Choice in this plan |
| --- | --- | --- |
| Participant link and capability format | It defines every participant API trust boundary | One-time random link token exchanged for a short-lived HTTP-only capability cookie |
| One device or device transfer rule | It defines concurrency and retry behavior | One active writer lease with explicit transfer |
| Realtime unified setup and sideband use | It defines control, transcript provenance, and trusted metrics | Server-mediated setup plus sideband monitoring |
| Canonical meaning of an interrupted AI turn | It changes the research transcript | Store generated, delivered, and display text separately |
| Voice timing definitions | First audio and first text are different measures | Record both as separate client observed metrics |
| Study database host and migration owner | Plans must name the owner | One private Postgres database owned by the Study API, hosted beside the API on the chosen Railway Postgres service |
| Staff role matrix | Authentication alone does not authorize research actions | Deny by default and grant named actions by role and `study_id` |
| Trace field allowlist and retention | Production tracing exports participant text | Export nothing until an approved policy version exists |
| Raw audio retention | Early wording can be read as audio collection | Do not record raw audio |
| Configuration snapshot contents | Version labels alone are not reproducible | Store immutable content hashes and exact provider settings |
| Text model path | Trace hooks and timing depend on it | Study API mediates text generation |
| LangSmith delivery | Retry and outbox depend on it | True best effort by default |

Remaining product choices for researchers, such as whether voice is required and whether participants see exact remaining time, belong in the snapshot and protocol, not as undecided API contracts.
