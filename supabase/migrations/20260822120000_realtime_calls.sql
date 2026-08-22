-- Realtime call records for server-mediated OpenAI Realtime setup.

CREATE TABLE realtime_calls (
    realtime_call_id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions (session_id) ON DELETE CASCADE,
    openai_call_id TEXT NOT NULL,
    capability_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    expires_at TIMESTAMPTZ NOT NULL,
    invalidated_at TIMESTAMPTZ,
    control_handoff_enqueued_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT realtime_calls_openai_call_id_unique UNIQUE (openai_call_id),
    CONSTRAINT realtime_calls_status_check CHECK (
        status IN ('active', 'invalidated', 'ended')
    )
);

CREATE INDEX realtime_calls_session_id_idx ON realtime_calls (session_id);

CREATE UNIQUE INDEX realtime_calls_session_active_unique
    ON realtime_calls (session_id)
    WHERE status = 'active';

ALTER TABLE realtime_calls ENABLE ROW LEVEL SECURITY;

CREATE POLICY realtime_calls_deny_api ON realtime_calls
    FOR ALL USING (false);
