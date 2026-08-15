# Participant UI prototype

Next.js App Router prototype for the Issue Discussion Study participant journey (Phase 1 static UI + Phase 2 browser behavior). Backend, OpenAI Realtime, and LangSmith are intentionally mocked.

## Run locally

```bash
cd ui
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000), then use **Open sample session**.

Sample session id: `demo-campus-speech-001`

Participant wording lives in `ui/content/` (`ui-copy.yaml` and `sessions/demo-campus-speech-001.yaml`). See [Where to edit participant wording](../docs/runbooks/setup/HOW_TO_SETUP_APP.md#where-to-edit-participant-wording).

## Verify

```bash
cd ui
npm run lint
npm test
npm run build
```

## Routes

- `/` — prototype entry
- `/session/[sessionId]` — introduction + AI preview
- `/session/[sessionId]/audio-check` — mic/speaker check
- `/session/[sessionId]/conversation` — text/voice discussion (mocked)
- `/session/[sessionId]/complete` — save confirmation
- `/session/[sessionId]/unavailable` — expired/completed/paused

## Out of scope (Phase 3)

Railway auth/session persistence, OpenAI Realtime WebRTC, LangSmith tracing, researcher admin.
