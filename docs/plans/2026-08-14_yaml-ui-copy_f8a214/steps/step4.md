# Step 4: Document where to edit wording, then run checks

Tell people which YAML files to edit. Prove lint, tests, and the production build still pass. Confirm the before and after screenshots from step 3.

## Caller

A researcher or agent who needs to change participant wording should open `docs/runbooks/setup/HOW_TO_SETUP_APP.md` or `docs/runbooks/HOW_TO_RUN_APP.md` and find the content folder without opening a React file.

## Out of scope

- Rewording study content
- Backend, Railway, or OpenAI Realtime work
- New user journeys

## Files to inspect

- `docs/runbooks/setup/HOW_TO_SETUP_APP.md`
- `docs/runbooks/HOW_TO_RUN_APP.md`
- `AGENTS.md`
- `ui/README.md`
- `README.md`
- `docs/plans/2026-08-14_yaml-ui-copy_f8a214/images/before/`
- `docs/plans/2026-08-14_yaml-ui-copy_f8a214/images/after/`

## Files allowed to change

- `docs/runbooks/setup/HOW_TO_SETUP_APP.md`
- `docs/runbooks/HOW_TO_RUN_APP.md`
- `AGENTS.md`
- `ui/README.md`
- `README.md` only if the UI quick start still implies that copy lives in code

## Files forbidden to change

- `ui/src/**`
- `ui/content/**`
- `strategy_planning/backend_proposal_2026_08_06.md`
- `docs/runbooks/testing/USER_JOURNEYS_TO_TEST.md`

## Docs to add

In `docs/runbooks/setup/HOW_TO_SETUP_APP.md`, after the package install steps, add a short section titled "Where to edit participant wording":

- Shared screen text is `ui/content/ui-copy.yaml`.
- Sample issue, AI persona, opening line, and scripted replies are `ui/content/sessions/demo-campus-speech-001.yaml`.
- After an edit, refresh the running Next.js app. If a required key is missing, the app throws and names the key.

In `docs/runbooks/HOW_TO_RUN_APP.md`, add one paragraph under "Start the participant UI" that points to that setup section.

In `AGENTS.md`, add one sentence that participant wording is edited in `ui/content/`, not in React files.

If `ui/README.md` still tells people how to run the prototype, add the same pointer there.

Do not paste the YAML schema into the runbook.

## Screenshot check

These six files must exist:

- `docs/plans/2026-08-14_yaml-ui-copy_f8a214/images/before/01-home.png`
- `docs/plans/2026-08-14_yaml-ui-copy_f8a214/images/before/02-introduction.png`
- `docs/plans/2026-08-14_yaml-ui-copy_f8a214/images/before/03-unavailable-expired.png`
- `docs/plans/2026-08-14_yaml-ui-copy_f8a214/images/after/01-home.png`
- `docs/plans/2026-08-14_yaml-ui-copy_f8a214/images/after/02-introduction.png`
- `docs/plans/2026-08-14_yaml-ui-copy_f8a214/images/after/03-unavailable-expired.png`

Home still shows "Issue Discussion Study" and "Open sample session". Introduction still shows Jordan and the campus-speech issue title. The expired unavailable screen still shows "This session has expired". Layout must match the before images.

## Commands

From `ui/`:

```bash
npm run lint
npm test
npm run build
```

`npm run lint` exits 0. `npm test` exits 0. `npm run build` exits 0 and does not warn that `content/ui-copy.yaml` is missing from the packaged files.

After `npm run dev`, open:

- http://localhost:3000/
- http://localhost:3000/session/demo-campus-speech-001
- http://localhost:3000/session/expired-demo/unavailable
- http://localhost:3000/session/not-a-real-id

## Pass

- The runbooks name the two YAML paths
- Lint, test, and build commands exit 0
- The six screenshots exist
- `ui/src/lib/api/study-backend.ts` has no in-memory `SAMPLE_SESSION` object

## Fail

- The docs tell people to edit TSX for participant sentences
- The build succeeds while `ui/content/` is empty
- The after screenshots show a redesign
- New npm packages such as `i18next` or `next-intl` were added
