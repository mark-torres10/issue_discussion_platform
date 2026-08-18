# UI proposal

## Recommendation

The first version should be a focused conversation experience with a short setup flow, one discussion screen, and one completion screen. The interface should tell the participant what will happen, help them test their microphone, keep the conversation easy to follow, and make it clear when the session is recording or saving data.

The product should identify the conversation partner as an AI participant. The AI can have a student style name, avatar, voice, and point of view, but the interface should not imply that a real student is present. Any study design that uses deception should be reviewed and approved through the research ethics process before it affects the interface.

Voice should be a mode within the same conversation, rather than a separate product. Participants should be able to use text if their microphone fails, if their environment is noisy, or if speaking is uncomfortable.

## Component boundaries

The participant UI is one part of a larger system. Named components are:

* **Study API.** Enforces participant and researcher commands.
* **Study Postgres.** Stores authoritative study records.
* **Railway.** Hosts the Study API and any worker.
* **LangSmith.** Stores a derived operational projection.
* **Supabase Auth.** Proves staff identity.

The participant UI owns microphone permission, local audio state, temporary partial text, and client observations. The participant UI must not own study assignment, canonical AI turns, model credentials, completion truth, or research exports.

Railway is the host for the Study API. Study Postgres is the authoritative store. LangSmith is not the study record.

## Design principles

### Keep the participant focused

The main screen should contain only the issue, the AI participant, the conversation, and the controls needed to continue or end the session. The screen should not include a general navigation menu, settings area, model selector, or unrelated dashboard.

### Explain what the system is doing

The participant should always be able to tell whether the system is listening, processing, speaking, muted, reconnecting, or finished. Voice interfaces feel broken when the state is unclear, even when the underlying service is working.

### Keep text and voice synchronized

Each spoken turn should appear in the local transcript after it is transcribed. The on-screen transcript gives participants a visual record, supports accessibility, and provides a text fallback when audio playback fails. The on-screen transcript is a local projection. The canonical transcript lives in Study Postgres and is read through the Study API.

### Use a calm visual style

The interface should use a neutral background, readable text, generous spacing, and one accent color. The avatar should add social presence without making the page feel like a game. Motion should be limited to useful state changes, such as a subtle speaking indicator.

### Protect participant control

The participant should explicitly start microphone access and should always have visible controls to mute, switch to text, or end the conversation. The site should never start recording when the page loads.

## Participant access

Participant access is not a staff login, and it is not proof of identity through a session UUID in the URL.

Each invitation uses a unique, single purpose link token. The token is separate from the internal `session_id`. The UI exchanges the token with `POST /v1/participant-access/exchange`. The Study API validates the token hash, sets a short-lived participant capability as an HTTP-only cookie, and returns the public participant session view.

After exchange, participant pages should use a route such as `/session`, `/session/audio-check`, `/session/conversation`, and `/session/complete`. The internal `session_id` stays out of public URLs, browser history as a public identifier, and LangSmith metadata.

The participant capability is required on every participant read and write, including Realtime setup. The capability is scoped to one session and a small set of allowed actions. The capability is separate from staff Supabase Auth. Participant routes remain outside Supabase Auth.

Because the capability uses a cookie, state changing requests need CSRF defense. Use an appropriate `SameSite` setting, strict `Origin` verification, and a CSRF token when the deployment model requires one. CORS alone is not a CSRF control.

If the same invitation is opened on a second device, the second device stays read-only until the participant completes an explicit writer lease transfer. The first writer keeps the lease until transfer succeeds.

## Participant journey

### Open the assigned session

The participant follows a unique invitation link. The UI sends the invitation token to the Study API. After a successful exchange, the UI loads the public session view, including the assigned issue, AI persona, study wave, and session rules from the configuration snapshot.

For the UI prototype under Sample contracts, the application can use fixed sample data instead of a real invitation token.

### Read the introduction

The introduction page explains:

* The participant will have a conversation with an AI participant.
* The AI will argue a specified position on a contested issue.
* The discussion will last about 5 to 10 minutes.
* The study will save a transcript and the measures approved by the study protocol.
* The participant can end the conversation at any time.
* The participant can use voice or text.

