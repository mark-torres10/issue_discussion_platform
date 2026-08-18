# Supabase Auth proposal

## Recommendation

Use Supabase Auth with email and password as the identity layer for protected staff surfaces. The first version should ship a default login page at `/login`, sign researchers and operators in with email and password, and keep the staff session in the standard `@supabase/ssr` browser session.

The standard `@supabase/ssr` flow is not HTTP-only. Application JavaScript in the browser can access the session cookies. Treat that as the current contract. Require a strict content security policy, few third-party scripts, short sessions, and multifactor authentication for staff. Require recent authentication for transcript export, role changes, and deletion.

A later option is a server-only backend for frontend session with HTTP-only cookies and no Supabase browser client in application JavaScript. The later option is not the current contract.

Study participants should not create accounts to run a discussion. They open an assigned invitation link, exchange it for a participant capability, complete the introduction and audio check, and enter the conversation. Staff authentication belongs on researcher, operator, and later admin routes, where transcript review, session configuration, and study controls must stay behind a signed-in user.

The proposal covers Auth setup and the login flow. Postgres schema, RLS for study tables, and a full researcher dashboard can follow once identity is in place. Study Postgres remains the authoritative store for sessions and transcripts even if some tables later move.

## Component boundaries

Named components are:

* **Study API.** Enforces participant and researcher commands, including staff authorization after JWT verification.
* **Study Postgres.** Stores authoritative study records, including `study_id` on sessions, snapshots, exports, and audit records.
* **Railway.** Hosts the Study API and any worker.
* **LangSmith.** Stores a derived operational projection.
* **Supabase Auth.** Proves staff identity and staff sessions.

Supabase Auth must not own participant link access. Supabase Auth must not make Study API authorization decisions by itself. The service role key stays off the UI. Put only the project URL and publishable key in `NEXT_PUBLIC_` environment variables. The service role key stays on Railway or other trusted servers. Never ship the service role key to Vercel browser bundles.

## Design principles

### Keep participant access separate from staff identity

Participant routes under `/session` remain outside Supabase Auth. The participant UI exchanges a unique invitation token for a short-lived participant capability (HTTP-only cookie). Login protects `/login` destinations such as `/app` or later `/research` routes. Do not force a participant through email and password before a study session.

### Prefer a simple email and password login

The first login page should ask only for email and password, with clear error text and a single submit action. Do not add OAuth, magic links, phone auth, or anonymous sign-in in the first build.

### Use the standard browser session in Next.js

The Vercel UI should use `@supabase/supabase-js` and `@supabase/ssr`. Browser and server clients share the same browser-managed session cookies. Refresh the session in Next.js Proxy or middleware so Server Components see a current token. Document for operators that those cookies are readable by script on the app origin, so CSP and a small script surface are required.

### Verify identity with claims, not cookie shape alone

When protecting a page or server action, call `supabase.auth.getClaims()` (or `getUser()` when a fresh Auth server lookup is required). Do not authorize from `getSession()` user fields alone in server code. Cookies can be present without a valid token.

### Authorize by study membership, not a global role alone

A global `researcher` role is not enough. Every staff object lookup and export must include `study_id` and current membership. Deny by default. Grant named actions by role within a study, including session creation, transcript reading, export, correction, deletion, and study configuration.

If v1 is a single study, state that invariant and still keep `study_id` on sessions, configuration snapshots, exports, and audit records.

### Invite accounts. Do not open public signup

For the first version, create researcher accounts in the Supabase dashboard or through a controlled admin path. The public UI should expose login, not self-service signup. Public signup can be disabled in Auth settings until the study team wants a controlled invite flow.

## Who authenticates

| Actor | How they enter | Auth requirement |
| --- | --- | --- |
| Study participant | Unique invitation token, then `/session` after exchange | Participant capability cookie. No Supabase login |
| Researcher / operator | `/login` with email and password | Supabase Auth JWT, then study-scoped membership on the Study API |
| Backend services | Railway service credentials | Not end-user Auth |

Participant routes stay on the capability contract described in the UI proposal. Staff JWTs never replace that capability on participant routes.

