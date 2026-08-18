# Suggested revisions to the backend and LangSmith plans

## Review conclusion

The proposals describe the participant journey well, but they do not yet define the contracts that protect the study record. The largest gaps are at the boundaries between the browser, the study API, OpenAI Realtime, the database, and LangSmith.

The current design lets the browser submit authoritative AI turns, system turns, timing data, token counts, and completion requests. It also treats a public session identifier as access control. A participant or a broken client could therefore alter the research record, mint Realtime credentials, or complete a session without the backend being able to distinguish a valid retry from conflicting data.

The LangSmith design has a second boundary problem. It proposes one root run that stays open across several HTTP requests, but it does not define how the backend will persist the run hierarchy or recover it after a restart. Direct tracing calls also have no durable handoff from the database transaction. A successful participant request can therefore lose its trace, while a retry can create a duplicate trace.

The plans should not be implemented as production contracts until the revisions below are resolved.

## Priority definitions

* Critical means the current design can corrupt data, bypass a trust boundary, or block safe operation.
* High means the current design has incompatible contracts or lacks behavior needed for recovery.
* Medium means the current design can be implemented, but the result will be hard to test, compare, or operate.

## Cross plan inconsistencies

| Inconsistency | Evidence | Required resolution |
| --- | --- | --- |
| A completed session is both readable and unavailable | `backend_proposal_2026_08_06.md:123-129`, `backend_proposal_2026_08_06.md:146`, and `backend_proposal_2026_08_06.md:520-523` | Keep a small completed projection readable for a defined grace period, while rejecting conversation writes |
| A duplicate turn is updated, rejected, and described only as "not duplicated" | `backend_proposal_2026_08_06.md:43-47`, `backend_proposal_2026_08_06.md:520-523`, `backend_proposal_2026_08_06.md:565-569`, and `ui_proposal_2026_08_06.md:286-292` | Make turns immutable, return the stored record for an identical retry, and return a conflict for different content |
| Participant access is called authenticated, public, and undecided | `ui_proposal_2026_08_06.md:280-283`, `supabase_auth_proposal_2026_08_05.md:13-15`, and `backend_proposal_2026_08_06.md:573-590` | Define participant capability authentication separately from staff Supabase Auth |
| The UI always opens with an AI message, while the backend makes it conditional | `ui_proposal_2026_08_06.md:74-78` and `backend_proposal_2026_08_06.md:85-97` | Make the configuration snapshot decide who speaks first, and define exactly which component creates the opening turn |
| Voice generation metrics are required by LangSmith but absent from the backend API | `langsmith_proposal_2026_08_06.md:189-202`, `langsmith_proposal_2026_08_06.md:287-298`, and `backend_proposal_2026_08_06.md:302-336` | Add a versioned observation contract or collect provider metrics through a trusted sideband connection |
| LangSmith describes a Railway mediated text path, while the backend leaves the path undecided | `langsmith_proposal_2026_08_06.md:63-73` and `backend_proposal_2026_08_06.md:573-590` | Choose the text model path before freezing trace hooks and timing semantics |
| The initial spec can be read as raw voice tracking, while every later plan excludes audio | `2026-08-06-init-specs.md:3-10`, `backend_proposal_2026_08_06.md:53-55`, and `langsmith_proposal_2026_08_06.md:377-383` | State that "voice" means approved configuration and metrics, not raw audio |
| The authoritative store is called Railway or Postgres, but its host and owner are unspecified | `backend_proposal_2026_08_06.md:18-20`, `backend_proposal_2026_08_06.md:520-523`, and `supabase_auth_proposal_2026_08_05.md:321-326` | Name the database host, migration owner, network path, and authorization model |
| Staff sessions are called HTTP only while the proposed browser Supabase client must manage the session | `supabase_auth_proposal_2026_08_05.md:3-5`, `supabase_auth_proposal_2026_08_05.md:21-27`, and `supabase_auth_proposal_2026_08_05.md:148-156` | Choose standard browser managed Supabase cookies or a server only backend for frontend session |
| Every document uses "Phase 1" to mean different work | `ui_proposal_2026_08_06.md:260-282`, `backend_proposal_2026_08_06.md:507-533`, `langsmith_proposal_2026_08_06.md:322-355`, and `supabase_auth_proposal_2026_08_05.md:301-326` | Replace phase numbers with shared named milestones and map each workstream to them |

## Critical revisions

### 1. Use a participant access capability instead of a session ID

Evidence:

* The participant API uses only `session_id` in every route. See `backend_proposal_2026_08_06.md:59-67` and `backend_proposal_2026_08_06.md:89-120`.
* The choice between an unguessable ID and a signed token is deferred. See `backend_proposal_2026_08_06.md:587`.
* The Auth plan intentionally leaves participant routes outside Supabase Auth. See `supabase_auth_proposal_2026_08_05.md:13-15`.

The API currently has no participant authentication contract. Anyone who obtains a session ID can load the assignment, write turns and events, change the mode, mint an OpenAI credential, and complete the session. A UUID in a URL can also appear in browser history, analytics, proxy logs, screenshots, and referrer headers.

Revise the design as follows:

