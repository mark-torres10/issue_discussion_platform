# Step 1: Add two YAML files and a loader

Add the wording files and a loader that reads them. Do not change screens in this step. Session lookup in `ui/src/lib/api/study-backend.ts` still returns the in-memory sample object.

## Caller

Later steps call `loadUiCopy()` from the root layout and `loadSessionContent()` from `getStudySession`. Step 1 only adds the YAML files, the loader, and tests.

## File tree

```text
ui/content/ui-copy.yaml
ui/content/sessions/demo-campus-speech-001.yaml
ui/src/lib/content/loader.ts
ui/src/lib/content/loader.test.ts
ui/vitest.setup.ts
```

Put TypeScript types for the YAML shapes in `ui/src/lib/content/loader.ts`. Do not add a separate types file.

## Out of scope

- Changing React screens or `getStudySession`
- Adding a session index YAML
- Adding a translation library
- Changing `ui/next.config.ts` unless `npm run build` omits `ui/content/` from the packaged files

## Files to inspect

- `ui/src/lib/api/study-backend.ts` for the sample session fields
- `ui/src/lib/types/session.ts` for the `StudySession` shape
- `ui/src/lib/api/study-backend.test.ts` for ids that must keep working
- `ui/package.json` for the existing `yaml` and `server-only` packages
- `ui/vitest.config.ts` (tests run with the working directory `ui/`)
- The screen files listed in step 3, so `ui-copy.yaml` contains today's strings and step 3 does not invent keys

## Files allowed to change

- `ui/content/ui-copy.yaml` (create)
- `ui/content/sessions/demo-campus-speech-001.yaml` (create)
- `ui/src/lib/content/loader.ts` (create)
- `ui/src/lib/content/loader.test.ts` (create)
- `ui/vitest.setup.ts` (only to stub `server-only` if tests fail on import)
- `ui/next.config.ts` (only if the production build drops `ui/content/`)

## Files forbidden to change

- `ui/src/lib/api/study-backend.ts`
- `ui/src/app/**/*.tsx`
- `ui/src/components/**/*.tsx`
- `ui/src/lib/realtime/**`
- `docs/runbooks/**`
- `strategy_planning/**`
- Python files

## How the loader should work

Read YAML with `readFileSync` and `parse` from the `yaml` package. Use these exact paths so Next.js can see the files:

- `path.join(process.cwd(), "content/ui-copy.yaml")`
- `path.join(process.cwd(), "content/sessions/demo-campus-speech-001.yaml")`

Put `import "server-only"` at the top of `ui/src/lib/content/loader.ts`. `server-only` is a small package that throws if a browser bundle imports the file, which is what we want, because the loader reads the disk.

Throw if the file is missing, the YAML is invalid, or a required key is missing. The error must name the file and the missing key. Do not substitute a default participant sentence.

Export two functions:

- `loadUiCopy()` returns the shared screen object
- `loadSessionContent()` returns a `StudySession` for `demo-campus-speech-001`, with `sessionId` and `status: "active"` taken from the session YAML

`SAMPLE_SESSION_ID` stays the string `demo-campus-speech-001` in `ui/src/lib/api/study-backend.ts` until step 2.

### Session YAML

Copy the current `SAMPLE_SESSION` object from `ui/src/lib/api/study-backend.ts` into `ui/content/sessions/demo-campus-speech-001.yaml`, including `sessionId` and `status`. The wording must match that file exactly.

Do not add `emptyAiReply`. The unused empty-list fallback in `selectScriptedAiReply` stays in code.

### Shared screen YAML

`ui/content/ui-copy.yaml` holds the participant-facing strings from the screens, grouped by screen (`metadata`, `home`, `introduction`, `audioCheck`, `conversation`, `complete`, `unavailable`, `notFound`). Copy the current strings exactly.

Leave microphone error sentences and remaining-time sentences in `ui/src/lib/realtime/microphone.ts` and `ui/src/lib/realtime/state.ts`. Researchers will edit issue text, introductions, and buttons. They do not need those short system phrases in YAML for this pass.

Where a sentence includes the discussion length, keep `{durationMinutes}` in the YAML string. Replace that token at the two call sites in step 3 with an ordinary string replace. Do not add a formatter module.

## Tests

File: `ui/src/lib/content/loader.test.ts`

1. `loadUiCopy()` reads the real file, and `home.heading` is `Issue Discussion Study`.
2. `loadSessionContent()` returns status `active`, the current issue title, and four scripted replies.
3. A session object missing `issue.title` throws, and the message includes `issue.title`.

Do not change `ui/src/lib/api/study-backend.test.ts` in this step.

## Implementation order

1. Write the two YAML files with current wording.
2. Write `loader.test.ts` (it should fail because the loader does not exist yet).
3. Implement the loader.
4. Stub `server-only` in `ui/vitest.setup.ts` if the tests throw on import.
5. Make the loader tests pass.

## Pass

```bash
cd ui
npm test -- src/lib/content/loader.test.ts
npm test
```

The loader tests pass. The existing study-backend, state, and microphone tests still pass. Screens still show hardcoded copy.

## Fail

- The loader invents default sentences when a key is missing
- A third YAML file appears for demo ids
- `ui/src/lib/api/study-backend.ts` is edited
- Screenshots are taken in this step
