# LangSmith proposal

## Recommendation

LangSmith is a derived operational projection of study conversations. The Study API and Study Postgres are the system of record for sessions, canonical transcript turns, completion status, consent, and study configuration. Railway hosts the Study API, Study Postgres, and any export worker. LangSmith must not be used for access control, consent, completion, or canonical transcripts.

The first LangSmith integration should help researchers and engineers inspect approved conversation traces. The same integration should also measure trusted AI latency and usage, and help debug model behavior. Later evaluation products stay out of the LangSmith proposal.

The first integration covers:

* Conversation traces grouped by a pseudonymous `telemetry_thread_id`
* Trusted generation metrics, including first streamed output token time when an instrumented text call exists, total latency when start and end times exist, token usage from a trusted provider record, and cost when trusted usage exists

The first integration leaves out:

* Automated evaluators
* Annotation queues
* Frozen dataset schemas for offline scoring
* Experiments and A/B comparison tables
* Human feedback scoring workflows in LangSmith

Datasets and evaluators can be added later from versioned Study Postgres exports, after the research team chooses measures.

## Design principles

### Study API and Study Postgres are the system of record

A turn saved once in Study Postgres must remain correct even if a retry posts a second LangSmith run, or if LangSmith is missing. LangSmith traces are a projection. If LangSmith is down, session completion must still succeed.

### LangSmith is never the access or consent boundary

Participant access uses a capability separate from the internal study `session_id`. Invitation tokens, public route IDs, participant identifiers, and email addresses must not appear in LangSmith. When the approved study protocol requires formal consent, missing or withdrawn consent blocks OpenAI transmission, transcript persistence, and LangSmith export. Microphone permission is not research consent.

### One root conversation turn trace per AI generation

Create one root `conversation_turn` trace for each AI generation operation. Put the participant message and the resulting AI message in the root trace top level `inputs.messages` and `outputs.messages`. Put an instrumented LLM call under the root as a child run when an instrumented call exists. Group the root traces with the same pseudonymous UUID version 7 `telemetry_thread_id` stored in Study Postgres.

Do not use the internal study `session_id` as LangSmith `thread_id`. Do not keep one root run open across start, turns, and completion for the whole session. Session start, session complete, and notable connection failures are independent root traces or ordinary database events.

LangSmith thread filtering and aggregate token and cost totals need thread metadata on every parent and child run. Add the thread metadata through one trace envelope builder. Do not rely on call context surviving across HTTP requests.

### `thread_id` is the canonical grouping key

Set `metadata.thread_id` to `telemetry_thread_id` on every parent and child run. If a compatibility `session_id` metadata key is also present, it must match `thread_id`, and both values must be `telemetry_thread_id`. Do not put the internal study `session_id` in LangSmith.

### True best effort delivery is the default

Participant requests never wait for LangSmith. Gaps in traces are accepted. The plan must not claim that every eligible turn appears in LangSmith.

If complete and reconcilable export is later required, a versioned outbox plus persisted UUID version 7 run IDs is mandatory. Under either contract, build traces only from committed canonical records. Reuse stored run IDs on retries. Keep LangSmith failure from failing completion.

### Fail closed on the envelope

Build every LangSmith run from a versioned allowlist. Reject unknown fields. Apply redaction before any export path writes. Do not copy free form client metadata, invitation tokens, public route IDs, emails, access tokens, or Realtime secrets.

### Preserve reproducibility without freezing evaluators

Keep immutable configuration snapshots, canonical and revised transcripts, export manifests, trace schema versions, stable turn and provider IDs, consent and trace policy versions, and the code version used to produce each derived export. Do not freeze dataset or evaluator schemas in the LangSmith proposal. Later datasets should come from Study Postgres exports, not from a mutable LangSmith project view.

## How LangSmith fits the architecture

```text
Participant browser (Vercel)
  |  capability scoped session API, observations, voice SDP
  v
Study API on Railway
  |  command validation, text generation, Realtime setup
  |  writes canonical records to Study Postgres
  v
Study Postgres
  |  sessions, snapshots, canonical turns, revisions, events
  |  telemetry_thread_id, consent, optional outbox rows
  v
Trace export path (best effort post, or outbox worker if complete export is chosen)
  v
LangSmith project for the deployment environment
  Threads: one per telemetry_thread_id
  Runs: one conversation_turn root per AI generation
  Metrics: trusted timing, usage, and cost when present
```

