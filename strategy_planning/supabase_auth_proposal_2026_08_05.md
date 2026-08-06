# Supabase Auth proposal

## Recommendation

Use Supabase Auth with email and password as the identity layer for protected application surfaces. The first version should ship a default login page at `/login`, sign researchers and operators in with email and password, keep the session in HTTP-only cookies through `@supabase/ssr`, and leave the public participant study journey on unique session links without a login step.

Study participants should not create accounts to run a discussion. They open an assigned session link, complete the introduction and audio check, and enter the conversation. Authentication belongs on researcher, operator, and later admin routes, where transcript review, session configuration, and study controls must stay behind a signed-in user.

This proposal covers Auth setup and the login flow only. Postgres schema, RLS for study tables, and a full researcher dashboard can follow once identity is in place.

## Design principles

### Keep participant access separate from researcher identity

Participant routes under `/session/[sessionId]` remain link based. Login protects `/login` destinations such as `/app` or later `/research` routes. Do not force a participant through email and password before a study session.

### Prefer a simple email and password login

The first login page should ask only for email and password, with clear error text and a single submit action. Do not add OAuth, magic links, phone auth, or anonymous sign-in in the first build.

### Use cookie based SSR sessions in Next.js

The Vercel UI should use `@supabase/supabase-js` and `@supabase/ssr`. Browser and server clients should share the same cookie session. Refresh the session in Next.js Proxy or middleware so Server Components see a current token.

### Verify identity with claims, not cookie shape alone

When protecting a page or server action, call `supabase.auth.getClaims()` (or `getUser()` when a fresh Auth server lookup is required). Do not authorize from `getSession()` user fields alone in server code. Cookies can be present without a valid token.

### Invite accounts. Do not open public signup

For the first version, create researcher accounts in the Supabase dashboard or through a controlled admin path. The public UI should expose login, not self-service signup. Public signup can be disabled in Auth settings until the study team wants a controlled invite flow.

### Keep secrets off the client

Put only the project URL and publishable key in `NEXT_PUBLIC_` environment variables. The service role key stays on Railway or other trusted servers. Never ship the service role key to Vercel browser bundles.

## Who authenticates

| Actor | How they enter | Auth requirement |
| --- | --- | --- |
| Study participant | Unique `/session/[sessionId]` link | No Supabase login |
| Researcher / operator | `/login` with email and password | Required |
| Backend services | Railway service credentials | Not end-user Auth |

Later phases can attach researcher identity to session creation, transcript exports, or admin APIs. Phase 1 only needs a working login and a protected post-login landing page.

## Login journey

### 1. Open the login page

The user visits `/login`. If they already have a valid session, redirect them to the default authenticated home, such as `/app`.

### 2. Enter email and password

The page shows:

* Study or product name
* Short line that this area is for study staff
* Email field
* Password field
* Sign in button
* Optional forgot password link once reset is enabled

The page should not offer create account, social login, or guest mode.

### 3. Sign in

The client calls `signInWithPassword` with the submitted email and password. On success, Supabase writes the session cookies and the app redirects to `/app`. On failure, show a generic invalid credentials message. Avoid revealing whether the email exists.

### 4. Land in the authenticated area

`/app` is a minimal protected page for the first Auth slice. It can show the signed-in email and a sign out control. Researcher tools can replace this shell later without changing the login contract.

### 5. Sign out

Sign out clears the Supabase session cookies and returns the user to `/login`.

### 6. Recover from an expired session

If a protected route finds no valid claims, redirect to `/login` with a safe return path. After login, send the user back to the requested page when that page is an allowlisted internal path.

## How Auth fits the architecture

```text
Researcher browser
  |  /login email + password
  v
Vercel Next.js UI
  |  @supabase/ssr cookie session
  |  getClaims() on protected routes
  v
Supabase Auth
  users, sessions, password hashes, email delivery

Participant browser
  |  /session/[sessionId] (no login)
  v
Vercel UI + Railway study API
```

Railway remains the study system of record for sessions and transcripts. Supabase Auth proves who the researcher is. When Railway later needs to trust a researcher call, it should verify the Supabase JWT rather than trusting a browser-supplied user id string.

## Implementation steps

### Step 1. Create or select the Supabase project

1. Create a Supabase project for this application, or reuse an existing project if the team already has one for this study.
2. Note the project URL and publishable key from the project Connect dialog.
3. Confirm Auth is available and email provider settings are visible under Authentication.

### Step 2. Configure email and password Auth

1. Keep Email enabled under Auth providers.
2. Disable public signup for the first release, or leave signup enabled only for local development.
3. Decide whether email confirmation is required before first login.
   * Hosted projects often require confirmation by default.
   * For invite-created researcher accounts, confirmation may still be needed unless the account is created already confirmed through the admin API.
4. Set Site URL to the Vercel app URL, and add local `http://localhost:3000` plus production and preview redirect URLs under Auth URL configuration.
5. Set a minimum password length that matches research and campus security expectations.

### Step 3. Create the first researcher users

1. Create one or more staff accounts in the Supabase dashboard Auth users view, or through the admin create-user API from a trusted environment.
2. Store temporary passwords through the team's secret process, not in git.
3. Confirm each account can sign in before wiring protected researcher tools.

### Step 4. Add Supabase packages to the UI

In `ui/`:

```bash
npm install @supabase/supabase-js @supabase/ssr
```

Pin versions and commit the lockfile.

### Step 5. Add environment variables

In local `.env.local` and Vercel project settings:

```bash
NEXT_PUBLIC_SUPABASE_URL=<project-url>
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=<publishable-key>
```

Do not add the service role key to the Next.js app unless a specific server-only admin path requires it, and even then keep it off `NEXT_PUBLIC_`.

### Step 6. Create browser and server Supabase clients

Add utility clients under `ui/src/lib/supabase/`:

* `client.ts` for Client Components with `createBrowserClient`
* `server.ts` for Server Components, Server Actions, and Route Handlers with `createServerClient` and Next.js cookies
* Shared env helpers that fail clearly when URL or publishable key is missing

Use a new client per server request. Reuse the browser singleton pattern provided by `createBrowserClient`.

### Step 7. Refresh sessions in Next.js Proxy or middleware

Add the Supabase session refresh layer recommended for App Router SSR:

1. Read cookies from the request.
2. Create a server Supabase client.
3. Call `getClaims()` so expired tokens refresh when possible.
4. Write refreshed cookies onto the request and response.
5. Apply cache headers from the cookie write path so CDNs do not cache authenticated responses.

Match the matcher so static assets are skipped. Protect only routes that need Auth awareness.

### Step 8. Build the default login page

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

### Step 9. Add a protected post-login home

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

Keep `/session/*` public so participants are unaffected.

### Step 10. Add sign out

Provide a Server Action or route handler that:

1. Creates the server Supabase client.
2. Calls `supabase.auth.signOut()`.
3. Redirects to `/login`.

### Step 11. Protect future researcher routes by convention

Use a route group such as:

```text
src/app/
  login/page.tsx
  app/page.tsx
  (protected)/
    research/
      ...
  session/[sessionId]/
    ...
```

Every protected layout should re-check claims on the server. Proxy or middleware can redirect early, but page-level verification remains required.

### Step 12. Optional password reset

After login works, add:

1. `/login/forgot-password` to collect email and call `resetPasswordForEmail`
2. `/login/update-password` for the authenticated password update after the email link
3. Redirect URL allowlisting for the update page

Password reset can wait until after the first login review if the team can rotate passwords in the dashboard for a small staff set.

### Step 13. Verify before researcher tooling

Confirm:

* A researcher can sign in with email and password.
* `/app` rejects signed-out users.
* `/login` redirects signed-in users to `/app`.
* Sign out returns the user to `/login` and blocks `/app`.
* Participant `/session/[sessionId]` pages still load without Auth.
* Preview and production Site URL and redirect URL settings work on Vercel.

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
      [sessionId]/
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

Names can follow the repo conventions once implementation starts. The important split is public session routes versus authenticated staff routes.

## Backend relationship

For the first Auth slice, Railway does not need to verify researcher JWTs. The login page and `/app` shell live entirely in the Next.js app against Supabase Auth.

When researcher APIs appear on Railway:

1. The browser sends the Supabase access token to Railway, or Railway trusts only server-to-server calls after the UI has already authorized the user.
2. Railway verifies the JWT with Supabase JWT secret or JWKS.
3. Railway authorizes by `sub` and `app_metadata` role claims, never by editable `user_metadata`.

Store authorization fields such as `role: "researcher"` in `app_metadata`, not `user_metadata`.

## Auth prototype phases

### Phase 1. Login and protected shell

* Supabase project Auth configuration
* Email and password login page at `/login`
* Cookie based SSR clients
* Session refresh Proxy or middleware
* Protected `/app` landing page
* Sign out
* Invite-created staff users
* Verification that participant session routes remain public

### Phase 2. Account recovery and staff metadata

* Forgot password and update password pages
* Researcher role in `app_metadata`
* Optional allowlisted email domains
* Audit of redirect URLs for preview deployments

### Phase 3. Authenticated researcher product surfaces

* Protected research routes for session lists, transcript review, and configuration
* Railway JWT verification for researcher APIs
* RLS policies that use `auth.uid()` only where Supabase-hosted tables need row ownership
* Explicit decision on whether any participant-facing account model is ever required

## Security controls

* Enable RLS on every table exposed through the Supabase Data API before those tables hold study data.
* Never authorize from `user_metadata`.
* Prefer publishable keys in the browser. Keep service role keys on trusted servers.
* Keep JWT lifetime appropriate for a research staff app. Shorter expiry reduces risk after a laptop is left unlocked.
* Sign out or revoke sessions before deleting a user if immediate lockout matters.
* Do not cache authenticated HTML or JSON at the CDN edge.
* Log Auth failures without storing raw passwords.

## Decisions needed before implementation

The study team should decide:

1. Whether Auth is staff-only for the first release, or whether any participant account model is required later.
2. Whether public signup stays disabled permanently in favor of invites.
3. Whether email confirmation is required for staff accounts.
4. Which email domains are allowed for researchers.
5. What the post-login home should be after `/app` is replaced by research tools.
6. Whether password reset is required in Phase 1 or can wait for Phase 2.
7. Whether Railway must verify Supabase JWTs in the same milestone as login, or only when researcher APIs ship.
8. Whether preview deployments each need Auth redirect URL entries.

## Initial scope

The first Auth build should include the Supabase email and password provider configuration, Next.js SSR clients, session refresh, `/login`, protected `/app`, sign out, and invite-created researcher users.

The first build should exclude OAuth providers, magic links, phone auth, anonymous Auth, public signup UI, researcher dashboards, Postgres study schema, RLS policies for transcripts, and Railway JWT verification. Those can follow once the login path is stable.