1. Give each invitation a random, single purpose link token that is separate from the internal session ID.
2. Store only a hash of the link token.
3. Exchange the link token for a short lived, HTTP only participant session cookie or bearer capability.
4. Require that capability on every participant read and write, including Realtime setup and refresh.
5. Scope the capability to one session and a small set of allowed actions.
6. Rate limit token exchange, Realtime setup, messages, events, and completion.
7. Rotate or revoke the capability when the session is completed, expired, or invalidated.
8. Keep the internal session ID out of public URLs and LangSmith metadata.

The design should also state the CORS policy, cookie settings, token lifetime, replay policy, and behavior when a link is opened on a second device. If the capability uses a cookie, state changing requests need a defined CSRF defense with an appropriate `SameSite` setting, strict `Origin` verification, and a CSRF token when the deployment model requires one. CORS alone is not a CSRF control.

### 2. Define who is allowed to create each kind of research record

Evidence:

* `TranscriptTurnCreate` accepts `participant`, `ai`, and `system` speakers from the browser. See `backend_proposal_2026_08_06.md:209-212` and `backend_proposal_2026_08_06.md:318-326`.
* The browser can send arbitrary turn and event metadata. See `backend_proposal_2026_08_06.md:315-326` and `backend_proposal_2026_08_06.md:384-390`.
* Voice timing and token counts are reported by the browser. See `langsmith_proposal_2026_08_06.md:79-84` and `langsmith_proposal_2026_08_06.md:189-202`.

The current public models do not separate commands from observations. They let the browser assert facts that should come from the backend or OpenAI. A client can label text as an AI or system turn, replace an earlier turn, invent token use, or report a false timestamp.

Revise the design around explicit provenance:

* The text message route accepts participant text only. The backend creates the participant turn, calls the model, and creates the AI turn.
* The browser cannot create a system turn.
* The backend assigns the canonical turn order.
* The backend creates canonical AI turn IDs, or maps a provider conversation item ID to one canonical turn.
* Browser observations use a separate model and are marked as untrusted observations. Examples include first audio heard, local connection state, and microphone permission.
* Provider usage, model identity, and server timing use trusted server or provider fields.
* Arbitrary `metadata` and `detail` dictionaries are replaced with versioned, allowlisted event payloads that have size limits.

Every stored turn should include `origin`, `provider_item_id`, `recorded_at`, `content_hash`, and a schema version. Client timestamps should remain optional evidence, not the canonical order.

### 3. Choose a server control strategy for OpenAI Realtime

Evidence:

* The browser receives a client secret and controls the Realtime data channel. See `backend_proposal_2026_08_06.md:490-503`.
* Railway receives only final turns and client reported events. See `backend_proposal_2026_08_06.md:499-501`.
* The proposal says Railway owns instructions, tools, and study control, but it does not define how Railway prevents client changes after connection. See `backend_proposal_2026_08_06.md:24-37`.

The ownership claim is stronger than the proposed connection contract. A direct client connection is useful for audio latency, but a client that controls the Realtime data channel can send `session.update` events. A sideband connection lets the backend monitor and update the session, but it does not prevent the client from sending its own updates.

Current OpenAI documentation describes two relevant options:

* The unified WebRTC interface lets the server submit the browser SDP together with the server owned session configuration.
* A sideband server connection lets the backend monitor the same WebRTC session, update instructions, and handle tools.

Revise the plan to compare and choose one of these options. Server mediated setup plus a sideband connection improves provider event capture and keeps tool execution on the server, but the plan must not claim that it makes the browser unable to alter session settings. If immutable session configuration is a study requirement, define how the backend detects unauthorized `session.updated` events, invalidates affected sessions, and marks their records. Confirm which instructions and settings remain visible to the browser under the chosen OpenAI contract.

The Study API must capture the `Location` header returned during server mediated WebRTC setup, extract and persist the OpenAI call ID, and securely enqueue a control handoff to the sideband worker. The browser should receive the SDP answer, not the call ID or standard API key. Set a privacy preserving `OpenAI-Safety-Identifier` on the trusted server request.

The design must also list the client events the application intends to send, how unexpected client updates are detected, how tool calls are handled, how a prior secret is invalidated, and what happens if the sideband connection fails while audio continues.

A sideband socket alone is not a durability guarantee. The backend should append final provider events to durable storage, acknowledge persisted provider item IDs, and expose a reconciliation cursor. The browser can retry missing client observations, but it should not become the only holder of a final AI turn. If crash recovery requires browser storage, define encryption, expiry, cleanup, and consent before using IndexedDB or another persistent store.

### 5. Do not keep one LangSmith root run open for the whole study session

Evidence:

* The proposal creates one root `session` run at start and closes it at completion. See `langsmith_proposal_2026_08_06.md:96-110`.
* Start, turns, messages, and completion happen in separate HTTP requests. See `langsmith_proposal_2026_08_06.md:287-296`.
* No model stores the root run ID or durable parent context needed to attach later requests.

A LangSmith run tree needs stable hierarchy fields. A process restart, deploy, abandoned session, or concurrent request can leave the root open or attach children incorrectly. A single root also makes the LangSmith thread look like one trace instead of a sequence of conversational traces.

