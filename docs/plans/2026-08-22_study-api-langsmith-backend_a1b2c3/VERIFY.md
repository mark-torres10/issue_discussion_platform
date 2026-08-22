# Verification: Study API + UI local E2E (2026-08-22 re-run)

## Environment

| Service | Command | URL |
| --- | --- | --- |
| Backend | `cd backend && uv run fastapi dev --host 127.0.0.1 --port 8000` | http://127.0.0.1:8000 |
| UI | `cd ui && NEXT_PUBLIC_STUDY_API_ORIGIN=http://127.0.0.1:8000 npm run dev -- --port 3000` | http://localhost:3000 |

No product code was modified. Artifacts live under `images/after/`.

**Browser note:** Use `http://localhost:3000` (not `127.0.0.1`) so invite cookies set on redirect are sent on subsequent `/session/*` requests.

## Results summary

| Check | Result | Notes |
| --- | --- | --- |
| `GET /health` | **PASS** | `{"status":"ok","commit":null}` — `images/after/health-ok.png` |
| `GET /v1/participant-session` (no cookie) | **PASS** | **401** `capability_missing` (was 500 before fix) |
| `POST /v1/participant-access/exchange` | **PASS** | 200 with demo token; Jordan + campus-speech issue |
| `/invite/<demo-token>` → `/session` | **PASS** | Route handler sets cookies; intro renders — `invite-exchange.png`, `session-intro.png` |
| Session intro (API-backed) | **PASS** | "Before you begin", Jordan persona, issue title — `session-intro-api.png` |
| `/session/audio-check` | **PASS** | "Check your audio" — `audio-check.png` |
| Text mode → `/session/conversation` | **PASS** | Session start succeeds on fresh backend; issue title visible — `conversation-api.png` |
| `/session/unavailable` (no cookie) | **PASS** | HTTP **200** (not 500); unavailable copy — `session-unavailable.png` |
| Prototype home `/` | **PASS** | `home.png` |
| API proof render | **PASS** | `conversation-api-detail.png`, `api-proof.json` |
| Screen recording | **PASS** | `walkthrough.mp4` (invite → intro → audio-check → conversation) |

## Fixes verified

1. **Invite cookie handling:** `/invite/[token]` is now a Route Handler (`route.ts`) that calls the exchange API and sets `participant_capability` + `participant_csrf` on the redirect response. Full UI path works without manual cookie injection.
2. **401 on missing capability:** Backend returns 401 `capability_missing` instead of 500; UI `fetchParticipantSession` treats 401 as null session; `/session/unavailable` renders 200.
3. **Conversation start:** Works when backend is fresh (in-memory writer slot). Stale backends after repeated exchanges can return `writer_conflict` on `POST /start` — restart backend before re-testing.

## Artifacts

| File | Description |
| --- | --- |
| `images/after/health-ok.png` | Backend health JSON |
| `images/after/home.png` | Prototype home |
| `images/after/invite-exchange.png` | Post-invite session intro |
| `images/after/session-intro.png` | Introduction screen |
| `images/after/session-intro-api.png` | Same (API-backed) |
| `images/after/audio-check.png` | Audio check with voice/text toggle |
| `images/after/conversation-api.png` | Conversation with campus-speech issue |
| `images/after/conversation-api-detail.png` | API exchange + session JSON proof |
| `images/after/session-unavailable.png` | Unavailable page without cookies (200) |
| `images/after/walkthrough.mp4` | Headed browser walkthrough recording |
| `images/after/e2e-results.json` | Machine-readable pass/fail list |
| `images/after/SMOKE_NOTES.md` | Curl + UI flow notes |
| `images/after/curl-transcript.txt` | One-line transcript |
| `images/after/api-proof.json` | Raw exchange response metadata |

## Verdict

**PASS** — Full local E2E path works: `/invite/<token>` → `/session` → audio-check → conversation. Unauthorized session is 401 (not 500). Unavailable page renders without error when no cookies are present.