Railway is the host. Study Postgres is the store. LangSmith is the derived view.

Voice in the LangSmith plan means approved configuration, interruption state, transcript text, and approved timing and usage fields. Voice does not mean raw audio. The first integration does not record raw audio in Study Postgres or in LangSmith.

## Text mode

The Study API mediates text generation so traces can freeze around a real model call.

1. The UI posts participant text to `POST /v1/participant-session/messages` with an idempotency key.
2. The Study API creates the participant turn after the write commits.
3. The Study API calls OpenAI through an instrumented client.
4. The Study API creates the canonical AI turn.
5. The export path builds a root `conversation_turn` trace from the committed records, with an instrumented LLM child when the wrapped call produced one.

Use `langsmith.wrappers.wrap_openai` or an equivalent instrumented client for `instrumented_text_generation`. `wrap_openai` applies to Chat Completions style calls on the Study API. `wrap_openai` does not instrument OpenAI Realtime.

Model text generation as an operation with `accepted`, `running`, `succeeded`, and `failed` states. A retry with the same idempotency key and request hash returns the stored operation and AI response, and it reuses stored LangSmith run IDs instead of calling the model again.

## Voice mode

Server mediated Realtime setup plus a sideband connection is the intended trusted metric source. The Study API submits the browser SDP with the server owned session configuration. The Study API persists the OpenAI call ID from the provider `Location` header, and enqueues a control handoff to the sideband worker. The browser receives the SDP answer. The browser does not receive the call ID or the standard OpenAI API key.

A reconstructed voice LLM run is not instrumented generation. Realtime also keeps conversation context across responses, so the latest participant turn alone is not the full input that affected an AI response.

Set `trace_kind` to one of:

* `instrumented_text_generation` for a Study API mediated text call that used `wrap_openai` or an equivalent wrapper
* `provider_observed_realtime_response` for a response observed through trusted sideband provider events
* `client_reconstructed_voice_turn` for a turn rebuilt from final transcript text and client observations

Mark latency and usage unknown unless a trusted source supplies them. Do not present a reconstructed turn as a complete Playground model call.

Browser observations use a separate allowlisted model and remain untrusted, e.g. first audio heard. Provider usage, model identity, and server timing use trusted server or provider fields.

## Trace model

### Thread grouping

| Field | Value |
| --- | --- |
| Canonical LangSmith thread key | `metadata.thread_id` |
| Value | UUID version 7 `telemetry_thread_id` stored in Study Postgres |
| Compatibility key | `metadata.session_id` only if needed, and only equal to `telemetry_thread_id` |
| Forbidden | Internal study `session_id`, invitation token, public route ID |

Keep the mapping from `session_id` to `telemetry_thread_id` in Study Postgres. Researchers open the Threads view by the telemetry thread, not by the internal study session ID.

### Recommended run tree

```text
conversation_turn (chain)                 # one root per AI generation
  llm (llm)                               # child only for instrumented_text_generation
                                          # or a provider observed Realtime child when
                                          # trusted sideband events exist

session_lifecycle (chain)                 # independent root for start or complete
connection_failure (chain)                # independent root, sparse, high signal only
```

Keep the first version simple:

* One root `conversation_turn` per AI generation
* Participant and AI messages on the root `inputs.messages` and `outputs.messages`
* An instrumented LLM child when the text wrapper produced a real call
* Independent roots or database events for session start, session complete, and notable connection failures

A stored opening AI turn from the configuration snapshot is not an AI generation. Do not export it as a `conversation_turn` root. Keep it in Study Postgres as canonical transcript text. A later lifecycle root may note that start returned opening content, without treating the snapshot text as a model call.

Do not create a LangSmith run for mute toggles, audio levels, or audio check media.

For current LangSmith Messages and Turns views, mark the top level trace with the documented root agent metadata and set the documented message format when manual instrumentation needs it. Treat the Messages view as a pilot acceptance check, because the current view is still described as beta.

### Trace envelope

Every LangSmith run comes from a validated envelope built from committed records:

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

The redaction and allowlist step should fail closed. Do not copy arbitrary database metadata into the envelope.