Use one root `conversation_turn` trace per AI generation operation. Put the participant message and resulting AI message in the root trace's top level `inputs.messages` and `outputs.messages`. Put an instrumented LLM call beneath it as a child run when one exists. Group the root traces with the same pseudonymous `thread_id`. Record session start, completion, and notable connection failures as independent root traces or ordinary database events. Do not make every turn a child of a root that spans the whole participant session.

LangSmith requires thread metadata on every parent and child run for thread filtering and aggregate token and cost calculations. The worker should add the thread metadata through one trace envelope builder, rather than relying on call context propagation across requests.

For current LangSmith Messages and Turns views, mark the top level trace with the documented root agent metadata and set the documented message format when manual instrumentation needs it. Treat the Messages view as a pilot acceptance check because the current view is still described as beta.

If the team keeps the long lived root design, the database must persist the root run ID and valid parent context, and it must close abandoned roots. SDK and API instrumentation can generate hierarchy fields when given valid trace context. The simpler per generation root design avoids carrying that context across requests and matches LangSmith's documented thread model.

### 6. Make completion and final transcript persistence one transaction

Evidence:

* A completion request can include final turns. See `backend_proposal_2026_08_06.md:370-379`.
* The completion endpoint must be safe to retry. See `backend_proposal_2026_08_06.md:43-47`.
* The proposal does not state whether final turns, completion state, and export events commit together.

The backend must not report a completed session while losing its final turns. It must also prevent a late retry from changing a completed transcript without an explicit correction record.

Revise completion to use one database transaction that:

1. Validates the expected session version and writer lease.
2. Inserts any missing final participant observations under the normal provenance rules.
3. Rejects an existing ID whose immutable payload has a different content hash.
4. Records the completion reason and server completion time.
5. Changes the session state.
6. Writes any durable trace delivery record required by the selected delivery guarantee.

A repeated request with the same idempotency key and request hash should return the stored response. The same key with a different request hash should return a conflict.

### Critical consent gate

The UI says formal consent may be a separate step when the approved study protocol requires it, but neither the backend nor the LangSmith plan models that gate. See `ui_proposal_2026_08_06.md:41-52` and `backend_proposal_2026_08_06.md:53-55`.

Microphone permission is not research consent. When the protocol or research ethics approval requires formal consent, store the consent version, timestamp, allowed data classes, and permitted interaction modes. Block OpenAI transmission, transcript persistence, and LangSmith export when required consent is absent or withdrawn. The approved participant wording should explain the relevant subprocessors, including that voice is sent to OpenAI even when raw audio is not retained.

## High priority revisions

### Define the LangSmith delivery guarantee

The proposal intentionally makes LangSmith best effort and non-authoritative. See `langsmith_proposal_2026_08_06.md:24-26`. It also requires duplicate trace prevention and suggests background retries without defining their durability. See `langsmith_proposal_2026_08_06.md:162-176` and `langsmith_proposal_2026_08_06.md:300-307`.

Choose one explicit contract:

* Under a true best effort contract, participant requests never wait for LangSmith, trace gaps are accepted, and the plans must not claim that every eligible turn appears in LangSmith.
* If complete and reconcilable trace coverage becomes a requirement, commit a versioned outbox event with the study record, export it through a worker with a persisted UUID version 7 run ID, and record retries, terminal failures, and reconciliation state.

Under either contract, build traces only from committed canonical records, reuse the stored run ID on retries, and prevent LangSmith failure from failing session completion.

### 7. Publish a session state transition table

The status enum lists `pending`, `active`, `completing`, `completed`, `expired`, `unavailable`, and `paused`, but the proposals do not define legal transitions. See `backend_proposal_2026_08_06.md:194-201`.

The plan must decide whether `unavailable` is an API projection, a persisted quarantine state, or both. A simple lifecycle that treats it as an API projection is:

```text
pending -> active
pending -> expired
active -> paused
paused -> active
active -> completing
paused -> completing
completing -> completed
active -> expired
paused -> expired
```

For each transition, define the actor, preconditions, transaction, idempotency behavior, allowed writes, and HTTP result. Add a monotonic `version` field to the session and require `expected_version` on lifecycle writes.

### 8. Resolve the completed session contradiction

The completion page is supposed to read the completed session and next instruction. See `backend_proposal_2026_08_06.md:123-129`. The route table and Phase 2 also say completed links can return unavailable or `410`. See `backend_proposal_2026_08_06.md:146` and `backend_proposal_2026_08_06.md:520-523`.

Keep a minimal completed projection readable to the same participant capability for a defined grace period. It can include status, completion time, and next instruction. Block conversation writes and new Realtime credentials after completion. Return `410` only after the grace period or explicit revocation.

### 9. Define one idempotency rule for turns

The proposal says a duplicate `turn_id` updates the existing turn. See `backend_proposal_2026_08_06.md:43-47`. Phase 2 says to reject duplicate turns. See `backend_proposal_2026_08_06.md:520-523`.

Use immutable canonical turns:

* The same ID and same content hash returns the existing turn.
* The same ID and different immutable content returns `409 turn_conflict`.
* A correction creates a new revision record with an actor, reason, and link to the prior revision.
* Unique constraints cover session plus client event ID, provider item ID, and canonical ordinal where applicable.

