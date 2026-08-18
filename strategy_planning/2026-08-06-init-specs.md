# Initial specs

The person in the study should be able to have a conversation with an AI agent. The UI can stay deliberately simple.

Hosting and services:

* UI on Vercel
* Study API on Railway
* Study Postgres as the authoritative store
* OpenAI Realtime for voice
* LangSmith for derived telemetry
* Supabase Auth for staff identity only

Shared milestones across the later proposals:

1. Sample contracts. Ship a UI look with frozen participant routes and sample data.
2. Durable record. Introduce the Study API and Study Postgres, and wire the conversation.
3. Voice control. Use server-mediated Realtime setup and a sideband worker.
4. Approved tracing. Connect LangSmith as a best-effort derived projection of approved fields from committed records.
5. Research export. Ship versioned exports from Study Postgres.

The first LangSmith integration records transcript text, voice configuration, interruption state, and approved timing and usage fields. It does not record raw audio. "Voice" means approved configuration and metrics, not raw audio files.

Later proposals define the contracts. Read `ui_proposal_2026_08_06.md` for the participant journey and participant API mapping. Read `supabase_auth_proposal_2026_08_05.md` for staff login. Read the backend and LangSmith proposals for capability cookies, canonical turns, completion, and tracing.
