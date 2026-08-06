# Initial specs

What we want is for our person to be able to have a conversation with an AI agent. I'm thinking that the UI can actually be pretty deliberately simple.

We'll do a UI build first and make it a no-op for now. We'll just get a look at how the interface can look, then we'll introduce the backend and wire everything together, and then we'll have some conversations. I'll then connect this to Langsmith to allow us to track the transcripts and the voices. That should be a three-part build.

UI: Vercel
Backend: Railway
AI: OpenAI GPT-live
Telemetry: LangSmith