Batch writes must be atomic, have a maximum size, and define whether one invalid item rejects the whole batch.

### 10. Remove the duplicate message and turn ownership

The message route creates participant and AI turns, while the turns route also accepts both speakers. See `backend_proposal_2026_08_06.md:152-158`.

Keep separate command boundaries:

* `POST /messages` is the text generation command. It accepts participant text and an idempotency key.
* The backend owns all canonical text mode turns.
* A voice ingestion route accepts provider identified final items or browser recovery observations under a narrower schema.
* A general public `/turns` upsert route should not exist.

Model text generation as an operation with `accepted`, `running`, `succeeded`, and `failed` states. A retry returns the same operation and AI response instead of calling the model again.

The opening turn needs the same ownership rule. If `ai_speaks_first` is true, define whether the start command returns stored opening content or initiates a generation operation. The UI must render exactly the turn returned by that contract.

### 11. Define concurrency and writer ownership before building the API

The plan defers the rule for two devices until Phase 2. See `backend_proposal_2026_08_06.md:565-571`.

The public contract needs the rule now because it affects every write. Choose optimistic version checks, row locking, or a server issued writer lease with fencing. If the product allows only one writer, a lease is a reasonable default. Starting on a second device should either transfer ownership through an explicit action or remain read only. Define the conflict response for stale writers.

Database tests should run simultaneous start, message, turn ingestion, refresh, and completion requests.

### 12. Separate public, domain, and storage models

`SessionInternal` inherits from `SessionPublic`. See `backend_proposal_2026_08_06.md:290-300`.

Inheritance makes accidental serialization of server fields more likely, and it couples the domain record to the browser projection. Define separate models and explicit mapping functions:

* `SessionRecord` is the storage model.
* `SessionDomain` enforces lifecycle rules.
* `ParticipantSessionView` contains the public projection.
* `ResearcherSessionView` contains approved staff fields.
* `RealtimeSessionConfig` contains the exact provider configuration.

Set Pydantic models used for public input to reject unknown fields. Add maximum lengths and item counts to all text, metadata, event, and batch fields.

### 13. Name the actual system of record

The plans repeatedly call "Railway" the source of truth. See `backend_proposal_2026_08_06.md:20` and `langsmith_proposal_2026_08_06.md:3-5`.

Railway is a deployment platform, not a data ownership boundary. Name the components:

* The Study API enforces participant and researcher commands.
* The Study Postgres database stores authoritative records.
* Railway runs the Study API and any worker.
* Supabase Auth proves staff identity.
* LangSmith stores a derived operational projection.

The plan must choose where Study Postgres runs. The backend proposal only says Postgres, while the Supabase proposal correctly says RLS applies if study tables are later hosted there. See `supabase_auth_proposal_2026_08_05.md:321-326` and `backend_proposal_2026_08_06.md:520-523`. State the physical database host, who owns migrations, which service can connect, and whether any Study tables are exposed through a data API.

### 14. Add study scoped staff authorization

The Auth proposal correctly requires Railway to verify staff identity and use server controlled role claims. See `supabase_auth_proposal_2026_08_05.md:289-299`. It does not define which studies or study waves an authenticated researcher may access.

A global `researcher` role is not an object authorization model. Add `study_id` to sessions, configuration snapshots, exports, and audit records. Define current membership and permissions for session creation, transcript reading, export, correction, deletion, and study configuration. Check study membership for every object lookup and export. If the product is deliberately single tenant and single study, state and enforce that invariant.

### Staff session cookie contract

The Supabase plan promises HTTP only cookies while also using `createBrowserClient` and client side `signInWithPassword`. See `supabase_auth_proposal_2026_08_05.md:3-5`, `supabase_auth_proposal_2026_08_05.md:148-156`, and `supabase_auth_proposal_2026_08_05.md:179-195`.

Choose one contract:

* Use the standard `@supabase/ssr` browser session, document that the browser can access the session cookies, and use a strict content security policy, minimal third party scripts, short sessions, and multifactor authentication for staff.
* Use a server only backend for frontend session with HTTP only cookies, and do not expose a Supabase browser client or tokens to application JavaScript.

Do not describe the standard browser flow as HTTP only. Require recent authentication for transcript export, role changes, and deletion.

### 15. Define the canonical transcript before using it for research

The plans use "final turn" without defining what final means when the participant interrupts AI audio. See `backend_proposal_2026_08_06.md:268-270`, `backend_proposal_2026_08_06.md:304-326`, `ui_proposal_2026_08_06.md:90`, and `langsmith_proposal_2026_08_06.md:366-375`.

For voice AI output, generated text can differ from text the participant heard. Store separate facts:

* Provider generated content.
* Content delivered before interruption.
* Final transcript text shown to the participant.
* Interruption time and provider item ID.
* Any participant approved correction as a revision, not an overwrite.

The research team must choose which field is exported as "what the AI said." Make the choice part of a versioned export manifest.

### 16. Snapshot the full study configuration

Version labels alone do not prove which configuration a participant received. See `backend_proposal_2026_08_06.md:537-551`.

