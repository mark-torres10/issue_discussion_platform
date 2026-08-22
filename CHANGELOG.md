# CHANGELOG

## 2026-08-22

1. Participants can complete study sessions through a FastAPI Study API wired to the Next.js UI, with signed invite cookies and CSRF on writes and Postgres or in-memory storage depending on environment. Server-side OpenAI handles text replies and voice realtime, staff can export sessions with a Supabase JWT, and LangSmith tracing stays off by default. [PR #10](https://github.com/mark-torres10/issue_discussion_platform/pull/10)

## 2026-08-14

1. Moved participant UI wording into editable YAML (`ui/content/ui-copy.yaml` and the sample session file) so researchers can change study copy without editing React components; screens load the same text through a server loader and shared context. [PR #3](https://github.com/mark-torres10/issue_discussion_platform/pull/3)

## 2026-08-06

1. Shipped the Phase 1–2 participant conversation UI in `ui/`: introduction, audio check, text/voice discussion with mocked streaming replies, completion and unavailable states, plus journey screenshots for study-flow review. [PR #1](https://github.com/mark-torres10/issue_discussion_platform/pull/1)