The page should use a short plain language summary.

Formal consent is a protocol and IRB gate, not a step that every study always requires. Microphone permission is not research consent. When the approved protocol requires formal consent, the UI must collect it before any OpenAI transmission, transcript persistence, or LangSmith export. Stored consent should include the consent version, timestamp, allowed data classes, and permitted interaction modes.

Approved participant wording should name relevant subprocessors. Voice is sent to OpenAI even when raw audio is not kept. "Voice" means approved configuration and metrics, not raw audio files. The application should not retain raw audio.

### Meet the AI participant

The participant sees the AI avatar, display name, short introduction, and assigned position. The display name should be clearly labeled as an AI participant.

The introduction should set expectations without revealing the full system prompt. For example, it can say that the AI will disagree respectfully, ask questions, and explain its position.

### Check audio

The participant selects voice or text. If they select voice, the browser asks for microphone permission only after they press a clear button.

The audio check should:

* Confirm that a microphone is available.
* Show an input level while the participant speaks.
* Play a short test sound through the selected output.
* Let the participant retry permission or continue with text.
* Explain that headphones can reduce echo.

The application should not save audio from the audio check.

### Start the discussion

The discussion screen renders exactly the turn returned by `POST /v1/participant-session/start`. The configuration snapshot decides who speaks first. The UI must not always open with an AI message.

If `ai_speaks_first` is true, the Study API returns stored opening content from the snapshot. The UI displays that returned turn. The UI must not invent an opening AI message in the browser.

The participant can respond by speaking or typing. Voice mode should support natural turn taking. Text mode should use a familiar message box with a send button.

The UI cannot create AI or system turns.

### Continue the discussion

The page shows the current conversation state near the avatar:

* "Listening" when the microphone is accepting speech.
* "Thinking" after the participant finishes a turn.
* "Speaking" while the AI audio is playing.
* "Muted" when the participant has disabled the microphone.
* "Reconnecting" when the voice connection has failed.

The on-screen transcript should distinguish participant turns from AI turns. New text should appear without moving the controls off screen.

If the research protocol allows interruption, the participant should be able to interrupt the AI while it is speaking. Interruption display should show that speech stopped, and it should keep local partial text separate from the canonical turn. Canonical voice AI output can store generated text, delivered text, display text, interruption time, and provider item ID as separate facts. The research team chooses which field is exported as what the AI said.

The header can show elapsed time and a small statement such as "About 3 minutes remaining." A large countdown may add pressure and change how participants speak, so the researchers should decide whether exact remaining time is part of the study protocol.

### End the discussion

The participant can press "End conversation" at any time. The application should ask for confirmation while the session is active, because an accidental end could invalidate a study session.

The application can also end the session when the assigned time expires. It should first give a neutral notice that the conversation is almost complete, then let the Study API produce a brief closing response when the snapshot allows one.

Completion uses `POST /v1/participant-session/complete` with an `Idempotency-Key` and expected session version. After complete, conversation writes stop. The UI can still read a minimal completed projection for a defined grace period. The projection can include status, completion time, and next instruction. After the grace period or explicit revocation, the Study API returns `410`.

### Confirm completion

The completion page confirms that the session was saved and gives the participant the next study instruction. It should not score, praise, or criticize how the participant handled the disagreement, because feedback could affect later study measures.

If saving fails, the page should keep retrying the same complete request with the same idempotency key and request hash, and it should tell the participant not to close the page while the request retries.

## Main discussion screen

### Desktop layout

The desktop page should use a narrow centered application frame. The frame has a compact header, a conversation area, and a fixed control area.

* A compact header with the issue title, session time, connection status, and an end button.
* A conversation area with the AI avatar and state at the top, followed by the scrollable transcript.
* A fixed control area with the microphone control, mute button, text input, captions control, and voice or text switch.

The transcript should receive most of the available space. The avatar can be prominent at the start of the session, then become smaller once the conversation begins.

### Mobile layout

The mobile page should use the same order in one column. The voice controls should remain within thumb reach at the bottom of the screen. The layout should account for the mobile browser toolbar and on screen keyboard.