## Login journey

### Open the login page

The user visits `/login`. If they already have a valid session, redirect them to the default authenticated home, such as `/app`.

### Enter email and password

The page shows:

* Study or product name
* Short line that this area is for study staff
* Email field
* Password field
* Sign in button
* Optional forgot password link once reset is enabled

The page should not offer create account, social login, or guest mode.

### Sign in

The client calls `signInWithPassword` with the submitted email and password. On success, Supabase writes the browser-managed session cookies and the app redirects to `/app`. On failure, show a generic invalid credentials message. Avoid revealing whether the email exists.

### Land in the authenticated area

`/app` is a minimal protected page for the first Auth slice. It can show the signed-in email and a sign out control. Researcher tools can replace this shell later without changing the login contract.

### Sign out

Sign out clears the Supabase session cookies and returns the user to `/login`.

### Recover from an expired session

If a protected route finds no valid claims, redirect to `/login` with a safe return path. After login, send the user back to the requested page when that page is an allowlisted internal path.

## How Auth fits the architecture

```text
Researcher browser
  |  /login email + password
  v
Vercel Next.js UI
  |  @supabase/ssr browser-managed session
  |  getClaims() on protected routes
  v
Supabase Auth
  users, sessions, password hashes, email delivery

Staff call to Study API
  |  verified Supabase JWT
  |  study_id membership check, deny by default
  v
Study API on Railway
  |  reads and writes Study Postgres
  v
Study Postgres
  authoritative sessions, transcripts, audit records

Participant browser
  |  invitation token exchange, then /session
  |  participant capability cookie, not a staff JWT
  v
Vercel UI + Study API
```

Study Postgres is the study system of record for sessions and transcripts. Railway hosts the Study API. Supabase Auth proves who the researcher is. When the Study API needs to trust a researcher call, it should verify the Supabase JWT rather than trusting a browser-supplied user id string, then check study membership for the requested `study_id`.

## Implementation steps

### Create or select the Supabase project

1. Create a Supabase project for this application, or reuse an existing project if the team already has one for this study.
2. Note the project URL and publishable key from the project Connect dialog.
3. Confirm Auth is available and email provider settings are visible under Authentication.

### Configure email and password Auth

1. Keep Email enabled under Auth providers.
2. Disable public signup for the first release, or leave signup enabled only for local development.
3. Decide whether email confirmation is required before first login.
   * Hosted projects often require confirmation by default.
   * For invite-created researcher accounts, confirmation may still be needed unless the account is created already confirmed through the admin API.
4. Set Site URL to the Vercel app URL, and add local `http://localhost:3000` plus production and preview redirect URLs under Auth URL configuration.
5. Set a minimum password length that matches research and campus security expectations.
6. Enable multifactor authentication for staff before production transcript access.

### Create the first researcher users

1. Create one or more staff accounts in the Supabase dashboard Auth users view, or through the admin create-user API from a trusted environment.
2. Store temporary passwords through the team's secret process, not in git.
3. Confirm each account can sign in before wiring protected researcher tools.
4. Record study membership for each user, including `study_id`, even when v1 has only one study.

### Add Supabase packages to the UI

In `ui/`:

```bash
npm install @supabase/supabase-js @supabase/ssr
```

Pin versions and commit the lockfile.

### Add environment variables

In local `.env.local` and Vercel project settings:

```bash
NEXT_PUBLIC_SUPABASE_URL=<project-url>
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<publishable-key>
```

Do not add the service role key to the Next.js app.

### Create browser and server Supabase clients

Add utility clients under `ui/src/lib/supabase/`:

* `client.ts` for Client Components with `createBrowserClient`
* `server.ts` for Server Components, Server Actions, and Route Handlers with `createServerClient` and Next.js cookies
* Shared env helpers that fail clearly when URL or publishable key is missing

Use a new client per server request. Reuse the browser singleton pattern provided by `createBrowserClient`.

### Refresh sessions in Next.js Proxy or middleware

Add the Supabase session refresh layer recommended for App Router SSR:

