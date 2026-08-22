# Instructions to the next AI agent: build the backend and LangSmith telemetry

This file is for the **next** Cursor agent that opens this repo. Read it first. Do not skip it.

The human has already put account credentials in **their** environment. You may not have those secrets in this Cloud Agent VM. Use what you have. Do not invent keys. Do not commit secrets.

---

## Who you are

You are the **orchestrator**. You do not implement the whole backend in one agent session by yourself.

Your job:

1. Read the frozen planning contracts (listed below).
2. Write a full implementation plan using the planning skill.
3. **Delegate** each plan slice to **subagents**.
4. Review their diffs, run verification, commit, push, and open or update PRs.

You stay the parent. Subagents do the coding slices. Your operating skill is `.cursor/skills/delegate-work-to-subagents/SKILL.md`.

---

## How to delegate (read this skill first)

**Read and follow** `.cursor/skills/delegate-work-to-subagents/SKILL.md` for the whole job. That is the delegation skill. You are the orchestrator in that file. Do not do research, implementation, QA, verification, or synthesis yourself when a subagent can do it.

Hard rules from that skill (repeat them so you cannot skip the file):

- Only **you** spawn subagents. A subagent must not spawn another subagent.
- Use **Composer 2.5** (`model: composer-2.5`) for every subagent.
- Spawn the named kinds: **research** (`explore` / `docs-researcher`), **implementation** (`generalPurpose`), **QA** (`generalPurpose`, no product-code edits), **verification** (`generalPurpose`, no product-code edits), **integration check** after parallel implementation slices, **status reporting** at checkpoints.
- Make a checklist of units of work. Put a **closed file set** on every implementation slice. Two subagents must not edit the same files. If they would, run those slices in sequence.
- Each Task `prompt` is a complete packet. A subagent cannot see this chat or the checklist. If a step can be misread, rewrite it until it cannot.
- Independent slices: one message, multiple Task calls. Wait when a slice depends on another.
- After a parallel implementation wave: confirm file ownership, then spawn an integration check before more slices or full QA.
- Subagents return an executive summary only (what they did, files, tests, blockers, risks, what to spawn next). You talk to the human. Short checkpoint updates. If you name a subagent, link it as `[Name](id)`.
- One implementation slice includes that slice’s tests. Do not split implementation and tests for the same slice across two subagents.

You still own git: branch names, commits, pushes, PRs. Subagents edit files. You commit unless you explicitly send a slice to an isolated worktree.

Skills you must read and follow (in this order):

0. `.cursor/skills/delegate-work-to-subagents/SKILL.md` — you are this orchestrator for the entire backend build.

1. `.cursor/skills/create-implementation-plan/SKILL.md` — after research, produce `docs/plans/<YYYY-MM-DD>_study-api-langsmith_<hash>/` with `plan.md` plus `steps/stepN.md`. Delegated tasks must be impossible to misread. Exact paths. Exact commands. No “as needed.”
2. `.cursor/skills/implement-plan-and-open-pr/SKILL.md` — the human already asked for **full implementation** of backend + LangSmith telemetry and a shippable result. After the plan exists, execute it to completion and open a PR. Follow `CODING_RULES.md` and `UNIT_TESTING_STANDARDS.md` in that skill folder.
3. `.cursor/skills/implement-from-spec/SKILL.md` — **each** delegated slice. Caller-first, contracts before behavior, tests first, one unit of work. Do not skip phase gates. One packet per Task invocation.
4. `.agents/skills/fastapi/SKILL.md` — Study API code in `backend/`.
5. `.agents/skills/use-railway/SKILL.md` — Railway `api` service. Discover MCP tools with `GetMcpTools` before `CallMcpTool`.
6. `.agents/skills/ecosystem-primer/SKILL.md` **and** LangGraph/LangChain skills **only** if you add an agent graph. The current contracts call for **LangSmith tracing of OpenAI calls**, not a required LangGraph app. Do not add LangGraph unless the plan proves you need it.
7. `.cursor/skills/plain-writing/SKILL.md` for any new participant or staff copy.
8. `.cursor/skills/code-security/SKILL.md` for auth, cookies, SQL, secrets.
9. Vercel / Next.js skills under `.agents/skills/` and plugin skills when you wire `ui/` to the real Study API.

Also follow repo `AGENTS.md`: participant wording lives in `ui/content/`. Runnable app is `ui/`. Python at repo root is lint and tests; FastAPI lives in `backend/`.

---

## What “done” means

**Completely implement** the Study API and LangSmith telemetry so they match the frozen contracts, not a hello-world stub.

Today on `main`:

- `backend/app/main.py` is a health check plus hello JSON.
- Railway hosts that stub at the production `api` service.
- Supabase is the **hosted Postgres and Auth** for this repo (`docs/runbooks/setup/HOW_TO_SETUP_APP.md`).
- Vercel hosts the Next.js UI. Participant routes are still mocked.

You must ship, at minimum:

