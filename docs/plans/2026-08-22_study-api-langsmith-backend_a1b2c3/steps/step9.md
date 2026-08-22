# Step 9: Participant UI wiring to the Study API

## Goal

Replace YAML-only session loading with real Study API calls. Add `/invite/[token]` to exchange the invitation and redirect to cookie-scoped `/session` routes without a public session id in the URL. Wire start, messages, transcript poll, complete, observations, and Realtime SDP setup through a server-side API client with credentials. Keep participant wording in `ui/content/`. Remove or redirect old `/session/[sessionId]/*` routes to the new shape.

## Files to inspect

- `/workspace/strategy_planning/ui_proposal_2026_08_06.md` (page structure, API mapping)
- `/workspace/ui/src/lib/api/study-backend.ts` (current mock)
- `/workspace/ui/src/app/session/[sessionId]/**` (current routes to migrate)
- `/workspace/ui/content/ui-copy.yaml`
- `/workspace/docs/runbooks/HOW_TO_RUN_APP.md`

## Files allowed to change (closed set)

- `/workspace/ui/src/app/invite/[token]/page.tsx`
- `/workspace/ui/src/app/session/page.tsx`
- `/workspace/ui/src/app/session/audio-check/page.tsx`
- `/workspace/ui/src/app/session/conversation/page.tsx`
- `/workspace/ui/src/app/session/complete/page.tsx`
- `/workspace/ui/src/app/session/unavailable/page.tsx`
- `/workspace/ui/src/app/session/[sessionId]/page.tsx` (redirect stub only)
- `/workspace/ui/src/app/session/[sessionId]/audio-check/page.tsx` (redirect stub only)
- `/workspace/ui/src/app/session/[sessionId]/conversation/page.tsx` (redirect stub only)
- `/workspace/ui/src/app/session/[sessionId]/complete/page.tsx` (redirect stub only)
- `/workspace/ui/src/app/session/[sessionId]/unavailable/page.tsx` (redirect stub only)
- `/workspace/ui/src/lib/api/study-backend.ts`
- `/workspace/ui/src/lib/api/study-backend-client.ts` (new browser-safe helpers if needed)
- `/workspace/ui/src/lib/api/csrf.ts`
- `/workspace/ui/src/lib/types/session.ts`
- `/workspace/ui/src/lib/types/transcript.ts`
- `/workspace/ui/src/lib/realtime/client.ts`
- `/workspace/ui/src/components/session/participant-introduction.tsx` (wire props only)
- `/workspace/ui/src/components/conversation/conversation-shell.tsx` (wire API calls only)
- `/workspace/ui/src/lib/api/study-backend.test.ts`
- `/workspace/ui/.env.example` (add `NEXT_PUBLIC_STUDY_API_ORIGIN` name only)
- `/workspace/docs/plans/2026-08-22_study-api-langsmith-backend_a1b2c3/images/before/` (screenshots before wiring)
- `/workspace/docs/plans/2026-08-22_study-api-langsmith-backend_a1b2c3/images/after/` (screenshots after wiring)

## Files forbidden to change

- `/workspace/backend/**`
- `/workspace/supabase/**`
- `/workspace/ui/content/*.yaml` (wording changes only if a new key is required. Prefer reusing existing keys)
- Staff `/login` routes (out of scope)

## Contracts / acceptance checks

UI routes after migration are as follows.

| Route | Behavior |
| --- | --- |
| `/invite/[token]` | Server action or route handler calls `POST /v1/participant-access/exchange`, stores CSRF token for client, redirects to `/session` |
| `/session` | `GET /v1/participant-session` for introduction |
| `/session/audio-check` | Local mic only. No audio upload to API |
| `/session/conversation` | `POST start`, then messages or Realtime per mode |
| `/session/complete` | `POST complete` with idempotency key retry UI |
| `/session/unavailable` | Shown on 404/410 from session read |

API client rules are as follows.

- All participant fetches use `credentials: 'include'`.
- State-changing requests send `X-CSRF-Token` header from exchange response.
- `NEXT_PUBLIC_STUDY_API_ORIGIN` points to the Railway Study API public origin in production and `http://127.0.0.1:8000` in local dev. This name matches `strategy_planning/CREDENTIALS_AND_SETUP.md`.
- UI does not call `POST /turns` or send AI/system speaker turns.
- Opening message rendered only from start response when `ai_speaks_first` true.
- For local development, document the `demo-campus-speech-001` invitation token in `.env.example` as the known sample token that matches backend sample data.

Required screenshots are listed below.

- Before wiring, capture the conversation page with YAML mock (`images/before/conversation-mock.png`).
- After wiring, capture the conversation page hitting local or staging API (`images/after/conversation-api.png`).

## Tests to add

| Test | What it locks |
| --- | --- |
| `study-backend.test.ts::TestExchangeRedirect::test_maps_api_session_view` | Type mapping |
| `study-backend.test.ts::TestCsrfHeader::test_includes_csrf_on_post` | CSRF header helper |
| `study-backend.test.ts::TestNoSessionIdInPath::test_session_routes_omit_id` | Route shape |

Run existing UI tests as follows.

| Test | What it locks |
| --- | --- |
| `realtime/state.test.ts` | Unchanged voice state machine |
| `content/loader.test.ts` | Copy still loads |

## Exact commands to run and expected output

```bash
cd /workspace/ui
npm install
npm test
```

You should see all Vitest or Jest tests pass with exit code 0.

```bash
cd /workspace/ui
npm run build
```

You should see the build complete without TypeScript errors.

Manual smoke with the backend running uses two terminals.

```bash
# Terminal 1
cd /workspace/backend && STORAGE_MODE=memory uv run fastapi dev app/main.py --port 8000

# Terminal 2
cd /workspace/ui && NEXT_PUBLIC_STUDY_API_ORIGIN=http://127.0.0.1:8000 npm run dev
```

Open `/invite/<sample-token>` in the browser. You should see a redirect to `/session`, and the introduction should load from the API.

## Out of scope for this step

- Staff login page
- LangSmith UI
- Full WebRTC audio in production (may keep simulated voice until Step 6 API is reachable from UI deploy)
- Railway or Vercel deploy (Step 10)

## Dependencies

- Integration check complete after Step 8 (full backend test suite passes, shared files merged, text and voice smoke paths verified).
- Step 2 minimum for local end-to-end (in-memory API).
- Step 5 for real text replies in integrated demo.
- Step 6 for live voice SDP (UI may ship text-first with voice gated behind env flag).

## Parallelization

This step runs after the integration check. Do not start Step 9 until Steps 1 through 8 and the integration check are complete.

## What must pass / fail before the step is complete

| Check | Must pass | Must fail |
| --- | --- | --- |
| `npm test` and `npm run build` | All tests pass and build succeeds | TypeScript or test failures |
| `/session/conversation` URL contains session id | No id in path | `/session/demo-001/conversation` as primary path |
| Browser network tab shows AI turn created client-side | Not applicable | POST with speaker ai from browser |