### Avatar behavior

The first version should use a high quality static avatar image. A subtle ring or small audio indicator can show when the AI is speaking.

Lip synchronization and generated video should be deferred. They add delay, cost, browser load, and new consent questions without improving the core measure of disagreement skills. A static avatar also makes the UI prototype faster to test.

### Voice controls

The primary voice control should be one large microphone button with a text label. Color alone should not communicate microphone state.

The control area should also include:

* Mute and unmute.
* Stop AI audio.
* Switch to text.
* Turn live captions on or off.
* Report a connection problem.

The interface should show a clear microphone permission error with steps to retry. It should not send the participant to browser settings without first offering text mode.

### Accessibility

The interface should support keyboard navigation, visible focus states, screen reader labels, reduced motion, sufficient color contrast, and zoom up to 200 percent. Live transcript updates should use an accessible announcement strategy that does not read every partial transcription aloud.

Captions should be available in voice mode. The participant should be able to read AI messages even when audio is muted.

## Suggested visual direction

The visual style should resemble a focused university research activity:

* Use a warm neutral page background and a white conversation surface.
* Use Northwestern purple as a limited accent if university branding is approved.
* Use a readable sans serif typeface through `next/font`.
* Use rounded controls, but avoid a page made of many separate cards.
* Use one consistent avatar treatment across setup and conversation screens.
* Use simple line icons with visible text labels for important controls.

The avatar images should have consistent lighting, framing, and background treatment. The study team should decide whether demographic traits are randomized, matched, fixed, or excluded, because avatar traits could affect participant responses and become an uncontrolled study variable.

## Page structure

The initial application can use these routes:

```text
/
  Prototype entry or invitation link instructions

/invite/[token]
  One time invitation landing that exchanges the token, then redirects to /session

/session
  Session introduction and AI participant preview after capability exchange

/session/audio-check
  Microphone and speaker check

/session/conversation
  Text and voice discussion

/session/complete
  Save confirmation and next instruction from the completed projection

/session/unavailable
  Invalid, expired, paused, or post-grace completed session
```

An internal researcher interface can come later. Researcher pages should be a separate protected route group, because participant pages should not expose study controls or transcript search. Staff identity uses Supabase Auth. Participant capability cookies are not staff sessions.

## Recommended frontend setup

Use the current stable Next.js App Router with TypeScript and deploy it to Vercel. Use Tailwind CSS for layout and tokens, and use selected shadcn/ui components for accessible controls such as dialogs, buttons, tooltips, and text areas.

Use Server Components for pages that load public session configuration after the capability cookie exists. Keep the interactive conversation surface in a Client Component because it needs microphone access, WebRTC, audio playback, timers, and local connection state.

A practical source structure would be:

```text
src/
  app/
    layout.tsx
    page.tsx
    invite/
      [token]/
        page.tsx
    session/
      page.tsx
      audio-check/
        page.tsx
      conversation/
        page.tsx
      complete/
        page.tsx
      unavailable/
        page.tsx
  components/
    conversation/
      conversation-shell.tsx
      transcript.tsx
      transcript-message.tsx
      voice-controls.tsx
      text-composer.tsx
      avatar-presence.tsx
      connection-status.tsx
      session-timer.tsx
    session/
      participant-introduction.tsx
      audio-check.tsx
  lib/
    api/
      study-backend.ts
    realtime/
      client.ts
      events.ts
      state.ts
    types/
      session.ts
      transcript.ts
```

The application should use `next/image` for avatars. The avatar source should be approved and stored in a controlled location, rather than loaded from arbitrary participant supplied URLs.

## Participant API mapping

The browser does not choose a `session_id` on every request. Participant calls are scoped by the capability cookie.

