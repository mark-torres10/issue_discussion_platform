# Initial specs

The person in the study should be able to have a conversation with an AI agent. The UI can stay deliberately simple.

The work is a short three-part build. First, ship a UI look with no live backend. Next, introduce the Study API and wire the conversation. Then connect telemetry so operators can review approved fields from committed records.

Hosting and services:

* UI on Vercel
* Study API on Railway
* Study Postgres as the authoritative store
* OpenAI Realtime for voice
* LangSmith for derived telemetry
* Supabase Auth for staff identity only

The first LangSmith integration records transcript text, voice configuration, interruption state, and approved timing and usage fields. It does not record raw audio. "Voice" means approved configuration and metrics, not raw audio files.

Later proposals define the contracts. Read `ui_proposal_2026_08_06.md` for the participant journey and participant API mapping. Read `supabase_auth_proposal_2026_08_05.md` for staff login. Read the backend and LangSmith proposals for capability cookies, canonical turns, completion, and tracing.

Shared milestones across those documents are Sample contracts, Durable record, Voice control, Approved tracing, and Research export.