1. **Study API** (FastAPI) on Railway: invitation cookie session, consent when required, text `POST /v1/participant-session/messages`, voice control plane (SDP in, SDP out; no ephemeral Realtime key in the browser), internal worker ingest for Realtime items, immutable turns, completion in one transaction, 24h completed read then `410`.
2. **Study Postgres** as the system of record. Use the **existing hosted Supabase Postgres** unless you write a plan that justifies a second database and the human approves it. Do not assume Railway Postgres; that language in older drafts is superseded by the setup runbook.
3. **LangSmith**: one `conversation_turn` root per AI generation; `telemetry_thread_id` as UUID v7 created at invitation; true best-effort export; `TRACE_EXPORT_ENABLED=false` until a written policy says otherwise. Opening snapshot is **not** a generation trace. Never send `session_id`, invitation tokens, or participant capability cookies to LangSmith.
4. **UI wiring** for the participant path so the browser talks to the Study API contracts (not `/turns` upsert, not client-created AI/system turns). Staff JWT stays on the UI server.
5. **Tests** that lock the contracts (authz, immutability, completion transaction, no public turn insert, trace payload shape, consent).
6. **Deploy** the API to the existing Railway service and document env vars without putting secret values in git.

Out of scope unless the human expands the ask: a full staff admin product, raw audio storage, client-side LangSmith, making the opening snapshot a traced generation.

---

## Planning inputs (read all of these before writing the plan)

Frozen contracts (after the planning PR merged to `main`):

- `strategy_planning/backend_proposal_2026_08_06.md`
- `strategy_planning/langsmith_proposal_2026_08_06.md`
- `strategy_planning/ui_proposal_2026_08_06.md`
- `strategy_planning/supabase_auth_proposal_2026_08_05.md`
- `strategy_planning/2026-08-06-init-specs.md`
- `strategy_planning/CREDENTIALS_AND_SETUP.md`
- `strategy_planning/SUGGESTED_REVISIONS.md` (review record; proposals were already updated)

Hosted reality:

- `docs/runbooks/setup/HOW_TO_SETUP_APP.md`
- `docs/runbooks/HOW_TO_RUN_APP.md`

If a planning sentence conflicts with the setup runbook on **where Postgres lives**, the setup runbook wins: **Supabase is the hosted database**.

Shared milestones the plan must cover: Sample contracts, Durable record, Voice control, Approved tracing, Research export. Order them by dependency. Do not start LangSmith export until turns exist. Do not enable `TRACE_EXPORT_ENABLED` in production without a written retention policy.

---

## Orchestrator workflow (follow this)

### Phase A — Plan (research + planning subagents; you review)

Spawn a **research** subagent first to read the contracts and the hosted runbooks and to list open design choices. If research finds a blocking choice, stop and ask the human. Do not let an implementation subagent guess.

Spawn a **generalPurpose** subagent to follow `create-implementation-plan` and write the plan package under `docs/plans/`. You review every sentence of the packets. Spawn a **status reporting** subagent after research finishes.

`plan.md` stays high level (no code identifiers). Each `steps/stepN.md` is a **subagent packet**: files, contracts, tests, commands, out of scope.

Suggested slice split (adjust only if the plan skill requires a different cut; keep packets non-overlapping):

1. Implementation plan package (if you have a subagent write it, you still review every sentence).
2. FastAPI app layout, Pydantic contracts, error model, auth middleware (invitation cookie + staff JWT forward), OpenAPI.
3. Supabase/Postgres schema, migrations, repositories, invitation hash, capability cookies, RLS or API-only DB role.
4. Participant lifecycle: start session, consent endpoint, text generation path, immutable turns, completion transaction, completed read/`410`.
5. OpenAI text integration (server-only key).
6. Voice: session minting, Realtime SDP proxy, sideband, `POST /internal/v1/realtime/calls/{openai_call_id}/items`, worker auth.
7. LangSmith export worker, `conversation_turn` tree, UUID v7 thread id, payload denylist, `TRACE_EXPORT_ENABLED`.
8. Next.js participant UI: replace mock session with Study API; keep copy in `ui/content/`.
9. Tests, Railway env (no secrets in git), deploy, smoke `/health` and one authenticated contract path.

Commit the plan on a feature branch. Push. Then implement.

### Phase B — Implement via subagents

Stay in the delegate-work-to-subagents loop.

For each step file:

1. Give the implementation subagent `implement-from-spec` plus the **full text** of that step, the closed file set, and the relevant contract quotes.
2. That same subagent adds or updates tests for the slice.
3. Spawn **QA** (no product-code edits) after slices land. Spawn **verification** for UI or live API paths when those exist.
4. After parallel slices, spawn an **integration check**, then commit and push on the working branch.

Do not start the next dependent slice until the previous slice’s contracts exist.

### Phase C — PR and verify

Follow `implement-plan-and-open-pr`. Open a PR for the implementation (not this planning-only history). Return the PR URL to the human.

If Railway/Vercel/Supabase CLIs are missing in the Cloud Agent, say so and use the human’s environment, runbooks, and MCP servers that **are** authenticated. Do not block forever on CLIs you cannot install.

---

## Hard rules (do not violate)

- No public `POST /turns`. Browser cannot create `ai` or `system` turns.
- `session_id` is internal. Public URLs use invitation tokens. Cookies are HTTP-only capability cookies.
- Staff: `@supabase/ssr` is **not** HTTP-only. UI server forwards JWT. Study API authorizes study-scoped membership. Deny by default.
- Mic permission is not consent. Consent is `POST /v1/participant-session/consent` when the protocol requires it.
- No raw audio in Study Postgres or LangSmith.
- LangSmith is derived, best-effort, never the system of record.
- Do not log invitation tokens, cookies, or OpenAI/LangSmith keys.
- Do not put `.env` secret values in the repo.

---

## If you are tempted to code it all yourself

Stop. Open `.cursor/skills/delegate-work-to-subagents/SKILL.md`. Spawn subagents. Your job is routing, contract enforcement, git, and talking to the human.
