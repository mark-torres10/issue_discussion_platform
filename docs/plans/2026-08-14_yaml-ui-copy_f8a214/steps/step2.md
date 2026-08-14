# Step 2: Load the sample session from YAML

`getStudySession` should read the session YAML through `loadSessionContent`. Demo ids and the `StudySession` shape stay the same. The complete page must stop calling session lookup from a client file, because the lookup will read files on the server.

## Caller

`getStudySession(sessionId)` in `ui/src/lib/api/study-backend.ts` is used by:

- `ui/src/app/session/[sessionId]/page.tsx`
- `ui/src/app/session/[sessionId]/audio-check/page.tsx`
- `ui/src/app/session/[sessionId]/conversation/page.tsx`
- `ui/src/app/session/[sessionId]/unavailable/page.tsx`
- `ui/src/app/session/[sessionId]/complete/complete-client.tsx` (must stop)

Home and layout import `SAMPLE_SESSION_ID` only. Those files are server components, so they can keep importing it from `study-backend.ts`.

## Out of scope

- Replacing shared screen strings (step 3)
- Changing routes, demo ids, or `isSessionAvailable`
- Adding `ui/src/lib/api/study-backend.constants.ts`

## Files to inspect

- `ui/src/lib/api/study-backend.ts`
- `ui/src/lib/api/study-backend.test.ts`
- `ui/src/lib/content/loader.ts`
- `ui/src/app/session/[sessionId]/complete/page.tsx`
- `ui/src/app/session/[sessionId]/complete/complete-client.tsx`

## Files allowed to change

- `ui/src/lib/api/study-backend.ts`
- `ui/src/lib/api/study-backend.test.ts`
- `ui/src/app/session/[sessionId]/complete/page.tsx`
- `ui/src/app/session/[sessionId]/complete/complete-client.tsx`

## Files forbidden to change

- `ui/content/**`
- `ui/src/app/page.tsx`
- `ui/src/app/layout.tsx`
- `ui/src/components/**`
- `ui/src/lib/realtime/**`
- `ui/src/app/not-found.tsx`
- `docs/runbooks/**`

## What to change

Delete the `SAMPLE_SESSION` object literal from `ui/src/lib/api/study-backend.ts`. Keep `SAMPLE_SESSION_ID` as the string `demo-campus-speech-001`.

`getStudySession` should:

1. Return `loadSessionContent()` when the id is `demo-campus-speech-001`.
2. For `expired-demo`, `completed-demo`, and `paused-demo`, return the same session object with `sessionId` and `status` overwritten, which is what `SESSION_REGISTRY` does today.
3. Return `null` for any other id.

Keep `isSessionAvailable` as `session.status === "active"`.

Add `import "server-only"` to `ui/src/lib/api/study-backend.ts`.

`complete-client.tsx` is a Client Component, so it cannot import that module after `server-only` is added. A Client Component is a React file marked `"use client"`, which means it runs in the browser.

Move the session load to `ui/src/app/session/[sessionId]/complete/page.tsx`:

1. Make that page an async Server Component. Read `params`, call `getStudySession(sessionId)`, and call `notFound()` when the result is null.
2. Pass `session` into `CompletePageClient`. Remove the `getStudySession` import from the client file. Keep the `sessionStorage` save retry on the client.
3. Keep the `Suspense` boundary around the client because of `useSearchParams`. Call `notFound()` outside that boundary.

Unknown complete URLs then use the existing not-found screen instead of the in-page "This session link is not available." line. File reading stays on the server, so the complete page cannot look up the session in the browser.

## Tests

Keep the cases in `ui/src/lib/api/study-backend.test.ts`. Add one case that `expired-demo` shares the sample issue title. Loader tests from step 1 must still pass.

## Implementation order

1. Point `getStudySession` at the loader and keep the three status overlays in that same file.
2. Add `server-only`.
3. Move the complete-page session load to the server.
4. Run the build and confirm it does not put `fs` in a client chunk.

## Pass

```bash
cd ui
npm test -- src/lib/api/study-backend.test.ts src/lib/content/loader.test.ts
npx tsc --noEmit
npm run build
```

Tests pass. `tsc` exits 0. The build succeeds. Opening `demo-campus-speech-001` still shows Jordan and the campus-speech issue. Opening `expired-demo` still goes to unavailable.

## Fail

- `complete-client.tsx` still imports `ui/src/lib/api/study-backend.ts`
- The build reports that `server-only` was imported from a Client Component
- Demo ids change
- Shared screen strings change in this step
- A new constants file or session index YAML is added