Store an immutable configuration snapshot with:

* The exact system instructions or their content hash and immutable object reference.
* Model and provider identifiers.
* Voice and audio settings.
* Tool names and versions.
* Turn detection and interruption settings.
* Temperature and other generation settings when supported.
* Safety policy version.
* Issue, persona, assignment, and randomization inputs.
* Application and schema versions.

The session should reference one snapshot ID that cannot be edited after assignment.

### 17. Treat voice metrics as observations with explicit trust and meaning

The LangSmith plan defines voice TTFT as either first audio or first transcript token. See `langsmith_proposal_2026_08_06.md:180-204` and `langsmith_proposal_2026_08_06.md:385-390`.

Those are different measures. Record them separately:

* `server_generation_started_at`
* `provider_first_output_at`
* `client_first_audio_observed_ms`
* `client_first_transcript_observed_ms`
* `generation_completed_at`
* `metric_source`
* `clock_basis`

Use durations measured by one monotonic clock when the browser reports two local observations. Do not subtract unrelated browser and server wall clocks. Mark browser values as client observed. Prefer provider events collected through the sideband connection for canonical operational metrics.

Do not use browser supplied token counts or cost as authoritative. Use provider usage, and leave cost absent when no trusted usage record exists.

### 18. Use a pseudonymous LangSmith thread ID

The proposal uses the study session ID as both `thread_id` and `session_id` metadata. See `langsmith_proposal_2026_08_06.md:88-95`.

Create a separate UUID version 7 telemetry thread ID. Keep the mapping in the Study database. Do not export invitation tokens, public route identifiers, participant identifiers, email addresses, or free form client metadata.

The trace builder should use a versioned allowlist. It should reject unknown fields and apply a redaction policy before writing the outbox event.

### 19. Distinguish actual model traces from reconstructed voice observations

The voice plan reconstructs an LLM run from final turns. See `langsmith_proposal_2026_08_06.md:75-84`.

A reconstructed run is not proof of the exact model input, output delivery, or generation timing. Realtime also maintains conversation context across responses, so the latest participant turn alone is not the full input that affected an AI response.

Add `trace_kind` with values such as `instrumented_text_generation`, `provider_observed_realtime_response`, and `client_reconstructed_voice_turn`. Add the provider response ID and the configuration snapshot ID. Only call a trace reproducible when it contains the exact approved input context and provider configuration. Do not present a client reconstructed turn as a complete model call in the Playground.

For text calls, trace the actual message context or an approved content hash and immutable reference. For Realtime calls, use sideband provider events when possible. A client reconstruction should remain useful for transcript review, but its latency, usage, and input completeness should be marked unknown unless a trusted source supplies them.

### 20. Define retention, deletion, and access before production tracing

The proposal correctly makes transcript retention and access prerequisites for production, but it leaves their values and enforcement unresolved. See `langsmith_proposal_2026_08_06.md:366-383`.

Production tracing should remain disabled until the plan specifies:

* The approved fields for each study wave.
* Retention in the Study database and LangSmith.
* Who can read traces and exports.
* How a withdrawal or deletion request finds and deletes all related runs.
* Whether backups and failed outbox payloads contain transcript text.
* How local and staging environments prevent real participant data.
* How access and deletion actions are audited.

The default should be no raw prompt or transcript export until an approved trace policy version is attached to the session.

Current LangSmith Cloud documentation describes base and extended trace retention, and it states that project retention changes affect new traces rather than existing traces. Masking and anonymization must happen before ingestion when sensitive fields must never leave the Study system. Whole trace deletion is asynchronous, so the deletion workflow must keep a tombstone and confirm completion instead of assuming immediate removal.

### 21. Separate deployment environment from study wave

The proposal suggests a separate production LangSmith project for a study wave. See `langsmith_proposal_2026_08_06.md:270-285`.

Use separate projects for local, staging, and production because those are security and operational boundaries. Use immutable metadata for study wave, protocol version, and configuration snapshot inside production. Create a separate production project for a wave only when access or retention rules differ. Otherwise, project proliferation makes comparison and operations harder.

### 22. Preserve a reproducible path to later evaluation

The LangSmith proposal deliberately excludes datasets and evaluators. See `langsmith_proposal_2026_08_06.md:12-20`.

Deferring evaluators is reasonable, but the storage model must preserve reproducibility now. Add:

* Immutable configuration snapshots.
* Canonical and revised transcript records.
* Export manifest versions.
* Trace schema versions.
* Stable turn and provider identifiers.
* Consent and trace policy versions.
* A record of the code version that produced each derived export.

Later datasets should be built from versioned Study database exports, not from the mutable LangSmith project view. LangSmith experiments can then reference a frozen dataset without redefining the study record.

Do not freeze a dataset or evaluator schema before the research team chooses the measures. Record an architecture decision later on whether evaluation operates at the turn or full thread level. At that point, dataset examples should carry the source identifiers, transcript revision, treatment assignment, configuration hash, trace policy version, curator, and dataset version. Online evaluator scores should remain operational signals until the study validates them against human ratings.

## Medium priority revisions

### 23. Fix readiness semantics