Keep `ls_provider` and `ls_model_name` in run metadata. Set `usage_metadata` through the supported run field. Do not nest provider or model names inside `usage_metadata`.

Optional tags can repeat allowlisted facts already in metadata:

```text
study-wave:<study_wave>
mode:voice
mode:text
status:completed
trace-kind:instrumented_text_generation
```

### Transcript payload shape

For instrumented text LLM children, prefer OpenAI style messages so LangSmith can render conversations:

```python
inputs = {
    "messages": [
        {"role": "system", "content": "<approved prompt excerpt or omitted>"},
        {"role": "user", "content": "<canonical participant turn text>"},
    ]
}

outputs = {
    "messages": [
        {"role": "assistant", "content": "<canonical AI display text>"},
    ]
}
```

If the approved `trace_policy_version` does not allow storing full system instructions in LangSmith, send a prompt version string or content hash. Keep the full prompt only in Study Postgres.

For voice, store separate canonical facts in Study Postgres and export only the fields the policy allows:

* Provider generated content
* Content delivered before interruption
* Final transcript text shown to the participant
* Interruption time and provider item ID
* Any participant approved correction as a revision, not an overwrite

The research team chooses which field is exported as what the AI said. Record the choice in a versioned export manifest.

### Run identifiers

Generate and persist one LangSmith UUID version 7 ID per exported root and per exported child. Do not assume an existing Study UUID is version 7 or time ordered.

Create or update using the persisted run ID. LangSmith documents separate create and update operations. A repeated create is not a general update contract.

Retrying an export for the same canonical AI turn must reuse the stored root and child run IDs so a second copy is not created.

Include reconciliation keys already in the allowlist, such as `canonical_turn_id` and `provider_response_id`. Do not add the internal study `session_id`.

## AI metrics in scope

Record timing fields separately. First audio is not time to first token.

| Field | Meaning | Trust |
| --- | --- | --- |
| `server_generation_started_at` | Study API start of a mediated generation | Server |
| `provider_first_output_at` | First provider output from a trusted source | Provider or sideband |
| `client_first_audio_observed_ms` | First audible AI audio heard in the browser | Client observed |
| `client_first_transcript_observed_ms` | First transcript token observed in the browser | Client observed |
| `generation_completed_at` | End of the generation span from the chosen source | Named in `metric_source` |
| `metric_source` | Which source supplied the timing and usage | Required |
| `clock_basis` | Which clock the durations used | Required |

Use durations measured by one monotonic clock when the browser reports two local observations. Do not subtract unrelated browser and server wall clocks. Prefer provider events collected through the sideband connection for canonical operational metrics.

Use a `new_token` event only for the first streamed output token on an instrumented text call. Keep first audible audio as `client_first_audio_observed_ms`. Do not silently present first audio as text time to first token.

Do not use browser supplied token counts or cost as authoritative. Use provider usage. Leave cost absent when no trusted usage record exists.

For automatic or manual cost tracking on an instrumented or provider observed run, include:

* `metadata.ls_provider` set to `"openai"` when OpenAI is the provider
* `metadata.ls_model_name` set to the chat or Realtime model ID actually used
* `usage_metadata` with at least `input_tokens` and `output_tokens` when a trusted usage record exists

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

Configure model pricing in LangSmith when the selected OpenAI models are not priced automatically. If exact research cost must be reproducible, store the provider usage payload and pricing version in Study Postgres rather than relying on later LangSmith price changes.

Other ordinary run fields stay in scope without becoming an eval product:

* Total AI turn latency when trusted start and end times exist
* Session duration from Study Postgres, if exported as lifecycle metadata
* Error rate on Realtime connect, turn save, and completion, in application metrics rather than as LangSmith feedback scores
* Mode mix of voice versus text turns per telemetry thread

Do not add custom LangSmith feedback scores yet.

## Delivery guarantee

True best effort is the default.

* Participant requests never wait for LangSmith
* Trace gaps are accepted
* The plans must not claim that every eligible turn appears in LangSmith
* Tracing failures are logged without participant text or secrets
* Completion never depends on LangSmith availability
* LangSmith IDs are never a required participant response field

If complete and reconcilable coverage becomes a requirement, commit a versioned outbox event with the study record. Export the event through a worker with persisted UUID version 7 run IDs. Record retries, terminal failures, and reconciliation state.

