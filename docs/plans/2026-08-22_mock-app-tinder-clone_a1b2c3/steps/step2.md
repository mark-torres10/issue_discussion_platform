# Step 2: Profiles and swipes API with tests

Implement JSON persistence, profile and swipe HTTP endpoints, and `main.py` with health check and mock-photo static mount. Test-first with `httpx` + FastAPI `TestClient`.

**Prerequisite:** Step 1 merged. Step 3 runs after this step (sequential on `main.py`).

## Caller

- Browser (step 4): `GET /api/profiles`, `GET /api/me`, `POST /api/swipes`
- Tests: `tests/test_profiles.py`, `tests/test_swipes.py`

## File tree (create)

```text
/workspace/mock_app/
  app/
    main.py
    routers/
      __init__.py
      profiles.py
      swipes.py
    services/
      __init__.py
      data_store.py
  tests/
    __init__.py
    conftest.py
    test_profiles.py
    test_swipes.py
```

## Out of scope

- Verification upload routes or `files.py`
- Upload directory mounts (step 3)
- Frontend files or frontend static mount (step 5)
- Editing `mock_data/profiles.json` profile content (only `swipes` array may be written at runtime)

## Files to inspect

- `/workspace/mock_app/app/config.py`
- `/workspace/mock_app/app/models/profile.py`
- `/workspace/mock_app/mock_data/profiles.json`
- `/workspace/docs/plans/2026-08-22_mock-app-tinder-clone_a1b2c3/steps/step1.md`

## Files allowed to change

- `/workspace/mock_app/app/main.py` (create — full app for profiles/swipes only)
- `/workspace/mock_app/app/routers/__init__.py` (create)
- `/workspace/mock_app/app/routers/profiles.py` (create)
- `/workspace/mock_app/app/routers/swipes.py` (create)
- `/workspace/mock_app/app/services/__init__.py` (create)
- `/workspace/mock_app/app/services/data_store.py` (create)
- `/workspace/mock_app/tests/__init__.py` (create)
- `/workspace/mock_app/tests/conftest.py` (create)
- `/workspace/mock_app/tests/test_profiles.py` (create)
- `/workspace/mock_app/tests/test_swipes.py` (create)
- `/workspace/mock_app/mock_data/profiles.json` (runtime writes to `swipes` only via data store)

## Files forbidden to change

- `/workspace/mock_app/app/config.py` (unless fixing a bug blocking step 2 — prefer not)
- `/workspace/mock_app/app/models/profile.py` (frozen from step 1)
- `/workspace/mock_app/app/routers/verifications.py`
- `/workspace/mock_app/app/services/files.py`
- `/workspace/mock_app/frontend/**`
- `/workspace/mock_app/tests/test_verifications.py`
- `/workspace/ui/**`, `/workspace/backend/**`

## HTTP API contract (freeze)

Base URL in tests: `http://testserver` via `TestClient`.

| Method | Path | Response | Notes |
|--------|------|----------|-------|
| `GET` | `/health` | `200` `{"status":"ok"}` | |
| `GET` | `/api/me` | `200` `Profile` JSON for `CURRENT_USER_ID` | |
| `GET` | `/api/profiles` | `200` `{"profiles":[Profile,...]}` | Excludes current user; excludes profiles already in `swipes` |
| `GET` | `/api/profiles/{profile_id}` | `200` Profile / `404` `{"detail":"Profile not found"}` | |
| `POST` | `/api/swipes` | `201` `SwipeRecord` / `404` unknown profile / `400` duplicate swipe / `400` cannot swipe self | Body: `SwipeRequest` |
| `GET` | `/api/swipes` | `200` `{"swipes":[SwipeRecord,...]}` | Ordered oldest-first |

Photo URLs in API responses: each profile includes resolved `photo_urls: list[str]` **in addition to** `photos` filenames, built as `/mock-photos/{filename}`.

Do not expose swipe deck profiles that are the current user.

## `data_store.py` contract

Class `DataStore` with methods:

