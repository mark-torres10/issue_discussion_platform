# Step 3: Verification upload API, static mounts, tests

Add multipart upload handling, verification endpoints that flip boolean tags on the current user, and extend `main.py` with upload static mounts. Test-first.

**Prerequisite:** Step 2 complete. This step **sequentially edits** `main.py` after step 2.

## Caller

- Browser (step 5): `POST /api/verifications/linkedin`, `POST /api/verifications/trust_source`
- Tests: `tests/test_verifications.py`

## File tree (create)

```text
/workspace/mock_app/
  app/
    routers/
      verifications.py
    services/
      files.py
  tests/
    test_verifications.py
```

## Out of scope

- Frontend verification UI (step 5)
- Serving `frontend/` (step 5)
- Changing profile model fields
- External network calls or real LinkedIn/Trust Source integration

## Files to inspect

- `/workspace/mock_app/app/main.py` (from step 2)
- `/workspace/mock_app/app/config.py`
- `/workspace/mock_app/app/services/data_store.py`
- `/workspace/mock_app/app/models/profile.py`
- `/workspace/docs/plans/2026-08-22_mock-app-tinder-clone_a1b2c3/steps/step2.md`

## Files allowed to change

- `/workspace/mock_app/app/routers/verifications.py` (create)
- `/workspace/mock_app/app/services/files.py` (create)
- `/workspace/mock_app/tests/test_verifications.py` (create)
- `/workspace/mock_app/app/main.py` (**add only**: include verifications router; call `ensure_upload_dirs()` on startup; mount `/uploads/linkedin` and `/uploads/trust_source` StaticFiles; do not remove step 2 routes/mounts)
- `/workspace/mock_app/app/services/data_store.py` (**add only** methods listed below — do not break step 2 tests)

## Files forbidden to change

- `/workspace/mock_app/app/routers/profiles.py`
- `/workspace/mock_app/app/routers/swipes.py`
- `/workspace/mock_app/app/models/profile.py`
- `/workspace/mock_app/app/config.py` (unless upload constants missing — should exist from step 1)
- `/workspace/mock_app/frontend/**`
- `/workspace/mock_app/tests/test_profiles.py`
- `/workspace/mock_app/tests/test_swipes.py`
- `/workspace/ui/**`, `/workspace/backend/**`

## Extend `data_store.py`

Add:

| Method | Behavior |
|--------|----------|
| `set_verification(self, kind: VerificationKind, verified: bool = True) -> Profile` | Update current user’s `linkedin_verified` or `trust_source_verified`; persist JSON; return updated profile |
| `append_verification_media(self, kind: VerificationKind, relative_path: str) -> None` | Optional: store under `data["verification_media"][kind]` list of relative URLs — if YAGNI, skip and only set boolean (tests only require boolean flip) |

Minimum for tests: boolean flags flip and persist after `save`.

## `files.py` contract

| Function | Behavior |
|----------|----------|
| `save_upload(*, kind: VerificationKind, file: UploadFile, prefix: str) -> str` | Validate content-type in allowed image OR video sets from config; enforce `MAX_UPLOAD_BYTES`; write to correct upload dir with filename `{prefix}_{uuid}{ext}`; return relative URL path e.g. `/uploads/linkedin/{filename}` |

Raise `HTTPException(400)` for wrong type or empty file. Use `fastapi.UploadFile`.

## HTTP API contract

Both endpoints accept `multipart/form-data` with **optional** fields (at least one required):

| Field | Type | Notes |
|-------|------|-------|
| `photo` | file | image MIME |
| `video` | file | video MIME |

| Method | Path | Success | Errors |
|--------|------|---------|--------|
| `POST` | `/api/verifications/linkedin` | `200` updated `Profile` for current user, `linkedin_verified: true` | `400` if no files; `400` bad MIME |
| `POST` | `/api/verifications/trust_source` | `200` updated Profile, `trust_source_verified: true` | same |

Response body: full current user `Profile` JSON (same shape as `/api/me`) plus optional `uploaded_urls: list[str]` if implemented.

Idempotent: posting again keeps flags `true`.

## `main.py` additions (only)

```python
# On startup event or lifespan: ensure_upload_dirs()
# app.include_router(verifications_router)
# StaticFiles mounts:
#   /uploads/linkedin -> LINKEDIN_UPLOAD_DIR
#   /uploads/trust_source -> TRUST_SOURCE_UPLOAD_DIR
```

Keep `/health`, `/api/*`, `/mock-photos` from step 2 unchanged.

## Test design (`test_verifications.py`)

Use `TestClient` and tmp data file fixture from `conftest.py` (extend conftest if needed to reset verification flags on `user-me` to `false` each test).

1. `test_linkedin_verification_requires_file` — POST with no files → 400.
2. `test_linkedin_verification_photo_sets_flag` — POST with small JPEG bytes, filename `id.jpg`, content-type `image/jpeg` → 200, `linkedin_verified is True`.
3. `test_trust_source_verification_video_sets_flag` — POST with minimal MP4 or webm fixture bytes (can be tiny invalid-but-typed blob if save only checks MIME — prefer minimal valid header) → 200, `trust_source_verified is True`.
4. `test_get_me_reflects_verification_after_post` — after linkedin POST, `GET /api/me` shows `linkedin_verified: true`.
5. `test_reject_invalid_mime` — POST `text/plain` as photo → 400.

Helper in test file to build multipart upload:

```python
def _upload(client, path, photo=None, video=None):
    files = []
    if photo:
        files.append(("photo", ("test.jpg", photo, "image/jpeg")))
    if video:
        files.append(("video", ("test.mp4", video, "video/mp4")))
    return client.post(path, files=files)
```

## Implementation order (TDD)

1. Write failing `test_verifications.py`.
2. Implement `files.py`.
3. Extend `data_store.py`.
4. Implement `routers/verifications.py`.
5. Patch `main.py` mounts and router.
6. Green all tests including step 2 regression.

## Commands and expected output

```bash
cd /workspace/mock_app
source .venv/bin/activate
pytest tests/test_verifications.py -v
```

Expected: all verification tests **PASSED** (≥ 5).

```bash
pytest -v
```

Expected: all tests in `test_profiles.py`, `test_swipes.py`, `test_verifications.py` **PASSED**.

Manual (server running):

```bash
curl -s -o /dev/null -w "%{http_code}" -F "photo=@mock_data/photos/alex-1.jpg;type=image/jpeg" http://127.0.0.1:8765/api/verifications/linkedin
```

Expected: `200`

```bash
curl -s http://127.0.0.1:8765/api/me | python -c "import sys,json; print(json.load(sys.stdin).get('linkedin_verified'))"
```

Expected: `True`

## What must pass

- All verification tests green.
- Step 2 tests still green.
- Uploaded file appears under `static/uploads/linkedin/` or `trust_source/` after POST.
- Static mount serves file at returned URL path.

## What must fail

- `GET /` → still 404 until step 5.
- Upload over `MAX_UPLOAD_BYTES` → 400 (optional test; add if trivial).

## Commit

```bash
git add mock_app/app/routers/verifications.py mock_app/app/services/files.py mock_app/app/main.py mock_app/app/services/data_store.py mock_app/tests/
git commit -m "feat(mock_app): verification upload API and static mounts"
```