Under either contract:

* Build traces only from committed canonical records
* Reuse the stored run ID on retries
* Keep LangSmith failure from failing session completion

### Outbox model when complete export is required

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

The payload is the redacted envelope, not a copy of the raw database row. Failed outbox rows may still contain transcript text. Say so in the retention policy, and bound how long failed rows are kept.

## Feature flag, environment, and projects

Use an application feature flag to select a no-op exporter or the export worker. Do not assume `LANGSMITH_TRACING=false` disables every SDK path. LangSmith's direct `RunTree` API sends when a run is posted, independently of the decorator tracing flag.

Set LangSmith secrets on Railway only:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=issue-discussion-platform
```

Set `LANGSMITH_WORKSPACE_ID` only when LangSmith docs require it for the documented key and workspace combination. Do not require the workspace ID for every workspace scoped key.

Use separate LangSmith projects for local, staging, and production. Local, staging, and production are security and operational boundaries:

* `issue-discussion-local`
* `issue-discussion-staging`
* `issue-discussion-prod`

Put study wave, protocol version, and configuration snapshot ID in immutable metadata inside the production project. Create a separate production project for a wave only when access or retention rules differ.

Local and staging projects must reject real participant data. Production configuration must reject synthetic defaults and local LangSmith projects.

## Wiring into the Study API

Add a tracing service behind an interface so Sample contracts can no-op, Durable record can persist IDs without sending, and Approved tracing can export.

```text
backend/app/services/tracing.py
```

Suggested methods, named for study records rather than for one root run that stays open for the whole session:

```python
class StudyTracingService(Protocol):
    def on_session_started(self, session: SessionDomain) -> None: ...
    def on_generation_committed(
        self,
        session: SessionDomain,
        participant_turn: CanonicalTurn | None,
        ai_turn: CanonicalTurn,
        operation: GenerationOperation,
    ) -> None: ...
    def on_session_completed(self, session: SessionDomain) -> None: ...
    def on_connection_failure(self, session: SessionDomain, event: SessionEvent) -> None: ...