| Method and path | UI input | Authority and retry rule |
| --- | --- | --- |
| `POST /v1/participant-access/exchange` | One time invitation token | Validates the token hash, sets the participant capability, and returns the participant session view |
| `GET /v1/participant-session` | Participant capability | Returns only the public projection for the capability's session |
| `POST /v1/participant-session/start` | Preferred mode, `Idempotency-Key`, and expected session version | Creates one lifecycle transition and, when configured, returns stored opening content from the snapshot |
| `POST /v1/participant-session/messages` | Participant text, client message ID, and `Idempotency-Key` | Creates participant text and one backend owned AI generation operation |
| `POST /v1/participant-session/realtime/calls` | Browser SDP, `Idempotency-Key`, and expected session version | Creates one server configured Realtime call and returns only the SDP answer |
| `POST /v1/participant-session/observations` | Versioned allowlisted browser observations | Records client observations without turning them into canonical provider facts |
| `GET /v1/participant-session/transcript` | Participant capability and optional cursor | Returns the canonical participant projection in server order |
| `POST /v1/participant-session/complete` | Completion reason, final participant recovery observations, `Idempotency-Key`, and expected session version | Atomically records valid final data and completion |

The public API should not expose a general turn upsert. The UI must not create AI or system turns, and it must not update an existing turn by posting different content for the same client ID.

Text send goes to `POST /v1/participant-session/messages`. Voice final facts come from the Study API and the provider. The browser posts observations such as first audio heard, local connection state, and microphone permission to `POST /v1/participant-session/observations`.

Duplicate requests retry with the same client IDs and the same idempotency key. Canonical turns are immutable. The same ID and same content hash returns the stored record. The same ID and different immutable content returns a conflict. The UI should not describe a client upsert that updates turn text.

## Local transcript and canonical transcript

Partial transcript text is temporary UI state. The local transcript can show streaming captions, interruption markers, and reconnect notices before the Study API acknowledges a canonical turn.

The canonical transcript is the participant projection from `GET /v1/participant-session/transcript`. Server order, speaker, origin, and content hash come from Study Postgres. After reconnect or refresh, the UI should replace local guesses with the canonical projection.

For interrupted AI audio, the local display can show that playback stopped. Canonical fields may still include generated text that was not delivered. The UI should not overwrite a canonical AI turn with a shorter local caption.

## Voice architecture

The current OpenAI product for low latency voice conversation is the Realtime API. The project should select the current supported realtime model during implementation instead of treating "GPT live" as a fixed model name.

For the production design, the browser should use WebRTC for microphone input and AI audio output. WebRTC is designed for low latency media and handles browser audio more reliably than sending audio chunks through ordinary HTTP requests.

The connection flow should be:

1. The participant starts voice mode after any required consent gate.
2. The Vercel UI calls `POST /v1/participant-session/realtime/calls` with the browser SDP, an idempotency key, and the expected session version.
3. The Study API on Railway validates the participant capability and the configuration snapshot, creates a server configured Realtime call, persists the provider call ID, and queues control handoff.
4. The browser receives the SDP answer only. The browser never receives the standard OpenAI API key or the provider call ID.
5. The browser sends and receives media. Unexpected client session updates are a backend detection problem, not a UI owned configuration change.
6. The browser posts allowlisted observations to the Study API. Final AI turns are created by the backend from trusted provider facts.
7. Study Postgres stores the authoritative study record. LangSmith receives approved derived traces later under Approved tracing.

The standard OpenAI API key must stay on the Study API host. It must never be included in the browser bundle or returned to the participant.

The Study API owns the system instructions, assigned issue, AI position, voice choice, time limits, and allowed tools through an immutable configuration snapshot. The browser should receive only the configuration needed to render the session. A participant must not be able to change the AI position or system instructions through browser requests.

LangSmith can trace model calls, events, transcript text, voice configuration, interruption state, and approved timing and usage fields. LangSmith does not record raw audio. Raw audio retention is out of scope. If a later study needs audio recordings, the consent language, retention period, access rules, encryption, and deletion process should be defined before recording is added.

## Crash recovery and browser storage

The browser should not be the only holder of a final AI turn. The Study API should acknowledge persisted provider item IDs and expose a reconciliation cursor. After a refresh, the UI reloads the canonical transcript.

IndexedDB or another persistent browser store is optional recovery for unsent participant observations, not a store of canonical AI text. If IndexedDB is used, the plan must define encryption at rest in the browser, expiry, cleanup on complete or revoke, and whether the consent profile allows local persistence. Prefer posting observations promptly and deleting local copies after the Study API acknowledges them.

