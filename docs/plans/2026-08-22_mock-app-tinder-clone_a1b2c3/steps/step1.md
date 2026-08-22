# Step 1: Scaffold, contracts, and mock data seed

Create the `mock_app` package layout, frozen data contracts, configuration constants, sample profiles on disk, and empty upload directories. No HTTP server behavior in this step.

## Caller

Steps 2–5 import from `app.config`, `app.models.profile`, and read `mock_data/profiles.json`. Step 1 only lays down files and shapes.

## File tree (create)

```text
/workspace/mock_app/
  pyproject.toml
  README.md
  app/
    __init__.py
    config.py
    models/
      __init__.py
      profile.py
  mock_data/
    profiles.json
    photos/
      alex-1.jpg
      jordan-1.jpg
      sam-1.jpg
  static/
    uploads/
      linkedin/
        .gitkeep
      trust_source/
        .gitkeep
```

Do **not** create routers, services, `main.py`, `frontend/`, or `tests/` yet (step 2+).

## Out of scope

- FastAPI app or routes
- Data store or file upload logic
- Frontend
- Automated tests (optional smoke import only)
- Changes outside `/workspace/mock_app/` and this plan folder

## Files to inspect

- `/workspace/docs/plans/2026-08-22_mock-app-tinder-clone_a1b2c3/plan.md`
- `/workspace/pyproject.toml` (repo root — read only for Python version hint; do not edit)

## Files allowed to change

- `/workspace/mock_app/pyproject.toml` (create)
- `/workspace/mock_app/README.md` (create — stub only; step 5 finishes)
- `/workspace/mock_app/app/__init__.py` (create)
- `/workspace/mock_app/app/config.py` (create)
- `/workspace/mock_app/app/models/__init__.py` (create)
- `/workspace/mock_app/app/models/profile.py` (create)
- `/workspace/mock_app/mock_data/profiles.json` (create)
- `/workspace/mock_app/mock_data/photos/*` (create — real small JPEG/PNG files, not empty placeholders)
- `/workspace/mock_app/static/uploads/linkedin/.gitkeep` (create)
- `/workspace/mock_app/static/uploads/trust_source/.gitkeep` (create)
- `/workspace/docs/plans/2026-08-22_mock-app-tinder-clone_a1b2c3/**` (only if fixing this plan)

## Files forbidden to change

- `/workspace/ui/**`
- `/workspace/backend/**`
- `/workspace/mock_app/app/main.py` (does not exist yet — do not create)
- `/workspace/mock_app/app/routers/**`
- `/workspace/mock_app/app/services/**`
- `/workspace/mock_app/frontend/**`
- `/workspace/mock_app/tests/**`
- Vercel, Railway, or root deploy config files

## `pyproject.toml` requirements

Project name: `mock-app-tinder-clone`.

Runtime dependencies (exact or minimum versions pinned in file):

- `fastapi>=0.115.0`
- `uvicorn[standard]>=0.32.0`
- `python-multipart>=0.0.9`
- `pydantic>=2.0`

Dev optional group `dev`:

- `pytest>=8.0`
- `httpx>=0.27.0`

`[project.scripts]` or documented module path: app served as `app.main:app` (file created in step 2).

`requires-python = ">=3.11"`.

## `app/config.py` contract (freeze)

All paths resolved from `MOCK_APP_ROOT = Path(__file__).resolve().parent.parent`.

| Constant | Value |
|----------|--------|
| `HOST` | `"127.0.0.1"` |
| `PORT` | `8765` |
| `MOCK_DATA_DIR` | `MOCK_APP_ROOT / "mock_data"` |
| `PROFILES_JSON` | `MOCK_DATA_DIR / "profiles.json"` |
| `PHOTOS_DIR` | `MOCK_DATA_DIR / "photos"` |
| `STATIC_DIR` | `MOCK_APP_ROOT / "static"` |
| `FRONTEND_DIR` | `MOCK_APP_ROOT / "frontend"` |
| `LINKEDIN_UPLOAD_DIR` | `STATIC_DIR / "uploads" / "linkedin"` |
| `TRUST_SOURCE_UPLOAD_DIR` | `STATIC_DIR / "uploads" / "trust_source"` |
| `CURRENT_USER_ID` | `"user-me"` (must match one profile id in JSON) |
| `ALLOWED_IMAGE_TYPES` | `{"image/jpeg", "image/png", "image/webp"}` |
| `ALLOWED_VIDEO_TYPES` | `{"video/mp4", "video/webm"}` |
| `MAX_UPLOAD_BYTES` | `10 * 1024 * 1024` (10 MiB) |