```

`on_session_started` and `on_session_completed` create independent root traces or skip LangSmith and keep database events only. The methods do not open or close a parent run that spans the whole session.

### Endpoint touchpoints

| Backend action | LangSmith action |
| --- | --- |
| `POST /v1/participant-session/start` | Optional independent lifecycle root, or a database event only. No parent run that spans the whole session. |
| `POST /v1/participant-session/messages` | After commit, create or update a `conversation_turn` root and an instrumented LLM child using persisted UUID version 7 IDs. |
| Voice provider item committed from sideband or recovery | After commit, create or update a `conversation_turn` root with `trace_kind` `provider_observed_realtime_response` or `client_reconstructed_voice_turn`. |
| `POST /v1/participant-session/observations` | Do not turn observations into canonical LLM runs. Attach allowlisted timing only when the policy says so. |
| `POST /v1/participant-session/complete` | Independent lifecycle root or database event. Never wait for LangSmith. Write any outbox row required by the selected guarantee inside the completion transaction. |
| `POST /v1/participant-session/realtime/calls` | Do not send the SDP, call ID, or client secret to LangSmith. A credential mint can be an audit record in Study Postgres. |

There is no public turn create-or-replace route. Canonical text turns belong to the messages command. Voice ingestion uses provider identified final items or narrower recovery observations.

## What researchers will see

In the LangSmith project for the matching environment, researchers can:

* Filter threads by study wave, issue version, or other allowlisted metadata
* Open one thread per `telemetry_thread_id`, made of many `conversation_turn` traces
* Use Messages and Turns views as a pilot check, knowing Messages is still described as beta
* Read per AI turn latency when trusted start and end times exist
* Read first streamed output token time on instrumented text children that emitted `new_token`
* Read token and cost totals per turn and rolled up per thread when child runs exist and usage metadata is present
* Separate prompt versions, avatars, voices, and modes with tags and metadata

Scoring how participants disagree can remain an offline research process using Study Postgres exports. LangSmith is the operational transcript and metrics viewer, not the canonical research file.

## Data handling, retention, deletion, and access

Production tracing stays disabled until the plan specifies, and then enforces:

* The approved fields for each study wave
* Retention in Study Postgres and in LangSmith
* Who can read traces and exports, checked by study membership
* How a withdrawal or deletion request finds and deletes all related runs
* Whether backups and failed outbox payloads contain transcript text
* How local and staging environments prevent real participant data
* How access and deletion actions are audited

The default is no raw prompt or transcript export until an approved `trace_policy_version` is attached to the session. Masking and anonymization must happen before ingestion when sensitive fields must never leave the Study system.

LangSmith Cloud retention applies to new traces. A later project retention change does not rewrite existing traces.

Whole trace deletion is asynchronous. The deletion workflow must keep a tombstone and confirm completion, instead of assuming immediate removal. Backups and failed outbox payloads may still contain text after a tombstone is written.

Staff export, deletion, and access changes require recent authentication and an audit record. The audit record names the actor, study, action, object, authorization result, request ID, timestamp, and object version, without copying transcript text.

Defaults for the first integration, until a policy version says otherwise:

* Export no raw prompt text
* Export no participant transcript text
* Store no raw audio in LangSmith
* Store no audio check data
* Treat cost as an engineering and pilot metric, not a formal study outcome

## Sampling and export limits

Approved study transcript traces may need full coverage if complete export is chosen, so the research record can be reconciled. Operational connection events can use a separate allowlist and sampling rule.

Add limits for:

* At most 400 exported runs per session
* Envelope payload at most 64 KiB
* Daily export volume at most 50,000 runs per production project
* Failed outbox rows retained 14 days, then tombstoned

Study Postgres retains canonical transcripts for 7 years or until an approved deletion request completes, whichever the protocol requires. LangSmith uses the project's current base retention for new traces. The deletion operator is the study_admin role, with Study API on-call confirming LangSmith purge completion.

When durable export is enabled, outbox backlog and repeated export failure should trigger alerts. OpenAI and LangSmith outages should appear in dependency health metrics without necessarily removing API readiness.

## Application observability outside LangSmith

LangSmith is for model traces. It is not the only service monitoring system.

Add structured application logs, request IDs, database metrics, outbox backlog metrics, Realtime connection metrics, and alerts. Define service objectives for message success, transcript durability, completion success, Realtime setup, and outbox delivery.

Never put participant text, access tokens, Realtime secrets, or Supabase JWTs in application logs.

Keep a separate server generated audit stream for staff access, transcript export, role and study membership changes, configuration publication, Realtime credential issuance, consent, correction, retention changes, and deletion. Keep participant reported events separate from audit records.

## Shared milestones

Replace numbered phase labels with the shared names below. LangSmith work maps onto the shared names instead of a conflicting Phase 1 label.

### Sample contracts

Implement `StudyTracingService` as a no-op exporter selected by the feature flag. Keep LangSmith env vars unset in local UI work. Prove the generation commit, start, complete, and connection failure hooks exist without sending data to LangSmith.

Review questions:

* Are the hook points correct for generation commit, start, complete, and connection failure?
* Is `telemetry_thread_id` available everywhere a later `thread_id` will be needed?
* Can tracing be disabled with the application feature flag, including RunTree posts?

### Durable record

When Study Postgres lands, store fields needed for later reconciliation. Include turn IDs, provider item IDs, timestamps, mode, model name, `telemetry_thread_id`, consent version, and optional generation metrics. Continue no-op or local dry run logging. Persist UUID version 7 LangSmith run IDs even before live export, if complete export is already selected.

Review questions:

* Can a thread be reconstructed from Study Postgres alone?
* Are generation metric fields validated even before LangSmith is enabled?
* Are stored run IDs UUID version 7, rather than reused Study UUIDs?

### Voice control

Enable server mediated Realtime setup and sideband ingestion in staging. Prefer `provider_observed_realtime_response` traces. Keep `client_reconstructed_voice_turn` marked incomplete for Playground use, with unknown latency and usage unless a trusted source exists.

Review questions:

* Are provider usage and browser observations distinguishable in the envelope?
* Is first audio stored separately from first streamed output token time?

### Approved tracing

Enable LangSmith in staging, then production, only after an approved `trace_policy_version`, retention, access, and deletion rules exist.

1. Create the environment LangSmith project and API key on Railway.
2. Trace text mode with wrapped OpenAI as `instrumented_text_generation`.
3. Trace voice from committed records with the correct `trace_kind`.
4. Attach `thread_id` and allowlisted metadata on every parent and child through the envelope builder.
5. Emit `new_token` only for the first streamed output token on instrumented text.
6. Populate `usage_metadata` from trusted provider usage when available.
7. Verify Threads, latency, and cost views with pilot sessions, and treat Messages view as a beta pilot check.

Pilot checklist:

* A text only session appears as one thread of ordered `conversation_turn` traces
* A voice session transcript appears without raw audio, and reconstructed turns are not shown as complete Playground model calls
* Duplicate export attempts reuse persisted run IDs
* Completion works when LangSmith is unreachable
* Cost shows for at least the instrumented text path
* First streamed output token time shows for streaming text when the wrapper emits `new_token`
* First audio, if present, is a separate client observed metric

### Research export

Build versioned research exports from Study Postgres. Only then decide whether to add LangSmith datasets and evaluators. Dataset examples should later carry source identifiers, transcript revision, treatment assignment, configuration hash, trace policy version, curator, and dataset version. Online evaluator scores should remain operational signals until the study validates them against human ratings. Record an architecture decision later on whether evaluation operates at the turn or full thread level.

## LangSmith contract tests

* A database commit succeeds when LangSmith is unavailable
* Under a complete export policy, every eligible committed AI turn produces one outbox event and one LangSmith run
* Worker retries reuse the persisted run ID
* Every run has the pseudonymous thread metadata
* Redaction tests prove that tokens, emails, invitation values, internal study session IDs, and disallowed prompt fields are absent
* Reconciliation finds a missing or failed export
* Thread token and cost totals include child runs when child runs exist
* Top level turn traces render with ordered message inputs and outputs in the current Messages and Turns views
* When the approved protocol requires consent, tracing is blocked without the required consent version
* A deletion test tombstones the database record and deletes the mapped LangSmith runs under the approved policy, then confirms asynchronous removal
* Production configuration rejects synthetic defaults and local LangSmith projects

## Implementation order

The backend plan owns participant capability, Study Postgres, atomic completion, and server mediated Realtime. LangSmith work starts after the backend contracts exist.

5. Approve the trace policy, retention, access, and deletion rules.
6. Implement the selected LangSmith export path with one root trace per AI generation.
7. Run concurrency, failure injection, redaction, reconciliation, and browser pilot tests.
8. Build versioned research exports and only then decide whether to add LangSmith datasets and evaluators.

## Current documentation checked

Current LangSmith and Realtime documentation supports the revisions:

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

## Decisions still needing named owners

| Decision | Why it blocks production tracing | Safe default |
| --- | --- | --- |
| Trace field allowlist and retention | Production tracing can export participant text | Export nothing until an approved policy version exists |
| Complete export versus true best effort | Outbox and run ID persistence depend on the guarantee | True best effort, with gaps accepted |
| Canonical meaning of an interrupted AI turn | Interrupted speech changes which text LangSmith may show | Preserve generated and delivered text separately, and name the export field in the manifest |
| Voice timing definitions | First audio and first text are different measures | Record both as separate fields, and treat first audio as not time to first token |
| Who can read the production LangSmith project | Access is a research data control | Deny by default, and grant named study membership |

## Initial scope

The first LangSmith build should include:

* A Study API tracing service interface and an application feature flag
* Thread grouping by `telemetry_thread_id`
* One `conversation_turn` root per AI generation, created or updated with a persisted UUID version 7 run ID
* `trace_kind` values for instrumented text, provider observed Realtime, and client reconstructed voice
* Envelope metadata for study wave, issue, prompt, avatar, voice, mode, snapshot, and policy versions
* Separate timing fields, with `new_token` only for first streamed output token
* Token and cost fields when trusted usage is available
* Safe failure behavior that never blocks participants
* Production gating on retention, deletion, access, and `trace_policy_version`

The first LangSmith build should exclude:

* Automated evaluators
* Annotation queues
* Experiments
* Frozen dataset upload schemas
* Feedback score collection in the participant UI
* Raw audio or video in traces
* Researcher facing LangSmith embeds inside the Next.js app
* Using the internal study `session_id` as `thread_id`
* A parent run that stays open for the whole session
* Treating first audio as time to first token
* Using `wrap_openai` on OpenAI Realtime