Closing or crashing the browser during final turn delivery must not depend on the UI rewriting AI turns. Missing client observations can be retried. Missing provider items are a backend reconciliation report.

## Shared milestones

Named shared milestones replace numbered phases that meant different work in each document.

### Sample contracts

Build all participant pages with sample session data. The conversation page should use scripted participant and AI messages. Voice controls should change visible state but should not request microphone access or call an API.

The first review should answer:

* Does the study flow make sense without explanation?
* Does the participant understand that the partner is an AI?
* Is the assigned position clear?
* Are the voice states easy to understand?
* Does the design work on a phone and a laptop?

Add microphone permission, input level display, audio device errors, local timers, transcript scrolling, responsive behavior, and a simulated streaming response while the Study API is still mocked. Include tests for denied microphone permission, lost network connection, refresh during a session, and switching from voice to text.

Former UI Phase 1 (static UI) and former UI Phase 2 (browser behavior) map to Sample contracts.

### Durable record

Connect the Vercel UI to the Study API. Add invitation exchange, participant capability cookies, start, text messages, canonical transcript reads, and idempotent completion. Render the opening turn exactly as `POST /v1/participant-session/start` returns it. Retry duplicate client IDs without updating stored turns.

Former UI Phase 3 work for session creation, persistence, and completion maps to Durable record.

### Voice control

Connect WebRTC through `POST /v1/participant-session/realtime/calls`. Post observations instead of canonical AI turns. Display interruption without overwriting canonical generated, delivered, and display text. Keep second-device sessions read-only until writer lease transfer.

Former UI Phase 3 Realtime work maps to Voice control.

### Approved tracing

The UI does not write LangSmith traces. Staff-facing review of derived traces comes after the backend exports from committed records. The UI only sends allowlisted observations and never sends raw audio.

Former UI Phase 3 LangSmith mention maps to Approved tracing.

### Research export

Researcher tools for transcript export stay on protected staff routes. The participant UI is not an export client.

## Data and research controls

Each saved session should include a server generated `session_id` that stays internal, a `study_id`, study wave, configuration snapshot ID, assigned issue, assigned AI position, prompt version, avatar version, voice version, timestamps, connection events, transcript turns, and completion status. Prompt, avatar, and voice versions are part of the immutable snapshot for the session.

The system should define what happens when:

* A participant refreshes the page.
* A connection drops during an AI response.
* The microphone permission is revoked.
* Transcription fails but audio continues.
* The participant leaves early.
* The participant opens the same session on two devices.
* The AI produces unsafe or irrelevant content.

Refresh reloads the public session view and canonical transcript under the same capability. A dropped connection during an AI response should reconnect without creating a second canonical conversation. Revoked microphone permission should offer text mode. Early leave still goes through complete. A second device remains read-only until explicit writer lease transfer.

## Decisions needed before backend work

The study team should decide:

1. Whether voice is required, preferred, or optional.
2. Whether raw participant or AI audio is recorded. The default is no raw audio retention.
3. Whether participants can interrupt the AI, and which interrupted text field is exported.
4. Whether participants see exact remaining time.
5. Whether participants can propose a spoken transcript correction as a revision, not an overwrite.
6. Whether a given snapshot uses `ai_speaks_first`.
7. How the study assigns topics, positions, avatars, and voices into the snapshot.
8. Whether a participant can resume an interrupted session under the same writer lease.
9. What safety rules end or pause a session.
10. What the completion page should ask the participant to do next.
11. How long the completed projection remains readable before `410`.
12. Whether any required consent wording must name OpenAI as a voice subprocessor.

## Initial scope

The first UI build under Sample contracts should include the introduction, AI participant preview, audio check, discussion screen, completion screen, mobile layout, and error states. It should use one sample issue, one sample avatar, and a scripted transcript.

The first build should exclude staff authentication, researcher administration, database storage, OpenAI calls, LangSmith, raw audio recording, generated video, lip synchronization, and scoring. Excluding those systems keeps the first review focused on whether participants understand and can use the experience.
