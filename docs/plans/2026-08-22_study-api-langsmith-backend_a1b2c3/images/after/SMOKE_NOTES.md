# API smoke transcript (2026-08-22 re-run)

Fresh backend (`uv run fastapi dev --host 127.0.0.1 --port 8000`), UI at `http://localhost:3000` with `NEXT_PUBLIC_STUDY_API_ORIGIN=http://127.0.0.1:8000`.

Token: `demo-campus-speech-001-invitation-token-for-contract-tests`

## Curl checks

```
GET /health
→ 200 {"status":"ok","commit":null}

GET /v1/participant-session (no cookie)
→ 401 {"error_code":"capability_missing","message":"Participant capability cookie is required"}

POST /v1/participant-access/exchange
  body: {"invitation_token":"demo-campus-speech-001-invitation-token-for-contract-tests"}
→ 200 (writer_role: writer, issue: campus-speech, persona: Jordan)

GET /v1/participant-session (with capability cookie + x-csrf-token)
→ 200 (status: pending, version: 1)

POST /v1/participant-session/start (text mode, via UI server action)
→ 200 (status: active, opening_turn from Jordan)
```

## UI flow (Playwright, localhost)

1. `GET /invite/<token>` → 307 → `/session` (cookies set on redirect)
2. `/session` → intro "Before you begin" with Jordan + campus-speech issue
3. Continue → `/session/audio-check` → "Check your audio"
4. Text mode → Start discussion → `/session/conversation` with issue title visible
5. `/session/unavailable` without cookies → 200 (not 500), "This session is unavailable"

## Notes

- Use **localhost** (not 127.0.0.1) in the browser so invite cookies match subsequent page loads.
- Conversation requires a fresh backend or writer role; re-running invite on a dirty backend can yield `writer_conflict` on start.
- Unauthorized session now returns **401** `capability_missing` (previously 500 `internal_error`).