`GET /ready` correctly has no external dependency requirement in the Phase 1 sample role. See `backend_proposal_2026_08_06.md:135-140`. The plan must change its semantics when later roles require Postgres or a worker queue.

Liveness should report that the process is running. Readiness should report whether the process can serve its configured role. In sample mode, readiness can require only sample storage. In database mode, it must check required database configuration and a bounded connectivity probe. In export worker mode, it must check the selected queue or delivery store. OpenAI and LangSmith outages should appear in dependency health metrics without necessarily removing API readiness.

Replace qualitative review questions with measurable release gates for session start, acknowledged turn durability, completion success, Realtime setup, generation latency, reconnect success, trace export lag, duplicate rate, unreconciled session rate, and cost variance. Record the owner and alert threshold for each gate.

### Persistence rollout and recovery

The proposal says Postgres can replace memory without changing route shapes, but it does not define migration or rollback. See `backend_proposal_2026_08_06.md:488-488` and `backend_proposal_2026_08_06.md:520-529`.

Run the same contract suite against memory and Postgres, including concurrent requests from separate API instances. Define additive schema compatibility, migration ownership, deployment order, rollback criteria, and how old code behaves against the new schema. Do not dual write without a reconciliation and cutover plan.

The Study database also needs encrypted backups, point in time recovery, retention, restore ownership, and a tested restore procedure. Define the acceptable data loss and recovery targets, then run restore drills that verify transcript hashes, order, configuration snapshots, audit records, and outbox state.

### 24. Define error status codes and retry contracts

The shared error body does not map errors to HTTP status codes, retry delay, idempotency state, or correlation ID. See `backend_proposal_2026_08_06.md:422-441`.

Add:

* `request_id`
* `error_code`
* `message`
* `retryable`
* `retry_after_seconds` when applicable
* `session_status`
* `current_version` for conflicts

Publish the HTTP status for every error. Do not return internal exception text.

### 25. Define limits and abuse controls

`MessageCreate` has a text limit, but transcript batches, event details, and metadata do not. See `backend_proposal_2026_08_06.md:318-330`, `backend_proposal_2026_08_06.md:341-344`, and `backend_proposal_2026_08_06.md:384-390`.

Set request body limits, batch limits, text limits, event rate limits, Realtime credential quotas, and per session model budgets. Define what happens when a participant repeatedly reconnects or submits an oversized recovery batch.

Add a model allowlist, maximum session duration, audio and token budgets, per session and global concurrency limits, spend alerts, and an emergency cutoff with a text fallback. Preserve trusted provider usage details, including separate audio and text token classes when available. If exact research cost must be reproducible, store the provider usage payload and pricing version in the Study database rather than relying on later LangSmith price changes.

### 26. Define trace volume and export controls

The proposal does not define sampling, a monthly trace budget, or a way to stop export without stopping the Study API.

For approved study sessions, transcript traces may need full coverage so the research record can be reconciled. Operational connection events can use a separate allowlist and sampling rule. Add limits for runs per session, payload size, daily export volume, and failed outbox retention.

Use an application feature flag that selects a no operation exporter or the outbox worker. Do not assume `LANGSMITH_TRACING=false` disables every SDK path. LangSmith's direct `RunTree` API sends when a run is posted, independently of the decorator tracing flag.

### 27. Define normal observability outside LangSmith

LangSmith is for model traces, not the only service monitoring system. Add structured application logs, request IDs, database metrics, outbox backlog metrics, Realtime connection metrics, and alerts. Define service objectives for message success, transcript durability, completion success, Realtime setup, and outbox delivery.

Never put participant text, access tokens, Realtime secrets, or Supabase JWTs in application logs.

Create a separate server generated audit stream for staff access, transcript export, role and study membership changes, configuration publication, Realtime credential issuance, consent, correction, retention changes, and deletion. Keep participant reported events separate from audit records. Audit records should name the actor, study, action, object, authorization result, request ID, timestamp, and object version without copying transcript text.

### 28. Clarify what "voices" means

The initial spec says LangSmith will track "the transcripts and the voices." See `2026-08-06-init-specs.md:3-10`. The later proposals explicitly exclude raw audio.

Revise the initial spec to say that the first integration records transcript text, voice configuration, interruption state, and approved timing and usage fields. It does not record raw audio.

### LangSmith product wording corrections

The proposal should make several current API details precise:

* Replace "upsert run" with "create or update using a persisted run ID." LangSmith documents separate create and update operations. A repeated create is not a general update contract.
* Generate and persist one LangSmith UUID version 7 ID per exported root and child run. Do not assume an existing Study UUID has the recommended version or time ordering.
* Use `thread_id` as the canonical metadata key. `session_id` is only a fallback compatibility key, and it must match when both are present.
* Keep `ls_provider` and `ls_model_name` in run metadata. Set `usage_metadata` through the supported run field, and do not nest provider or model names inside it.
* Use a `new_token` event only for the first streamed output token under the chosen convention. Keep first audible audio as a separate metric instead of silently presenting it as text TTFT.
* State that `LANGSMITH_WORKSPACE_ID` is required only for the key and workspace combinations documented by LangSmith, rather than for every workspace scoped key.
* Replace references to run "upsert" in the endpoint table with create or update using the stored run ID.

