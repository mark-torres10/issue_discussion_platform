-- Generation operations for server-mediated text generation (Step 5).

CREATE TABLE generation_operations (
    operation_id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions (session_id) ON DELETE CASCADE,
    idempotency_scope TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    participant_turn_id UUID,
    ai_turn_id UUID,
    model_name TEXT NOT NULL,
    error_code TEXT,
    error_message TEXT,
    response_body JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT generation_operations_status_check CHECK (
        status IN ('accepted', 'running', 'succeeded', 'failed')
    ),
    CONSTRAINT generation_operations_session_idempotency_unique UNIQUE (
        session_id, idempotency_scope, idempotency_key
    )
);

CREATE INDEX generation_operations_session_id_idx ON generation_operations (session_id);

ALTER TABLE generation_operations ENABLE ROW LEVEL SECURITY;

CREATE POLICY generation_operations_deny_api ON generation_operations
    FOR ALL USING (false);
