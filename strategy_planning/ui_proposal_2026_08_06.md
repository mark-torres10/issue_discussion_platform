# UI proposal

## Recommendation

The first version should be a focused conversation experience with a short setup flow, one discussion screen, and one completion screen. The interface should tell the participant what will happen, help them test their microphone, keep the conversation easy to follow, and make it clear when the session is recording or saving data.

The product should identify the conversation partner as an AI participant. The AI can have a student style name, avatar, voice, and point of view, but the interface should not imply that a real student is present. Any study design that uses deception should be reviewed and approved through the research ethics process before it affects the interface.

Voice should be a mode within the same conversation, rather than a separate product. Participants should be able to use text if their microphone fails, if their environment is noisy, or if speaking is uncomfortable.

## Design principles

### Keep the participant focused

The main screen should contain only the issue, the AI participant, the conversation, and the controls needed to continue or end the session. It should not include a general navigation menu, settings area, model selector, or unrelated dashboard.

### Explain what the system is doing

The participant should always be able to tell whether the system is listening, processing, speaking, muted, reconnecting, or finished. Voice interfaces feel broken when the state is unclear, even when the underlying service is working.

### Keep text and voice synchronized

Each spoken turn should appear in the transcript after it is transcribed. The transcript gives participants a visual record, supports accessibility, and provides a text fallback when audio playback fails.

### Use a calm visual style

The interface should use a neutral background, readable text, generous spacing, and one accent color. The avatar should add social presence without making the page feel like a game. Motion should be limited to useful state changes, such as a subtle speaking indicator.

### Protect participant control

The participant should explicitly start microphone access and should always have visible controls to mute, switch to text, or end the conversation. The site should never start recording when the page loads.

## Participant journey

### 1. Open the assigned session

The participant follows a unique study link. The application validates that the link is active and loads the assigned issue, AI persona, study wave, and session rules.

For the UI prototype, the application can use fixed sample data instead of a real session link.

### 2. Read the introduction

The introduction page explains:

* The participant will have a conversation with an AI participant.
* The AI will argue a specified position on a contested issue.
* The discussion will last about 5 to 10 minutes.
* The study will save a transcript and the measures approved by the study protocol.
* The participant can end the conversation at any time.
* The participant can use voice or text.

The page should use a short plain language summary. Formal consent should remain a separate step if the study protocol requires it.

### 3. Meet the AI participant

The participant sees the AI avatar, display name, short introduction, and assigned position. The display name should be clearly labeled as an AI participant.

The introduction should set expectations without revealing the full system prompt. For example, it can say that the AI will disagree respectfully, ask questions, and explain its position.

### 4. Check audio

The participant selects voice or text. If they select voice, the browser asks for microphone permission only after they press a clear button.

The audio check should:

* Confirm that a microphone is available.
* Show an input level while the participant speaks.
* Play a short test sound through the selected output.
* Let the participant retry permission or continue with text.
* Explain that headphones can reduce echo.

The application should not save audio from the audio check.

### 5. Start the discussion

The discussion screen opens with a short first message from the AI. The participant can respond by speaking or typing.

The participant should not need to learn special controls. Voice mode should support natural turn taking, and text mode should use a familiar message box with a send button.

### 6. Continue the discussion

The page shows the current conversation state near the avatar:

* "Listening" when the microphone is accepting speech.
* "Thinking" after the participant finishes a turn.
* "Speaking" while the AI audio is playing.
* "Muted" when the participant has disabled the microphone.
* "Reconnecting" when the voice connection has failed.

The transcript should distinguish participant turns from AI turns. New text should appear without moving the controls off screen. The participant should be able to interrupt the AI while it is speaking if the research protocol allows interruption.

The header can show elapsed time and a small statement such as "About 3 minutes remaining." A large countdown may add pressure and change how participants speak, so the researchers should decide whether exact remaining time is part of the study protocol.

### 7. End the discussion

The participant can press "End conversation" at any time. The application should ask for confirmation while the session is active, because an accidental end could invalidate a study session.

The application can also end the session when the assigned time expires. It should first give a neutral notice that the conversation is almost complete, then let the AI give a brief closing response.

### 8. Confirm completion

The completion page confirms that the session was saved and gives the participant the next study instruction. It should not score, praise, or criticize how the participant handled the disagreement, because feedback could affect later study measures.

If saving fails, the page should keep the local session state and tell the participant not to close the page while the application retries.

## Main discussion screen

### Desktop layout

The desktop page should use a narrow centered application frame with three regions:

1. A compact header with the issue title, session time, connection status, and an end button.
2. A conversation area with the AI avatar and state at the top, followed by the scrollable transcript.
3. A fixed control area with the microphone control, mute button, text input, captions control, and voice or text switch.

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
  Prototype entry or study link instructions