Export a helper `ensure_upload_dirs() -> None` that creates both upload directories if missing (used in step 3).

## `app/models/profile.py` contract (freeze)

Use Pydantic v2 `BaseModel`. All models JSON-serializable.

### `WorkEntry`

| Field | Type | Required |
|-------|------|----------|
| `company` | `str` | yes |
| `title` | `str` | yes |
| `start_year` | `int` | yes |
| `end_year` | `int \| None` | no (`null` = present) |

### `EducationEntry`

| Field | Type | Required |
|-------|------|----------|
| `school` | `str` | yes |
| `degree` | `str` | yes |
| `year` | `int` | yes |

### `Profile`

| Field | Type | Required |
|-------|------|----------|
| `id` | `str` | yes |
| `name` | `str` | yes |
| `bio` | `str` | yes |
| `photos` | `list[str]` | yes — filenames only, relative to `mock_data/photos/` |
| `work_history` | `list[WorkEntry]` | yes (may be empty list) |
| `education_background` | `list[EducationEntry]` | yes (may be empty list) |
| `linkedin_verified` | `bool` | yes, default `False` in model |
| `trust_source_verified` | `bool` | yes, default `False` in model |

Optional response-only fields (step 2+): none in step 1.

### `SwipeDirection` (enum)

Values: `"like"`, `"pass"`.

### `SwipeRequest` (API body, step 2)

| Field | Type |
|-------|------|
| `profile_id` | `str` |
| `direction` | `SwipeDirection` |

### `SwipeRecord` (persisted, step 2)

| Field | Type |
|-------|------|
| `profile_id` | `str` |
| `direction` | `SwipeDirection` |
| `swiped_at` | `str` (ISO 8601 UTC) |

### `VerificationKind` (enum)

Values: `"linkedin"`, `"trust_source"`.

Re-export models from `app/models/__init__.py`.

## `mock_data/profiles.json` contract

Top-level JSON object:

```json
{
  "profiles": [ ... ],
  "swipes": []
}
```

- `profiles`: array of at least **4** profile objects matching `Profile` shape.
- One profile **must** have `"id": "user-me"` with both verification flags `false` initially.
- Other profiles: distinct ids (e.g. `profile-alex`, `profile-jordan`, `profile-sam`).
- Each profile references at least one photo file that exists under `mock_data/photos/`.
- Include varied work and education entries on at least two profiles.
- Set `linkedin_verified: true` on one non-current profile and `trust_source_verified: true` on another (for badge UI testing in step 4).
- `swipes`: empty array `[]` (step 2 appends here).

Photo files: copy or generate small valid JPEGs (≥1 KB each). Filenames must match `photos` arrays in JSON.

## `README.md` stub

Three lines only:

```markdown
# Mock App — Tinder-like clone (localhost)

Run instructions will be added in step 5.
```

## Implementation order

1. Create directory tree and `pyproject.toml`.
2. Implement `config.py` and `profile.py` models.
3. Add sample images and `profiles.json`.
4. Create venv, install package, verify imports.
5. Commit: `feat(mock_app): scaffold contracts and mock data seed`.

## Commands and expected output

```bash
cd /workspace/mock_app
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Expected: install succeeds with no errors; `fastapi`, `pytest`, `httpx` available.

```bash
python -c "from app.config import PORT, CURRENT_USER_ID; from app.models.profile import Profile; print(PORT, CURRENT_USER_ID)"
```

Expected stdout (exact):

```text
8765 user-me
```

```bash
python -c "import json; from pathlib import Path; d=json.loads(Path('mock_data/profiles.json').read_text()); assert len(d['profiles'])>=4; assert any(p['id']=='user-me' for p in d['profiles']); print('profiles ok')"
```

Expected stdout:

```text
profiles ok
```

```bash
ls mock_data/photos/*.jpg mock_data/photos/*.png 2>/dev/null | wc -l
```

Expected: count ≥ 3 (at least three image files exist).

## What must pass

- Package installs editable with dev extras.
- Import of config and models succeeds.
- `profiles.json` validates against `Profile` models when loaded in a one-liner (implementer may run a quick script; no committed test file required in step 1).
- Upload directories contain `.gitkeep`.
- No files outside the allowed set were created (no `main.py` yet).

## What must fail (if attempted in step 1)

- `pytest` under `mock_app/tests/` — directory must not exist.
- `curl http://127.0.0.1:8765/` — server not running.
- Import `app.main` — module must not exist.

## Commit

```bash
git add mock_app/ docs/plans/2026-08-22_mock-app-tinder-clone_a1b2c3/
git commit -m "feat(mock_app): scaffold contracts and mock data seed"
```
