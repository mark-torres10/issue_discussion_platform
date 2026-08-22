-- LangSmith trace run id persistence (Step 7).

CREATE TABLE trace_runs (
    trace_run_id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions (session_id) ON DELETE CASCADE,
    export_kind TEXT NOT NULL,
    langsmith_root_run_id UUID NOT NULL,
    canonical_turn_id UUID,
    trace_kind TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT trace_runs_export_kind_check CHECK (
        export_kind IN ('conversation_turn', 'session_lifecycle', 'connection_failure')
    )
);

CREATE UNIQUE INDEX trace_runs_canonical_turn_export_unique
    ON trace_runs (canonical_turn_id, export_kind)
    WHERE canonical_turn_id IS NOT NULL;

CREATE INDEX trace_runs_session_id_idx ON trace_runs (session_id);

ALTER TABLE trace_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY trace_runs_deny_api ON trace_runs
    FOR ALL USING (false);
