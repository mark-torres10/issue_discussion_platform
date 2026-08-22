# Step 4: Swipe UI with work, education, and verification badges

Build the vanilla frontend card stack that loads the profile deck, displays rich profile fields and verification badges, and records like/pass swipes. No verification upload UI in this step.

**Prerequisite:** Steps 2–3 API complete. **Do not edit `main.py`** — same-origin browser testing completes in step 5.

## Caller

End user in browser at `http://127.0.0.1:8765/` (after step 5 mount). During step 4, validate JS structure and optional local static preview (see commands).

## File tree (create)

```text
/workspace/mock_app/frontend/
  index.html
  styles.css
  app.js
```

## Out of scope

- Verification upload form (step 5)
- `main.py` frontend mount (step 5)
- Frameworks (React, Vue, build tools)
- Changes to API routes or tests (unless fixing a bug blocking UI — avoid)

## Files to inspect

- `/workspace/mock_app/app/routers/profiles.py` (response shapes)
- `/workspace/mock_app/app/routers/swipes.py`
- `/workspace/mock_app/mock_data/profiles.json` (sample field values)
- `/workspace/docs/plans/2026-08-22_mock-app-tinder-clone_a1b2c3/steps/step2.md` (API contract)

## Files allowed to change

- `/workspace/mock_app/frontend/index.html` (create)
- `/workspace/mock_app/frontend/styles.css` (create)
- `/workspace/mock_app/frontend/app.js` (create)

## Files forbidden to change

- `/workspace/mock_app/app/main.py`
- `/workspace/mock_app/app/routers/**`
- `/workspace/mock_app/app/services/**`
- `/workspace/mock_app/app/models/**`
- `/workspace/mock_app/app/config.py`
- `/workspace/mock_app/mock_data/**` (read only)
- `/workspace/mock_app/tests/**`
- `/workspace/mock_app/README.md` (step 5)
- `/workspace/ui/**`, `/workspace/backend/**`

## UI contract

### `index.html`

- Single page `#app` root.
- Regions (use these element ids):
  - `#card-stack` — active profile card container
  - `#empty-state` — hidden when deck has cards; message “No more profiles”
  - `#profile-name`, `#profile-bio`, `#profile-photos`, `#profile-work`, `#profile-education`
  - `#badge-linkedin`, `#badge-trust-source` — badge elements showing Verified / Not verified
  - `#btn-like`, `#btn-pass`
- Link `styles.css` and defer `app.js`.
- No verification section yet (step 5 adds `#verification-panel`).

### `styles.css`

- Mobile-first card (~360px max width), centered.
- Photo area with aspect ratio ~3:4; support multiple photos as horizontal scroll or dot indicator.
- Badge styles: distinct classes `.badge-verified` (green) and `.badge-unverified` (muted).
- Work and education as stacked list items.
- Like (green) and Pass (red/gray) buttons fixed below card.
- Simple swipe animation optional (CSS transform on button click acceptable; no library required).

### `app.js` behavior

Constants at top:

```javascript
const API_BASE = ''; // same-origin
```

Functions (implement with fetch, no bundler):

| Function | Behavior |
|----------|----------|
| `fetchDeck()` | `GET /api/profiles` → parse `profiles` array |
| `renderProfile(profile)` | Fill DOM; map `photo_urls` to `<img src="...">`; render work_history as `title at company (years)`; education as `degree, school (year)`; set badge text/class from `linkedin_verified` and `trust_source_verified` |
| `swipe(direction)` | `POST /api/swipes` JSON `{profile_id, direction}` where direction is `"like"` or `"pass"`; on success advance to next profile |
| `init()` | Load deck, show first profile, attach button listeners |

State: in-memory index into deck array; on empty deck show `#empty-state`.

Error handling: `alert()` or inline `#error-message` for failed fetch (minimal).

**Do not** implement verification upload functions in step 4.

## API usage (must match step 2)

- `GET /api/profiles` → use each item’s `photo_urls`, `work_history`, `education_background`, verification booleans.
- `POST /api/swipes` with `Content-Type: application/json`.

## Implementation order

1. Build static HTML skeleton with placeholder text.
2. Style card and badges.
3. Implement `app.js` against running API (developer runs uvicorn manually).
4. Commit frontend-only.

## Commands and expected output

Syntax check (no server required):

```bash
cd /workspace/mock_app
node --check frontend/app.js
```

Expected: no output, exit code `0`.

Optional API integration check (requires step 2+3 server and step 5 mount **not** required if using curl to verify API separately):

```bash
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8765 &
sleep 2
curl -s http://127.0.0.1:8765/api/profiles | python -c "import sys,json; p=json.load(sys.stdin)['profiles']; assert len(p)>0; print('deck', len(p))"
kill %1 2>/dev/null || true
```

Expected stdout:

```text
deck <N>
```

where `<N>` ≥ 1.

File presence:

```bash
test -f frontend/index.html && test -f frontend/styles.css && test -f frontend/app.js && echo "frontend ok"
```

Expected:

```text
frontend ok
```

Grep contract ids:

```bash
grep -E 'id="(card-stack|btn-like|btn-pass|badge-linkedin)"' frontend/index.html
```

Expected: all four ids found in output.

## What must pass

- `node --check frontend/app.js` succeeds.
- All required element ids exist in `index.html`.
- `app.js` contains fetch calls to `/api/profiles` and `/api/swipes` (verify with `grep`).
- Step 2–3 `pytest` still passes unchanged:

```bash
pytest -v
```

Expected: all tests **PASSED**.

## What must fail (during step 4 only)

- `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/` → `404` (until step 5 mounts frontend).

## Screenshots (optional for this experimental app)

Not required unless orchestrator requests; step 5 E2E validation covers visual check.

## Commit

```bash
git add mock_app/frontend/
git commit -m "feat(mock_app): swipe UI with profile details and badges"
```