1. Read cookies from the request.
2. Create a server Supabase client.
3. Call `getClaims()` so expired tokens refresh when possible.
4. Write refreshed cookies onto the request and response.
5. Apply cache headers from the cookie write path so CDNs do not cache authenticated responses.

Match the matcher so static assets are skipped. Protect only staff routes that need Auth awareness. Do not require Supabase cookies on `/session`.

### Build the default login page

Add:

```text
/login
  Default email and password login page
```

The page should:

* Use the existing calm visual style from the UI proposal
* Stay centered and narrow, similar to participant frames
* Submit through a Client Component or Server Action that calls `signInWithPassword`
* Disable the submit button while the request is in flight
* Show field validation for empty email or password
* Redirect authenticated users away from `/login`

Example sign-in call:

```ts
const { error } = await supabase.auth.signInWithPassword({
  email,
  password,
});
```

### Add a protected post-login home

Add:

```text
/app
  Authenticated landing page after login
```

On load:

1. Create the server Supabase client.
2. Call `getClaims()`.
3. If claims are missing or invalid, redirect to `/login`.
4. If valid, render the signed-in email and a sign out control.

Keep `/session/*` public to Supabase Auth so participants are unaffected. Participant access still requires a valid capability from the Study API.

### Add sign out

Provide a Server Action or route handler that:

1. Creates the server Supabase client.
2. Calls `supabase.auth.signOut()`.
3. Redirects to `/login`.

### Protect future researcher routes by convention

Use a route group such as:

```text
src/app/
  login/page.tsx
  app/page.tsx
  (protected)/
    research/
      ...
  session/
    ...
```

Every protected layout should re-check claims on the server. Proxy or middleware can redirect early, but page-level verification remains required.

### Optional password reset

After login works, add:

1. `/login/forgot-password` to collect email and call `resetPasswordForEmail`
2. `/login/update-password` for the authenticated password update after the email link
3. Redirect URL allowlisting for the update page

Password reset can wait until after the first login review if the team can rotate passwords in the dashboard for a small staff set.

### Verify before researcher tooling

Confirm:

* A researcher can sign in with email and password.
* `/app` rejects signed-out users.
* `/login` redirects signed-in users to `/app`.
* Sign out returns the user to `/login` and blocks `/app`.
* Participant `/session` pages still load without Supabase Auth.
* Preview and production Site URL and redirect URL settings work on Vercel.
* The service role key is absent from Vercel env for the UI.

## Suggested UI structure

```text
ui/src/
  app/
    login/
      page.tsx
      login-form.tsx
    app/
      page.tsx
      sign-out-button.tsx
    session/
      ...
  lib/
    supabase/
      client.ts
      server.ts
      middleware.ts
    auth/
      redirect.ts
  components/
    auth/
      login-form.tsx
```

Names can follow the repo conventions once implementation starts. The important split is public participant routes versus authenticated staff routes.

## Backend relationship

For the first Auth slice under Sample contracts, the Study API does not need to verify researcher JWTs. The login page and `/app` shell live entirely in the Next.js app against Supabase Auth.

When researcher APIs appear on the Study API:

1. The Next.js UI server reads the staff session with `@supabase/ssr` and forwards the access token in the `Authorization` header to the Study API. Application JavaScript does not call staff Study API routes with a raw token.
2. The Study API verifies the JWT with the Supabase JWT secret or JWKS.
3. The Study API authorizes by `sub`, server-controlled `app_metadata` claims, and current study membership for the requested `study_id`, never by editable `user_metadata`.
4. Deny by default. A staff member cannot read a session outside current study membership.

Staff actions by role, deny by default:

| Action | operator | researcher | study_admin |
| --- | --- | --- | --- |
| Create invitation and session | no | no | yes |
| Read transcript for current `study_id` | yes | yes | yes |
| Export transcript | no | yes, with recent auth | yes, with recent auth |
| Create a correction revision | no | yes | yes |
| Delete or tombstone | no | no | yes, with recent auth |
| Publish a configuration snapshot | no | no | yes |
| Transfer a writer lease | no | no | yes |

