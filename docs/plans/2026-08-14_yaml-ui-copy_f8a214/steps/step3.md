# Step 3: Load shared screen text from YAML

Replace hardcoded participant sentences with strings from `ui/content/ui-copy.yaml`. Keep the same layout, components, and routes. Capture screenshots before you edit TSX.

## Caller

The root layout calls `loadUiCopy()` and puts the result in a React context. Client screens read that context. Microphone helpers and remaining-time formatting keep their current string returns. They do not import the loader.

## Screenshots, required before TSX edits

Start the app with `cd ui && npm run dev`. Save PNGs to `docs/plans/2026-08-14_yaml-ui-copy_f8a214/images/before/`:

| File | URL |
| --- | --- |
| `01-home.png` | http://localhost:3000/ |
| `02-introduction.png` | http://localhost:3000/session/demo-campus-speech-001 |
| `03-unavailable-expired.png` | http://localhost:3000/session/expired-demo/unavailable |

After the screens read YAML, save the same names under `docs/plans/2026-08-14_yaml-ui-copy_f8a214/images/after/`. The after images must match the before images in layout and wording. If a string differs, fix the YAML. Do not crop or restyle the screenshot to hide the difference.

## Out of scope

- New screens or a visual redesign
- A translation library
- Changing mock timers or save retry delay
- Moving microphone errors or remaining-time phrases into YAML
- Changing `selectScriptedAiReply`
- A `format-copy.ts` module

## Files to inspect

- `ui/content/ui-copy.yaml`
- `ui/src/app/layout.tsx`
- `ui/src/app/page.tsx`
- `ui/src/app/not-found.tsx`
- `ui/src/app/session/[sessionId]/unavailable/page.tsx`
- `ui/src/app/session/[sessionId]/complete/page.tsx`
- `ui/src/app/session/[sessionId]/complete/complete-client.tsx`
- `ui/src/components/session/participant-introduction.tsx`
- `ui/src/components/session/audio-check.tsx`
- `ui/src/components/conversation/conversation-shell.tsx`
- `ui/src/components/conversation/session-header.tsx`
- `ui/src/components/conversation/voice-controls.tsx`
- `ui/src/components/conversation/text-composer.tsx`
- `ui/src/components/conversation/avatar-presence.tsx`

## Files allowed to change

The inspect list above, plus:

- `ui/src/lib/content/content-provider.tsx` (create)
- `ui/content/ui-copy.yaml` only if a required key was missed in step 1, and only by adding today's TSX string

`ui/src/app/session/[sessionId]/page.tsx`, `audio-check/page.tsx`, and `conversation/page.tsx` should not need edits unless a child needs a new prop. Prefer the context so those pages stay as they are.

## Files forbidden to change

- `ui/src/components/ui/**`
- `ui/src/lib/api/study-backend.ts`
- `ui/src/lib/realtime/microphone.ts`
- `ui/src/lib/realtime/state.ts`
- `docs/runbooks/**`
- `strategy_planning/**`
- Python files

## How screens get the strings

`ui/src/app/layout.tsx` calls `loadUiCopy()`, sets document metadata from `copy.metadata`, and wraps `{children}` with `UiCopyProvider`. Skip-link and header strings come from the shared YAML. The sample session href still uses `SAMPLE_SESSION_ID`.

`useUiCopy()` throws if it is called outside the provider.

Do not load YAML inside Client Components.

For the introduction duration sentence, replace `{durationMinutes}` with `String(session.rules.durationMinutes)` at that call site.

Delete `STATUS_COPY` from `unavailable/page.tsx` and read `copy.unavailable[status]` instead.

Do not add extra boolean props to pick copy. The screen already knows the state (`saveFailed`, voice vs text), so it should pick the matching YAML field.

## Implementation order

1. Capture the three before screenshots. Do not edit TSX until those files exist.
2. Add the provider.
3. Wire layout, then home, not-found, unavailable, introduction, audio-check, complete, and the conversation screens.
4. Capture the after screenshots.
5. Search `ui/src` for leftover literals that now live in YAML, such as `Check your audio`, `Session complete`, and `This session has expired`. The step fails if those literals remain in TSX outside tests.

## Pass

```bash
cd ui
npm test
npx tsc --noEmit
```

All tests pass. `tsc` exits 0. The after screenshots exist and match the before screenshots.

## Fail

- A Client Component imports `ui/src/lib/content/loader.ts`
- New visual styling
- Wording rewritten while it is moved
- Before screenshots missing
- `microphone.ts` or `state.ts` signatures change
- A formatter module is added
