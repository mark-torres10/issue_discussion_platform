# How to run the app

This runbook starts the Issue Discussion Study participant prototype as it exists today: a Next.js app in `ui/` with in-memory sample sessions. There is no FastAPI, Railway, OpenAI Realtime, or LangSmith process to start.

## What you need

- **Node.js 20.x**: required by `ui/package.json`
- **npm**: used for install and scripts
- A browser with microphone permission if you want to exercise voice mode

Python tooling in the repo (`uv`, `pytest`, `ruff`) is for lint and tests. `main.py` prints a hello message. It is not the study app.

## Start the participant UI

Install dependencies once, then start the Next.js dev server:

```bash
cd ui
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Use **Open sample session** to enter the happy path.

Sample session id: `demo-campus-speech-001`.

The prototype stores audio-check preferences and conversation snapshots in the browser (`sessionStorage`). Refreshing the same tab keeps that local state. A new browser profile starts clean.

## Participant routes

| Path | Screen |
| --- | --- |
| `/` | Prototype home |
| `/session/[sessionId]` | Introduction and AI preview |
| `/session/[sessionId]/audio-check` | Microphone and speaker check, or text mode |
| `/session/[sessionId]/conversation` | Mocked text or voice discussion |
| `/session/[sessionId]/complete` | Save confirmation |
| `/session/[sessionId]/unavailable` | Expired, completed, paused, or invalid |

Known demo ids besides the sample session:

- `expired-demo`
- `completed-demo`
- `paused-demo`

Unknown ids render **Session not found**. Non-active known ids redirect from introduction, audio check, and conversation to `/unavailable`.

Home-page shortcuts:

- [expired](http://localhost:3000/session/expired-demo/unavailable)
- [completed](http://localhost:3000/session/completed-demo/unavailable)
- [paused](http://localhost:3000/session/paused-demo/unavailable)

## Stop the app

Stop the dev server with `Ctrl+C` in the terminal that is running `npm run dev`.

## Checks that do not start the UI

From `ui/`:

```bash
npm run lint
npm test
npm run build
```

`npm run build` compiles a production bundle. Serve it with `npm start` after a successful build if you need that mode instead of `npm run dev`.

## What is still mocked

Conversation replies, save retries, and Realtime voice are local scripts and timers. The UI does not call a study backend. Treat anything you type as prototype-only; it is not a research record.

For journeys to walk through by hand, see [User journeys to test](testing/USER_JOURNEYS_TO_TEST.md).