| Method | Behavior |
|--------|----------|
| `__init__(self, data_path: Path \| None = None)` | Default `data_path = PROFILES_JSON` from config |
| `load(self) -> dict` | Read JSON; raise `FileNotFoundError` if missing |
| `save(self, data: dict) -> None` | Atomic write (write temp file then rename) |
| `list_profiles_for_deck(self) -> list[Profile]` | Filter as per API contract |
| `get_profile(self, profile_id: str) -> Profile \| None` | |
| `get_current_user(self) -> Profile` | `get_profile(CURRENT_USER_ID)`; raise `KeyError` if missing |
| `record_swipe(self, profile_id: str, direction: SwipeDirection) -> SwipeRecord` | Append to `swipes`; reject duplicate `profile_id`, reject `profile_id == CURRENT_USER_ID`, reject unknown id |
| `list_swipes(self) -> list[SwipeRecord]` | |

Use a module-level singleton `get_data_store()` returning one `DataStore` instance (tests reset by using a temp JSON file via fixture).

## `main.py` contract (step 2 scope)

- `FastAPI(title="Mock App")`
- Include routers with prefixes: profiles → `/api`, swipes → `/api`
- `GET /health`
- Mount `StaticFiles` at `/mock-photos` directory=`PHOTOS_DIR`, `name="mock-photos"`
- **Do not** mount frontend or upload dirs (step 3/5)
- Export `app` for uvicorn: `app.main:app`

## Test design (`conftest.py`)

Fixture `tmp_data_file`: copy step 1 `profiles.json` to tmp path with `swipes: []`; monkeypatch `get_data_store` to use tmp file; yield path; tests isolated.

Fixture `client`: `TestClient(app)` with monkeypatched store.

Reset swipes between tests via fresh tmp file per test or explicit truncate in fixture.

## `test_profiles.py` (write tests first)

1. `test_health_ok` — `GET /health` → 200, `status == "ok"`.
2. `test_get_me_returns_current_user` — `GET /api/me` → 200, `id == "user-me"`.
3. `test_list_profiles_excludes_current_user` — no profile in list has `id == "user-me"`.
4. `test_list_profiles_excludes_swiped` — after recording a swipe via store or POST, that `profile_id` absent from `GET /api/profiles`.
5. `test_get_profile_by_id` — known id → 200 with matching `name`.
6. `test_get_profile_not_found` — `GET /api/profiles/missing` → 404.

## `test_swipes.py` (write tests first)

1. `test_swipe_like_creates_record` — POST `{"profile_id":"<valid>","direction":"like"}` → 201, body has `profile_id`, `direction`, `swiped_at`.
2. `test_swipe_duplicate_returns_400` — same `profile_id` twice → second 400.
3. `test_swipe_self_returns_400` — `profile_id: "user-me"` → 400.
4. `test_swipe_unknown_profile_returns_404`.
5. `test_list_swipes_after_post` — POST then `GET /api/swipes` includes the record.

## Implementation order (TDD)

1. Write `conftest.py` and all tests (they fail).
2. Implement `data_store.py`.
3. Implement `routers/profiles.py`, `routers/swipes.py`.
4. Wire `main.py`.
5. Green tests; commit.

## Commands and expected output

```bash
cd /workspace/mock_app
source .venv/bin/activate
pytest tests/test_profiles.py tests/test_swipes.py -v
```

Expected: all tests **PASSED** (count ≥ 11).

```bash
pytest -v
```

Expected: only step 2 tests exist; all passed.

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8765
```

In another shell:

```bash
curl -s http://127.0.0.1:8765/health
```

Expected stdout:

```json
{"status":"ok"}
```

```bash
curl -s http://127.0.0.1:8765/api/me | python -m json.tool | head -5
```

Expected: JSON with `"id": "user-me"`.

Stop uvicorn after manual check.

## What must pass

- All tests in `test_profiles.py` and `test_swipes.py`.
- Manual health and `/api/me` curl checks.
- `GET /mock-photos/<existing-filename>.jpg` returns 200 when server running.

## What must fail

- `POST /api/verifications/linkedin` → 404 (route not implemented until step 3).
- `GET /` serving `index.html` → 404 (frontend mount is step 5).

## Commit

```bash
git add mock_app/app/main.py mock_app/app/routers/ mock_app/app/services/data_store.py mock_app/tests/
git commit -m "feat(mock_app): profiles and swipes API with tests"
```
