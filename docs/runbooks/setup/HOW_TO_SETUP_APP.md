# How to set up the app

Install the tools and packages you need before you start the app.

## Tools to install

You need Node.js 20.x and npm to run the UI. You need Python 3.12 and uv to run the FastAPI backend, and to run lint or tests at the repo root. uv is the installer for Python packages in this repo. You need the Vercel CLI and the Railway CLI to work with the hosted UI and API.

- Node.js 20.x
- npm (included with Node.js)
- Python 3.12
- uv
- Vercel CLI (`vercel`)
- Railway CLI (`railway`)

Install the CLIs if they are missing:

```bash
npm install -g vercel
brew install railway
```

## Install UI packages

Run `npm install` in `ui/` so packages from `ui/package-lock.json` are in `ui/node_modules`.

```bash
cd ui
npm install
```

## Where to edit participant wording

Shared screen text (home, introduction labels, audio check, conversation controls, completion, unavailable) lives in `ui/content/ui-copy.yaml`.

Sample issue text, AI persona, opening line, and scripted replies live in `ui/content/sessions/demo-campus-speech-001.yaml`.

After you edit a YAML file, refresh the running Next.js app to see the new wording. If a required key is missing, the app throws and names the key.

## Install Python packages

Run `uv sync --group dev` at the repo root so packages from `uv.lock` are in `.venv`. Skip this step if you only want to start the UI.

```bash
uv sync --group dev
```

The FastAPI backend lives in `backend/`. FastAPI is the Python web framework for the API. Sync that folder when you will run or deploy the API:

```bash
cd backend
uv sync
```

## Hosted projects

This repo is linked to one Vercel project for the Next.js UI in `ui/`, and one Railway project for the FastAPI API in `backend/`. Next.js is the web framework used in `ui/`.

Sign in once on this machine:

```bash
vercel login
railway login
```

Confirm the links:

```bash
vercel whoami
vercel project inspect issue-discussion-platform --cwd ui --scope marktorres10s-projects
railway whoami
railway status
```

`railway status` must be run from the repo root, which is already linked to the Railway project.

### Vercel (UI)

| | |
| --- | --- |
| Team | `marktorres10s-projects` (`marktorres10's projects`) |
| Project | `issue-discussion-platform` |
| Project ID | `prj_0YS7IAFzIGvFSAD9sOtLGxMtW8Qu` |
| Root directory | `ui` |
| Framework | Next.js, Node 20.x |
| GitHub | [mark-torres10/issue_discussion_platform](https://github.com/mark-torres10/issue_discussion_platform) |
| Dashboard | [Vercel project](https://vercel.com/marktorres10s-projects/issue-discussion-platform) |

The UI is not deployed until you push to GitHub or run a CLI deploy from `ui/`. Preview deploys are test URLs for a branch or CLI upload. Production is the live site for the main branch.

```bash
cd ui
vercel deploy --scope marktorres10s-projects -y --no-wait
```

After a deploy, open the URL printed by the CLI, or open the project on the Vercel dashboard. Add `--prod` only when you intend to update production.

### Railway (API)

| | |
| --- | --- |
| Workspace | `mark-torres10's Projects` |
| Project | `issue-discussion-platform` |
| Project ID | `dbbb5f8f-5e8d-4ec9-85d5-ed44f0bb8474` |
| Service | `api` |
| Environment | `production` |
| Public URL | [https://api-production-198a.up.railway.app](https://api-production-198a.up.railway.app) |
| Health | [https://api-production-198a.up.railway.app/health](https://api-production-198a.up.railway.app/health) |
| Dashboard | [Railway project](https://railway.com/project/dbbb5f8f-5e8d-4ec9-85d5-ed44f0bb8474) |

Open the public URL for `{"message": "Issue Discussion Platform API"}`. Open `/health` for `{"status": "ok"}`. The dashboard shows builds, logs, and the `api` service.

Deploy local `backend/` code again with:

```bash
railway up ./backend --path-as-root --service api --environment production --detach -m "Describe the change"
```

`--path-as-root` means Railway treats `backend/` as the app root. `--detach` queues the build and returns. Check status with `railway deployment list --service api --environment production`.

## After setup

Start the app with [How to run the app](../HOW_TO_RUN_APP.md).
