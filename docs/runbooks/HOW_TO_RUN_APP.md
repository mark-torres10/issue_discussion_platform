# How to run the app

Install tools and packages first, using [How to set up the app](setup/HOW_TO_SETUP_APP.md).

The runnable app is the Next.js participant prototype in `ui/`. Next.js is the web framework used in `ui/`. Python at the repo root is for lint and tests. If you run `main.py`, you see a hello message. `main.py` is not the study app.

A browser with microphone permission is useful if you want to try voice mode.

## Start the participant UI

From `ui/`, run `npm run dev` to start the Next.js development server.

```bash
cd ui
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Use **Open sample session** to open the sample study session.

To change participant wording without editing React files, use the YAML paths in [Where to edit participant wording](setup/HOW_TO_SETUP_APP.md#where-to-edit-participant-wording).

Sample session id: `demo-campus-speech-001`.

Audio-check preferences and conversation snapshots stay in the browser in `sessionStorage`. `sessionStorage` is a browser store that lasts until you close the tab. Refreshing the same tab keeps the stored preferences and snapshots. A new browser profile has no stored preferences or snapshots.

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

If you open an unknown id, you see **Session not found**. If you open the introduction, audio check, or conversation URL for a known id that is not active, you see `/unavailable`.

Home-page shortcuts:

- [expired](http://localhost:3000/session/expired-demo/unavailable)
- [completed](http://localhost:3000/session/completed-demo/unavailable)
- [paused](http://localhost:3000/session/paused-demo/unavailable)

## Stop the app

Stop the development server with `Ctrl+C` in the terminal that is running `npm run dev`.

## Checks that do not start the UI

From `ui/`, run these commands.

```bash
npm run lint
npm test
npm run build
```

Run `npm run build` to compile a production bundle. After a successful build, run `npm start` if you want that mode instead of `npm run dev`.

## What is still mocked

Conversation replies, save retries, and voice behavior are local scripts and timers. Realtime is OpenAI's live voice and text API. There is no Realtime connection and no study backend. Treat anything you type as prototype-only, because the typed text is not a research record.

For journeys to walk through by hand, see [User journeys to test](testing/USER_JOURNEYS_TO_TEST.md).
