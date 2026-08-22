# Step 5: Verification UI, frontend mount glue, README

Add the verification upload panel to the frontend, mount static frontend in `main.py`, finalize README with exact run instructions, and verify full localhost happy path.

**Prerequisite:** Steps 2–4 complete. **Sequential:** edits `main.py` and extends `frontend/*` after step 4.

## Caller

End user: open app → swipe → open verification panel → upload photo/video → see badges update on `/api/me` and in UI after reload.

## File tree (touch)

```text
/workspace/mock_app/
  app/main.py          # add frontend StaticFiles + index route
  frontend/index.html  # add verification panel
  frontend/styles.css  # panel styles
  frontend/app.js      # upload handlers
  README.md            # complete runbook
```

## Out of scope

- Deployment or Docker
- Auth or multi-user sessions
- Changes outside `/workspace/mock_app/`
- New API endpoints beyond step 3 contract

## Files to inspect

- `/workspace/mock_app/app/main.py`
- `/workspace/mock_app/app/routers/verifications.py`
- `/workspace/mock_app/frontend/*` (step 4)
- `/workspace/mock_app/app/config.py` (`FRONTEND_DIR`, `HOST`, `PORT`)
- `/workspace/docs/plans/2026-08-22_mock-app-tinder-clone_a1b2c3/plan.md`

## Files allowed to change

- `/workspace/mock_app/app/main.py` (add frontend serving only)
- `/workspace/mock_app/frontend/index.html`
- `/workspace/mock_app/frontend/styles.css`
- `/workspace/mock_app/frontend/app.js`
- `/workspace/mock_app/README.md` (replace stub with full instructions)

## Files forbidden to change

- `/workspace/mock_app/app/routers/**` (unless critical bug — avoid)
- `/workspace/mock_app/app/services/**`
- `/workspace/mock_app/app/models/**`
- `/workspace/mock_app/mock_data/**` (except runtime uploads/swipes from usage)
- `/workspace/mock_app/tests/**` (must stay green; no test edits unless fixing flake)
- `/workspace/ui/**`, `/workspace/backend/**`

## `main.py` frontend glue contract

Add **without removing** existing routes/mounts from steps 2–3:

1. Mount `StaticFiles(directory=FRONTEND_DIR, html=True)` at `/` **or** serve `index.html` via explicit route and mount assets at `/static` — preferred pattern for clarity:

| Mount | Path | Directory |
|-------|------|-----------|
| Frontend files | `/` | `FRONTEND_DIR` with `html=True` so `/` serves `index.html` |

If `html=True` on `/` conflicts with `/api` routes, use Starlette order: register API routers **before** catch-all static, or mount frontend at `/` with `html=True` after API includes (FastAPI matches more specific routes first — `/api/*` and `/health` must still work).

2. Verify `GET /health`, `/api/*`, `/mock-photos/*`, `/uploads/*` still work.

## Frontend verification UI contract

Add to `index.html` section `#verification-panel`:

| Element id | Purpose |
|------------|---------|
| `#verification-panel` | collapsible section |
| `#btn-toggle-verification` | show/hide panel |
| `#linkedin-photo`, `#linkedin-video` | file inputs (optional either) |
| `#btn-submit-linkedin` | POST linkedin verification |
| `#trust-photo`, `#trust-video` | file inputs |
| `#btn-submit-trust` | POST trust_source verification |
| `#verification-status` | text feedback (success/error) |
| `#current-user-badges` | mirror of current user verification state (optional) |

### `app.js` additions

| Function | Behavior |
|----------|----------|
| `fetchMe()` | `GET /api/me` → update badge display for current user in panel header |
| `uploadVerification(kind)` | Build `FormData`; append `photo` and/or `video` if selected; `POST /api/verifications/{kind}` where kind is `linkedin` or `trust_source`; on 200 refresh me + show success in `#verification-status` |
| Wire buttons `#btn-submit-linkedin`, `#btn-submit-trust` |

Use same-origin relative URLs (no CORS).

After successful upload, call `fetchMe()` and update `#badge-linkedin` / `#badge-trust-source` on the **card** if current user is shown elsewhere, or show current user status only in panel (minimum: panel shows updated flags).

## README.md contract (replace stub entirely)

Must include these exact sections and commands:

### Title

`# Mock App — Tinder-like clone (localhost)`

### Prerequisites

- Python 3.11+
- macOS/Linux/WSL (or Windows with venv)

### Setup

```bash
cd /workspace/mock_app
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Run

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

### Open

`http://127.0.0.1:8765/`

### Test

```bash
pytest -v
```

### Happy path (manual)

Numbered list: open app → swipe like/pass → open verification → upload image for LinkedIn → confirm badge → upload for Trust Source → confirm badge.

### Scope note

Local only; no deployment; does not modify main repo UI/backend.

## End-to-end manual verification script

Run with server up:

```bash
# 1. Root serves HTML
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/
# expect 200

# 2. API still works
curl -s http://127.0.0.1:8765/health
# expect {"status":"ok"}

# 3. Verification
curl -s -F "photo=@mock_data/photos/alex-1.jpg;type=image/jpeg" http://127.0.0.1:8765/api/verifications/trust_source | python -c "import sys,json; print(json.load(sys.stdin)['trust_source_verified'])"
# expect True

# 4. Full test suite
pytest -v
```

## Implementation order

1. Update `main.py` frontend mount; verify `/` returns HTML.
2. Add verification panel markup and styles.
3. Implement upload JS; manual browser test.
4. Write README.
5. Run full pytest + manual script.
6. Commit.

## Commands and expected output

```bash
cd /workspace/mock_app
source .venv/bin/activate
pytest -v
```

Expected: all tests **PASSED** (profiles, swipes, verifications).

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Second terminal:

```bash
curl -s http://127.0.0.1:8765/ | head -5
```

Expected: HTML containing `<!DOCTYPE html>` or `<html` and `id="card-stack"`.

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/api/profiles
```

Expected: `200`

```bash
grep -q "uvicorn app.main:app" README.md && grep -q "127.0.0.1:8765" README.md && echo "readme ok"
```

Expected:

```text
readme ok
```

## What must pass

- Full pytest suite green.
- `GET /` serves `index.html` with swipe and verification UI elements.
- Browser happy path: swipe at least one card; upload sets verification flags visible in UI or via `/api/me`.
- README contains setup, run, test, and open URL instructions.
- No files modified outside `/workspace/mock_app/`.

## What must fail

- Access from non-localhost binding if user only starts with `127.0.0.1` (documented) — `0.0.0.0` not required.

## Commit

```bash
git add mock_app/
git commit -m "feat(mock_app): verification UI, frontend mount, and README"
```

## Orchestrator note

Steps 4 and 5 are **sequential** on `frontend/*`. Steps 2 and 3 are **sequential** on `main.py`. Steps 1 ∥ none. Steps 2–3 backend can be parallelized with step 4 only if step 4 avoids `main.py` (as specified); step 5 must run last.
