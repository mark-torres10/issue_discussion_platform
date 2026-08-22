# Mock App — Tinder-like clone (localhost)

A local-only prototype with profile swiping and verification uploads. Serves the frontend and API from the same origin on `127.0.0.1:8765`.

## Prerequisites

- Python 3.11+
- macOS/Linux/WSL (or Windows with venv)

## Setup

```bash
cd /workspace/mock_app
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

## Open

`http://127.0.0.1:8765/`

## Test

```bash
pytest -v
```

## Happy path (manual)

1. Open `http://127.0.0.1:8765/` in your browser.
2. Swipe through profiles with **Like** or **Pass**.
3. Click **Verification** in the header to open the verification panel.
4. On the **LinkedIn** tab, choose a photo and/or video, preview if shown, then click **Submit LinkedIn verification**.
5. Confirm the LinkedIn badge shows **Verified** in the panel.
6. Switch to the **Trust Source** tab, upload a photo and/or video, and submit.
7. Confirm the Trust Source badge shows **Verified** in the panel.

You can also confirm via the API:

```bash
curl -s http://127.0.0.1:8765/api/me | python -m json.tool
```

Look for `"linkedin_verified": true` and `"trust_source_verified": true`.

## Scope note

Local only; no deployment; does not modify main repo UI/backend.