Store authorization fields such as `role: "researcher"` in `app_metadata`, not `user_metadata`. Pair the role with membership rows that name `study_id`.

Require a recent authentication timestamp before transcript export, role changes, and deletion.

## Shared milestones

Named shared milestones replace numbered phases that meant different work in each document.

### Sample contracts

* Supabase project Auth configuration
* Email and password login page at `/login`
* Standard `@supabase/ssr` browser session, documented as script-readable on the app origin
* Session refresh Proxy or middleware
* Protected `/app` landing page
* Sign out
* Invite-created staff users
* Verification that participant session routes remain outside Supabase Auth
* CSP, few third-party scripts, and short session lifetime documented as required controls

Former Auth Phase 1 (login and protected shell) maps to Sample contracts.

### Durable record

* Researcher role in `app_metadata` plus study membership with `study_id`
* Study API JWT verification for researcher APIs
* Deny-by-default object checks on every session, snapshot, and audit lookup
* Single-study v1 invariant stated in config while `study_id` remains on every record
* Recent authentication required for role changes

Former Auth Phase 2 staff metadata and former Auth Phase 3 JWT verification map to Durable record.

### Voice control

Staff Auth does not mint Realtime credentials. Voice setup stays on the participant capability path. Staff routes must not expose OpenAI keys or participant capability cookies.

### Approved tracing

Staff identity is required before anyone reads derived traces. Membership still limits which `study_id` traces a researcher may see. Tracing remains disabled until an approved policy version exists.

### Research export

* Protected research routes for session lists, transcript review, and configuration
* Recent authentication for transcript export and deletion
* RLS policies that use `auth.uid()` only where Supabase-hosted tables need row ownership
* Explicit decision that participant-facing account model is not required
* Optional later move to a server-only BFF session if the team wants HTTP-only staff cookies

Former Auth Phase 2 account recovery and former Auth Phase 3 researcher product surfaces map to Research export, except JWT verification which maps to Durable record.

Forgot password and update password pages, optional allowlisted email domains, and audit of redirect URLs for preview deployments can ship with Sample contracts or Research export depending on staff size.

## Security controls

* Enable RLS on every table exposed through the Supabase Data API before those tables hold study data.
* Never authorize from `user_metadata`.
* Prefer publishable keys in the browser. Keep service role keys on trusted servers.
* Keep JWT lifetime short for a research staff app. Shorter expiry reduces risk after a laptop is left unlocked.
* Sign out or revoke sessions before deleting a user if immediate lockout matters.
* Do not cache authenticated HTML or JSON at the CDN edge.
* Log Auth failures without storing raw passwords.
* Use CSP and a small set of third-party scripts because staff session cookies are not HTTP-only under the current contract.
* Require MFA for staff before production access to transcripts.
* Require recent authentication for transcript export, role changes, and deletion.

## Decisions needed before implementation

The study team should decide:

1. Whether Auth is staff-only for the first release, or whether any participant account model is required later. The default is staff-only.
2. Whether public signup stays disabled permanently in favor of invites.
3. Whether email confirmation is required for staff accounts.
4. Which email domains are allowed for researchers.
5. What the post-login home should be after `/app` is replaced by research tools.
6. Whether password reset is required under Sample contracts or can wait for Research export.
7. Whether the Study API must verify Supabase JWTs in the same milestone as login, or only when researcher APIs ship under Durable record.
8. Whether preview deployments each need Auth redirect URL entries.
9. The membership model for `study_id` when v1 is a single study.
10. When MFA becomes mandatory relative to first transcript export.

## Initial scope

The first Auth build under Sample contracts should include the Supabase email and password provider configuration, Next.js SSR clients, session refresh, `/login`, protected `/app`, sign out, and invite-created researcher users.

The first build should exclude OAuth providers, magic links, phone auth, anonymous Auth, public signup UI, researcher dashboards, Postgres study schema, RLS policies for transcripts, Study API JWT verification, and a server-only BFF staff session. The excluded work can follow once the login path is stable.
