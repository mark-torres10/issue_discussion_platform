# Credentials and setup to enable the study stack

Create the accounts and copy the values below before you wire the Study API, staff login, voice, or tracing. Local UI sample screens in `ui/` do not need these yet. You need them as soon as you leave Sample contracts.

Do not put secrets in git. Store them in a password manager and in the host dashboards named below.

Official product pages:

* [Vercel](https://vercel.com)
* [Railway](https://railway.com)
* [OpenAI API keys](https://platform.openai.com/api-keys)
* [OpenAI Realtime](https://developers.openai.com/api/docs/guides/realtime-webrtc)
* [Supabase](https://supabase.com/dashboard)
* [LangSmith](https://smith.langchain.com)

## Accounts to create

Create one account (or a shared team seat) for each product. Use a work email that the study team can recover.

| Product | Why you need it | Who should own the seat |
| --- | --- | --- |
| GitHub | Hosts the repo and feeds Vercel and Railway deploys | Repo admin |
| Vercel | Hosts the participant UI and staff login pages | Frontend deploy owner |
| Railway | Hosts the Study API, the Realtime control worker, and Study Postgres | Backend deploy owner |
| OpenAI | Text generation and Realtime voice | Research or engineering owner with billing access |
| Supabase | Staff email and password login only | Auth owner |
| LangSmith | Derived traces after records commit | Observability owner |

You do not need a separate Postgres vendor. Study Postgres is a private Railway Postgres database owned by the Study API.

You do not need participant accounts in Supabase. Participants use invitation tokens.

## What to turn on in each dashboard

Do these dashboard steps in one sitting. Write down the resulting URLs and keys as you go.

### GitHub

1. Confirm you can push to this repository.
2. Invite the people who will deploy. They need access so Vercel and Railway can read the repo.
3. Do not store API keys in GitHub Actions until CI needs them.

### Vercel

1. Create a Vercel team or personal account.
2. Import this GitHub repository. Set the root directory to `ui/` when you create the project.
3. Attach a production domain you control, or keep the default `*.vercel.app` URL for staging.
4. Add `http://localhost:3000` as a local origin you will allow from the Study API later.
5. Keep participant routes public. Do not put Vercel Deployment Protection in front of `/invite` or `/session`, or participants cannot open study links.
6. Protect `/login` and `/app` in application code with Supabase Auth, not with Vercel SSO, unless staff-only preview URLs need extra protection.

Copy these values:

* Production UI origin, e.g. `https://your-app.vercel.app`
* Preview origin pattern, if you will allow Vercel preview deployments to call the Study API

### Railway

1. Create a Railway account and a project named for this study.
2. Create three environments if the team wants the same split as LangSmith. Local can stay on a laptop. Staging and production should be Railway environments.
3. Add a Postgres service. This is Study Postgres. Do not expose it on the public internet. The Study API and the worker should connect over Railway private networking.
4. Add a web service for the Study API.
5. Add a worker service for Realtime sideband control. You can add it when you reach Voice control, but creating the empty service now keeps networking simple.
6. Give the Study API a public HTTPS domain. The Vercel browser must call that origin.
7. Turn on encrypted backups and point in time recovery on Postgres before any real participant data. The backend plan target is no more than 5 minutes of data loss.
8. Generate a long random string for internal worker calls. The worker uses it to post provider items to `POST /internal/v1/realtime/calls/{openai_call_id}/items`.

Copy these values:

* Study API public origin, e.g. `https://study-api.up.railway.app`
* Postgres connection URL (private). Railway often names this `DATABASE_URL`.
* Internal worker shared secret that you generate

### OpenAI

1. Create or select an OpenAI organization with billing enabled.
2. Create an API key that can call Chat Completions (or the current Responses API you choose for text) and Realtime.
3. Confirm Realtime and WebRTC are enabled for that key. Server-mediated setup needs the standard API key on the Study API only. The browser must never receive that key.
4. Set usage limits and billing alerts. The backend plan expects a per session spend cutoff and a text fallback when the snapshot allows text.
5. Note the model IDs you will put in configuration snapshots. Do not treat "GPT live" as a fixed model name.
6. You do not create a separate OpenAI "client secret" product for participants. The Study API submits SDP and returns only the SDP answer.

Copy these values:

* `OPENAI_API_KEY`
* Organization ID (for support and spend views, not for the browser)

### Supabase

1. Create a Supabase project for this application.
2. Keep Email auth enabled. Do not enable OAuth, magic links, phone auth, or anonymous sign-in for the first staff login.
3. Disable public signup in production. Create staff users in the dashboard.
4. Set Auth Site URL to the Vercel production origin. Add `http://localhost:3000` and any preview URLs under redirect URLs.
5. Set a minimum password length that matches campus rules.
6. Enable multifactor authentication before staff can export transcripts in production.
7. Create at least one staff user. Store the temporary password in the team secret process.
8. Copy the project URL and the publishable key. Those go to Vercel.
9. Copy the JWT secret (or JWKS URL) and the service role key. Those go to Railway only.

Copy these values from Project Settings:

* Project URL
* Publishable key (sometimes labeled anon public)
* JWT secret
* Service role key

Never put the service role key in Vercel or in any `NEXT_PUBLIC_` variable.

### LangSmith

1. Create a LangSmith account in the workspace the study team will use.
2. Create three projects, one per operational boundary:
   * `issue-discussion-local`
   * `issue-discussion-staging`
   * `issue-discussion-prod`
3. Create an API key for each environment, or one key per workspace if your LangSmith plan uses workspace keys.
4. Copy `LANGSMITH_WORKSPACE_ID` only if LangSmith's current docs require it for your key type. Do not assume every key needs it.
5. Invite researchers who should open Threads. Do not invite them to local or staging if those projects must stay free of real participant data.
6. Leave production tracing off in the app until a trace policy version is approved. Creating the projects now is still useful.

Copy these values:

* API key for staging
* API key for production
* Project names above
* Workspace ID, only if required

## Secrets by host

Set the same names in each environment (local, staging, production) with environment-specific values.

### Vercel and `ui/.env.local`

These are the only values the Next.js app should receive.

```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
NEXT_PUBLIC_STUDY_API_ORIGIN=
```

`NEXT_PUBLIC_STUDY_API_ORIGIN` is the public Study API origin the browser calls for participant routes, e.g. `https://study-api.up.railway.app`. Local sample UI can omit it until you wire HTTP.

Do not set on Vercel:

* `OPENAI_API_KEY`
* `DATABASE_URL`
* `SUPABASE_SERVICE_ROLE_KEY`
* `LANGSMITH_API_KEY`
* Internal worker secrets

Staff JWTs stay in browser-managed Supabase cookies on the Vercel origin. The Next.js server forwards them to staff Study API routes. Application JavaScript must not call staff Study API routes with a raw token.

### Railway Study API

```bash
DATABASE_URL=
OPENAI_API_KEY=
PARTICIPANT_UI_ORIGINS=https://your-app.vercel.app,http://localhost:3000
PARTICIPANT_COOKIE_SECRET=
INTERNAL_WORKER_TOKEN=
SUPABASE_URL=
SUPABASE_JWT_SECRET=
SUPABASE_SERVICE_ROLE_KEY=
STUDY_API_ROLE=api
```

`PARTICIPANT_COOKIE_SECRET` is a long random string used to sign the HTTP-only participant capability cookie. Generate a new value per environment.

`PARTICIPANT_UI_ORIGINS` is the CORS and CSRF allowlist. Do not use `*`. Include every Vercel origin that may send credentialed participant requests.

`STUDY_API_ROLE=api` makes `/ready` check Postgres. Sample mode on a laptop can use a sample role that does not require Postgres.

Optional until Approved tracing:

```bash
TRACE_EXPORT_ENABLED=false
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=issue-discussion-staging
LANGSMITH_WORKSPACE_ID=
```

Keep `TRACE_EXPORT_ENABLED=false` until a trace policy is approved. `LANGSMITH_TRACING=false` does not disable every LangSmith SDK path. The application feature flag is the switch that must stay off.

### Railway worker

```bash
DATABASE_URL=
OPENAI_API_KEY=
INTERNAL_WORKER_TOKEN=
STUDY_API_INTERNAL_ORIGIN=
STUDY_API_ROLE=worker
```

`STUDY_API_INTERNAL_ORIGIN` should be the private Railway hostname of the Study API when possible, not the public URL.

### Local Study API on a laptop

Use a `.env` file that is gitignored. You can point `DATABASE_URL` at a local Postgres or at a Railway staging database that holds only synthetic data. Never point local LangSmith at production, and never export real participant text from a laptop.

## Shared non-secret settings to decide while you are in the dashboards

These are not API keys, but you will need the answers when you paste origins and create users.

* Production UI origin and whether preview deployments may call staging Study API
* One `study_id` UUID for v1, even if there is only one study
* Staff emails, roles (`operator`, `researcher`, `study_admin`), and that `study_id`
* OpenAI model IDs for text and for Realtime
* Monthly OpenAI spend cap and alert emails
* LangSmith retention on new traces (LangSmith changes apply to new traces, not old ones)
* Whether the protocol requires stored consent before OpenAI transmission

## What you can skip until a later milestone

| Milestone | You can wait on |
| --- | --- |
| Sample contracts | Railway, OpenAI, Supabase, LangSmith, and Postgres. The `ui/` app can run with YAML sample data. |
| Durable record | OpenAI Realtime, LangSmith export, MFA if no transcript export exists yet |
| Voice control | LangSmith production export. You still need `OPENAI_API_KEY` and the worker secret. |
| Approved tracing | Dataset and evaluator products in LangSmith. You still need the three LangSmith projects and keys. |
| Research export | LangSmith experiments. Exports come from Study Postgres. |

## Quick paste checklist

Work top to bottom. Check a box when the value is in the password manager and in the correct host.

GitHub and Vercel:

* [ ] GitHub repo access
* [ ] Vercel project with root `ui/`
* [ ] Production UI origin copied
* [ ] Participant routes not behind Vercel Authentication
* [ ] `NEXT_PUBLIC_SUPABASE_URL` set
* [ ] `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` set
* [ ] `NEXT_PUBLIC_STUDY_API_ORIGIN` set (after Railway has a public domain)

Railway:

* [ ] Project and staging environment
* [ ] Postgres created and not public
* [ ] Backups and point in time recovery enabled
* [ ] Study API public HTTPS domain copied
* [ ] `DATABASE_URL` set on API and worker
* [ ] `PARTICIPANT_COOKIE_SECRET` generated
* [ ] `INTERNAL_WORKER_TOKEN` generated
* [ ] `PARTICIPANT_UI_ORIGINS` matches Vercel and localhost

OpenAI:

* [ ] Billing enabled
* [ ] API key created
* [ ] Realtime allowed on that key
* [ ] Usage limit and alert set
* [ ] `OPENAI_API_KEY` set on Railway only

Supabase:

* [ ] Project created
* [ ] Email auth on, public signup off in production
* [ ] Site URL and redirect URLs match Vercel and localhost
* [ ] First staff user created
* [ ] MFA plan for production export
* [ ] Publishable key on Vercel only
* [ ] JWT secret on Railway
* [ ] Service role key on Railway only

LangSmith:

* [ ] Account and workspace
* [ ] Projects `issue-discussion-local`, `issue-discussion-staging`, `issue-discussion-prod`
* [ ] API keys stored
* [ ] Keys on Railway only
* [ ] `TRACE_EXPORT_ENABLED=false` until policy approval

## How to tell it worked

After the values are set, these checks are enough to know the dashboards are connected:

1. Vercel production loads `/login` and `/session` without Vercel Authentication blocking them.
2. A staff user can sign in at `/login` with the Supabase user you created.
3. Railway `/health` returns ok. After Durable record, `/ready` returns ok with Postgres configured.
4. A test Chat Completions or Realtime call from the Railway environment succeeds, and the key never appears in the browser network panel.
5. LangSmith shows no production participant traces while `TRACE_EXPORT_ENABLED` is false.

The contracts that use these credentials live in `backend_proposal_2026_08_06.md`, `langsmith_proposal_2026_08_06.md`, `supabase_auth_proposal_2026_08_05.md`, and `ui_proposal_2026_08_06.md`.