## Proposed canonical component boundaries

| Component | Owns | Must not own |
| --- | --- | --- |
| Participant UI | Microphone permission, local audio state, temporary partial text, and client observations | Study assignment, canonical AI turns, model credentials, completion truth, or research exports |
| Study API | Capability validation, lifecycle rules, concurrency control, text generation commands, Realtime setup, and staff authorization | Long running trace delivery in the participant request |
| Study Postgres | Sessions, immutable configuration snapshots, canonical turns, revisions, events, completion, audit records, and any selected delivery state | Model trace rendering |
| Realtime control worker | Authenticated call ID handoff, sideband monitoring, provider event ingestion, tool handling, and provider identifier mapping | Participant identity or study analysis |
| Trace export worker, if complete export is required | Redacted LangSmith projection, retries, persisted run IDs, and reconciliation | Authoritative transcript mutation |
| LangSmith | Derived traces, thread views, latency, usage, cost, and later experiments | Participant access control, canonical transcripts, consent truth, or completion state |
| Supabase Auth | Staff identity and sessions | Participant link access or Study API authorization decisions by itself |

## Proposed participant API boundary

The participant API should be capability scoped, so the browser does not choose a session ID on every request.

| Method and path | Input | Authority and retry rule |
| --- | --- | --- |
| `POST /v1/participant-access/exchange` | One time invitation token | Validates the token hash, sets the participant capability, and returns the participant session view |
| `GET /v1/participant-session` | Participant capability | Returns only the public projection for the capability's session |
| `POST /v1/participant-session/start` | Preferred mode, `Idempotency-Key`, and expected session version | Creates one lifecycle transition and, when configured, one opening generation operation |
| `POST /v1/participant-session/messages` | Participant text, client message ID, and `Idempotency-Key` | Creates participant text and one backend owned AI generation operation |
| `POST /v1/participant-session/realtime/calls` | Browser SDP, `Idempotency-Key`, and expected session version | Creates one server configured Realtime call, persists the call ID from the provider `Location` header, queues the control handoff, and returns only the SDP answer |
| `POST /v1/participant-session/observations` | Versioned allowlisted browser observations | Records client observations without turning them into canonical provider facts |
| `GET /v1/participant-session/transcript` | Participant capability and optional cursor | Returns the canonical participant projection in server order |
| `POST /v1/participant-session/complete` | Completion reason, final participant recovery observations, `Idempotency-Key`, and expected session version | Atomically records valid final data and completion |

The public API should not expose a general turn upsert. Staff APIs should use a separate route group, a verified Supabase JWT, and explicit role checks.

## Proposed minimum data model

### Session

```text
session_id
participant_capability_hash
telemetry_thread_id
study_id
status
version
writer_lease_id                    # when the selected concurrency strategy uses leases
writer_lease_expires_at
configuration_snapshot_id
consent_version                    # when the approved protocol requires a consent gate
consented_at
consent_profile
started_at
completed_at
completion_reason
created_at
updated_at
```

### Configuration snapshot

