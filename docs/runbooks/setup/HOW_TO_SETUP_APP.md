# How to set up the app

Install the tools and packages you need before you start the app.

## Tools to install

You need Node.js 20.x and npm to run the UI. You need Python 3.12 and uv to run the FastAPI backend, and to run lint or tests at the repo root. uv is the installer for Python packages in this repo. You need the Vercel CLI, the Railway CLI, and the Supabase CLI to work with the hosted UI, API, and database. Supabase is the hosted Postgres and auth service for this repo.

- Node.js 20.x
- npm (included with Node.js)
- Python 3.12
- uv
- Vercel CLI (`vercel`)
- Railway CLI (`railway`)
- Supabase CLI (`supabase`)

Install the CLIs if they are missing:

```bash
npm install -g vercel
brew install railway
brew install supabase/tap/supabase
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

This repo is linked to one Vercel project for the Next.js UI in `ui/`, one Railway project for the FastAPI API in `backend/`, and one Supabase project for hosted Postgres. Next.js is the web framework used in `ui/`. GitHub is connected to Vercel and Railway. The Supabase CLI is linked from the repo root.

A pull request deploys a Vercel **preview** (a unique test URL for that branch). Merging into `main` deploys Vercel **production** and rebuilds the Railway `api` service in **production**.

Sign in once on this machine:

```bash
vercel login
railway login
supabase login
```

Confirm the links:

```bash
vercel whoami
vercel project inspect issue-discussion-platform --cwd ui --scope marktorres10s-projects
railway whoami
railway status
supabase projects list
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

Push a branch and open a pull request. Vercel comments on the PR with the preview URL. Merge to `main` to update production. Open production and recent previews from the dashboard, or list them with:

```bash
vercel ls --scope marktorres10s-projects --cwd ui
```

Use a CLI deploy only when you need an upload that is not from GitHub:

```bash
cd ui
vercel deploy --scope marktorres10s-projects -y --no-wait
```

Add `--prod` only when you intend to update production from the CLI.

### Railway (API)

| | |
| --- | --- |
| Workspace | `mark-torres10's Projects` |
| Project | `issue-discussion-platform` |
| Project ID | `dbbb5f8f-5e8d-4ec9-85d5-ed44f0bb8474` |
| Service | `api` |
| GitHub source | `mark-torres10/issue_discussion_platform`, branch `main`, root `/backend` |
| Environment | `production` |
| Public URL | [https://api-production-198a.up.railway.app](https://api-production-198a.up.railway.app) |
| Health | [https://api-production-198a.up.railway.app/health](https://api-production-198a.up.railway.app/health) |
| Dashboard | [Railway project](https://railway.com/project/dbbb5f8f-5e8d-4ec9-85d5-ed44f0bb8474) |

Open the public URL for `{"message": "Issue Discussion Platform API"}`. Open `/health` for `{"status": "ok"}` and the git commit SHA when Railway deployed from GitHub. The dashboard shows builds, logs, and the `api` service.

Merging into `main` rebuilds production. Check status with `railway deployment list --service api --environment production`.

Use a CLI upload only when you need to ship local files that are not on GitHub yet:

```bash
railway up ./backend --path-as-root --service api --environment production --detach -m "Describe the change"
```

`--path-as-root` means Railway treats `backend/` as the app root. `--detach` queues the build and returns.

### Supabase (database)

| | |
| --- | --- |
| Organization | `mark-torres10's Org` (`ziawajuzavopbzcayxno`) |
| Project | `issue-discussion-platform` |
| Project ref | `unlvjgskqzdceihzacng` |
| Region | `us-east-1` (East US, North Virginia) |
| API URL | [https://unlvjgskqzdceihzacng.supabase.co](https://unlvjgskqzdceihzacng.supabase.co) |
| Dashboard | [Supabase project](https://supabase.com/dashboard/project/unlvjgskqzdceihzacng) |
| CLI config | `supabase/config.toml` at the repo root |

The repo root is already linked. `supabase projects list` marks this project with a filled circle when the link is in place. If the link is missing, run this from the repo root (the database password is the one set when the project was created):

```bash
supabase link --project-ref unlvjgskqzdceihzacng
```

Open the dashboard to use the Table Editor, SQL Editor, Auth, and API settings. The API URL is the host for client and server calls to this project.

Get API keys from the dashboard (Project Settings, then API Keys) or from the CLI:

```bash
supabase projects api-keys --project-ref unlvjgskqzdceihzacng
```

Use the publishable (anon) key in browser or Next.js `NEXT_PUBLIC_` env vars. Keep the secret (`service_role`) key on the server only. Do not commit keys or the database password. `*.env` and `supabase/.env.local` are gitignored.

A local Docker copy is optional. It is not required to use the hosted project:

```bash
supabase start
supabase status
```

## After setup

Start the app with [How to run the app](../HOW_TO_RUN_APP.md).