/session/[sessionId]
  Session introduction and AI participant preview

/session/[sessionId]/audio-check
  Microphone and speaker check

/session/[sessionId]/conversation
  Text and voice discussion

/session/[sessionId]/complete
  Save confirmation and next instruction

/session/[sessionId]/unavailable
  Invalid, expired, completed, or paused session
```

An internal researcher interface can come later. It should be a separate protected route group, because participant pages should not expose study controls or transcript search.

## Recommended frontend setup

Use the current stable Next.js App Router with TypeScript and deploy it to Vercel. Use Tailwind CSS for layout and tokens, and use selected shadcn/ui components for accessible controls such as dialogs, buttons, tooltips, and text areas.

Use Server Components for pages that load session configuration. Keep the interactive conversation surface in a Client Component because it needs microphone access, WebRTC, audio playback, timers, and local connection state.

A practical source structure would be:

```text
src/
  app/
    layout.tsx
    page.tsx
    session/
      [sessionId]/
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

## Voice architecture

The current OpenAI product for low latency voice conversation is the Realtime API. The project should select the current supported realtime model during implementation instead of treating "GPT live" as a fixed model name.

For the production design, the browser should use WebRTC for microphone input and AI audio output. WebRTC is designed for low latency media and handles browser audio more reliably than sending audio chunks through ordinary HTTP requests.

The connection flow should be:

1. The participant starts voice mode.
2. The Vercel application asks the Railway backend to start or resume the study session.
3. Railway validates the study link and creates a short lived OpenAI client secret.
4. The browser uses the short lived secret to establish a WebRTC connection with OpenAI.
5. The browser sends and receives structured conversation events through the WebRTC data channel.
6. The application sends final transcript events and session state to Railway.
7. Railway stores the authoritative study record and sends approved trace data to LangSmith.

The standard OpenAI API key must stay on Railway. It must never be included in the browser bundle or returned to the participant. The short lived client secret should be scoped to one configured realtime session.

Railway should own the system instructions, assigned issue, AI position, voice choice, time limits, and allowed tools. The browser should receive only the configuration needed to render the session. A participant must not be able to change the AI position or system instructions through browser requests.

The system should not assume that LangSmith stores raw voice recordings. LangSmith can trace model calls, events, and transcript data, but raw audio retention should be treated as a separate research and storage decision. If the study needs audio recordings, the consent language, retention period, access rules, encryption, and deletion process should be defined before recording is added.

## UI prototype phases

### Phase 1. Static UI

Build all participant pages with sample session data. The conversation page should use scripted participant and AI messages. Voice controls should change visible state but should not request microphone access or call an API.

The first review should answer:

* Does the study flow make sense without explanation?
* Does the participant understand that the partner is an AI?
* Is the assigned position clear?
* Are the voice states easy to understand?
* Does the design work on a phone and a laptop?

### Phase 2. Browser behavior

Add microphone permission, input level display, audio device errors, local timers, transcript scrolling, responsive behavior, and a simulated streaming response. Keep the backend mocked.

The phase should include tests for denied microphone permission, lost network connection, refresh during a session, and switching from voice to text.

### Phase 3. Realtime and study backend

Connect the Vercel UI to Railway and OpenAI Realtime. Add authenticated session creation, transcript persistence, reconnect behavior, idempotent completion, and LangSmith tracing.

The study team should run pilot sessions across Safari, Chrome, mobile Safari, and common campus network conditions before using the system with participants.

## Data and research controls

Each saved session should include a server generated session ID, study wave, assigned issue, assigned AI position, prompt version, avatar version, voice version, timestamps, connection events, transcript turns, and completion status.

Prompt, avatar, and voice versions should be fixed and recorded for each study wave. Changing any of them can change participant behavior, so the researchers need enough version data to identify which participants received each configuration.

Partial transcript text should be treated as temporary UI state. Railway should save final turns with stable turn IDs, speaker labels, timestamps, and ordering. Repeated save requests should not create duplicate turns.

The system should define what happens when:

* A participant refreshes the page.
* A connection drops during an AI response.
* The microphone permission is revoked.
* Transcription fails but audio continues.
* The participant leaves early.
* The participant opens the same session on two devices.
* The AI produces unsafe or irrelevant content.

## Decisions needed before backend work

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

## Initial scope

The first UI build should include the introduction, AI participant preview, audio check, discussion screen, completion screen, mobile layout, and error states. It should use one sample issue, one sample avatar, and a scripted transcript.

The first build should exclude authentication, researcher administration, database storage, OpenAI calls, LangSmith, raw audio recording, generated video, lip synchronization, and scoring. Excluding those systems keeps the first review focused on whether participants understand and can use the experience.