```text
configuration_snapshot_id
study_wave
protocol_version
issue_version
persona_version
prompt_content_hash
prompt_object_reference
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

### Outbox event when complete export is required

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

## Proposed trace envelope

Every LangSmith run should come from a validated envelope built from committed records:

```text
trace_schema_version
trace_policy_version
trace_kind
langsmith_run_id
telemetry_thread_id
canonical_turn_id
provider_response_id
ls_agent_type
ls_message_format
study_wave
protocol_version
configuration_snapshot_id
issue_version
prompt_version
avatar_version
voice_version
interaction_mode
model_provider
model_name
frontend_build_revision
backend_build_revision
metric_source
approved_inputs
approved_outputs
usage
timing
```

Do not copy arbitrary database metadata into the envelope. The redaction and allowlist step should fail closed.

## Required contract tests

### Participant API

* A missing, expired, revoked, or wrong session capability cannot read or mutate a session.
* A completed session cannot mint a Realtime credential or add a new canonical turn.
* The same idempotency key and request hash returns the same response.
* The same idempotency key with a different request hash returns a conflict.
* Under a lease based concurrency policy, a stale writer lease cannot mutate the session.
* Two simultaneous start or completion requests produce one transition.
* Unknown input fields and oversized payloads are rejected.
* When the approved protocol requires consent, session start, Realtime setup, and tracing are blocked without the required consent version.
* A staff member cannot read a session outside the staff member's current study membership.

### Transcript integrity

* A browser cannot create AI or system turns.
* A duplicate provider item maps to one canonical turn.
* A conflicting duplicate ID does not overwrite text.
* A completion transaction either saves all final records or saves none.
* An interruption preserves generated, delivered, and displayed text according to the protocol.

### Realtime

* The backend creates the provider session from an immutable configuration snapshot.
* The browser never receives the standard OpenAI API key.
* A sideband disconnect is detected and recorded.
* Reconnect and secret refresh do not create a second canonical conversation.
* Provider usage and browser observations remain distinguishable.
* Closing or crashing the browser at each point in final turn delivery does not lose an acknowledged provider item.
* Reconciliation reports provider item gaps instead of silently treating an incomplete transcript as complete.

### LangSmith

* A database commit succeeds when LangSmith is unavailable.
* Under a complete export policy, every eligible committed AI turn produces one outbox event and one LangSmith run.
* Worker retries reuse the persisted run ID.
* Every run has the pseudonymous thread metadata.
* Redaction tests prove that tokens, emails, invitation values, and disallowed prompt fields are absent.
* Reconciliation finds a missing or failed export.
* Thread token and cost totals include child runs when child runs exist.
* Top level turn traces render with ordered message inputs and outputs in the current Messages and Turns views.

### Operations

* Readiness changes according to the configured service role and required dependencies.
* When durable export is enabled, outbox backlog and repeated export failure trigger alerts.
* A deletion test removes or tombstones the database record and deletes the mapped LangSmith runs under the approved policy.
* Production configuration rejects synthetic defaults and local LangSmith projects.
* A database restore preserves transcript hashes, ordering, configuration snapshots, audit records, and pending outbox work.
* The current and previous supported UI versions pass the same API contract suite.

## Decisions that need named owners

| Decision | Why it blocks the design | Safe default |
| --- | --- | --- |
| Participant link and capability format | It defines every participant API trust boundary | One time random link token exchanged for a short lived capability |
| One device or device transfer rule | It defines concurrency and retry behavior | One active writer lease with explicit transfer |
| Realtime unified setup and sideband use | It defines control, transcript provenance, and trusted metrics | Server mediated setup plus sideband monitoring |
| Canonical meaning of an interrupted AI turn | It changes the research transcript | Preserve generated and delivered text separately |
| Voice timing definitions | First audio and first text are different measures | Record both as separate client observed metrics |
| Study database host and migration owner | The proposals name Postgres but not its owner | One private Postgres database owned by the Study API |
| Staff role matrix | Authentication alone does not authorize research actions | Deny by default and grant named actions by role |
| Trace field allowlist and retention | Production tracing exports participant text | Export nothing until an approved policy version exists |
| Raw audio retention | The initial wording can be read as audio collection | Do not record raw audio |
| Configuration snapshot contents | Version labels alone are not reproducible | Store immutable content hashes and exact provider settings |

## Suggested implementation order

1. Freeze the participant capability, state machine, concurrency, idempotency, provenance, and error contracts.
2. Choose the Study database location and write the schema and unique constraints.
3. Implement the API against durable storage, including atomic completion and any trace delivery record required by the selected guarantee.
4. Implement server mediated Realtime setup and sideband ingestion in a staging environment.
5. Approve the trace policy, retention, access, and deletion rules.
6. Implement the selected LangSmith export path with one root trace per AI generation.
7. Run concurrency, failure injection, redaction, reconciliation, and browser pilot tests.
8. Build versioned research exports and only then decide whether to add LangSmith datasets and evaluators.

## Current documentation checked

The following current documentation supports the LangSmith and Realtime revisions:

* [LangSmith threads](https://docs.langchain.com/langsmith/threads) requires thread metadata on every parent and child run for filtering, token totals, and cost totals.
* [LangSmith observability concepts](https://docs.langchain.com/langsmith/observability-concepts) defines a thread as a sequence of traces rather than one session wide trace.
* [LangSmith Messages view trace format](https://docs.langchain.com/langsmith/messages-view-trace-format) documents the top level message shape and root metadata used by the current view.
* [LangSmith Messages view integrations](https://docs.langchain.com/langsmith/messages-view-integrations) documents current integration requirements and limitations.
* [LangSmith custom instrumentation](https://docs.langchain.com/langsmith/annotate-code) recommends UUID version 7 custom run IDs and documents deterministic IDs for idempotency.
* [LangSmith LLM traces](https://docs.langchain.com/langsmith/log-llm-trace) documents `run_type="llm"`, message shaped input and output, model metadata, usage metadata, and `new_token` events.
* [LangSmith cost tracking](https://docs.langchain.com/langsmith/cost-tracking) documents provider and model metadata, token usage, and optional direct cost fields.
* [LangSmith data masking](https://docs.langchain.com/langsmith/mask-inputs-outputs) documents pre-ingestion hiding and transformation of inputs, outputs, and metadata.
* [LangSmith usage, billing, and retention](https://docs.langchain.com/langsmith/usage-and-billing) documents current retention behavior.
* [LangSmith data purging and compliance](https://docs.langchain.com/langsmith/data-purging-compliance) documents retention and deletion behavior.
* [OpenAI Realtime WebRTC](https://developers.openai.com/api/docs/guides/realtime-webrtc) documents the unified server setup and ephemeral token setup.
* [OpenAI Realtime conversations](https://developers.openai.com/api/docs/guides/realtime-conversations) documents client and server session update events.
* [OpenAI Realtime server controls](https://developers.openai.com/api/docs/guides/realtime-server-controls) documents a sideband server connection for WebRTC sessions.
* [Supabase advanced server Auth guidance](https://supabase.com/docs/guides/auth/server-side/advanced-guide) explains why the standard browser based `@supabase/ssr` flow does not use HTTP only cookies.
