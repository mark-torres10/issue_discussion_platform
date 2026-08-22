-- Study API core schema for Supabase-hosted Postgres.
-- The Study API connects with a direct connection string and API-only role.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- Configuration snapshots (immutable once published)
-- ---------------------------------------------------------------------------

CREATE TABLE configuration_snapshots (
    configuration_snapshot_id UUID PRIMARY KEY,
    study_id UUID NOT NULL,
    study_wave TEXT NOT NULL,
    protocol_version TEXT NOT NULL,
    issue_version TEXT NOT NULL,
    persona_version TEXT NOT NULL,
    prompt_content_hash TEXT NOT NULL,
    prompt_object_reference TEXT NOT NULL,
    opening_display_text TEXT NOT NULL,
    ai_speaks_first BOOLEAN NOT NULL DEFAULT TRUE,
    model_provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_parameters_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    voice_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    tool_manifest_hash TEXT NOT NULL,
    safety_policy_version TEXT NOT NULL,
    assignment_seed_reference TEXT NOT NULL,
    application_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Invitations (token hash only; never store raw token)
-- ---------------------------------------------------------------------------

CREATE TABLE invitations (
    invitation_id UUID PRIMARY KEY,
    study_id UUID NOT NULL,
    session_id UUID NOT NULL,
    token_hash TEXT NOT NULL,
    telemetry_thread_id UUID NOT NULL,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT invitations_token_hash_unique UNIQUE (token_hash),
    CONSTRAINT invitations_telemetry_thread_id_unique UNIQUE (telemetry_thread_id)
);

CREATE INDEX invitations_session_id_idx ON invitations (session_id);

-- ---------------------------------------------------------------------------
-- Sessions
-- ---------------------------------------------------------------------------

CREATE TABLE sessions (
    session_id UUID PRIMARY KEY,
    study_id UUID NOT NULL,
    participant_capability_hash TEXT NOT NULL DEFAULT '',
    telemetry_thread_id UUID NOT NULL,
    status TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    writer_lease_id UUID,
    writer_lease_expires_at TIMESTAMPTZ,
    configuration_snapshot_id UUID NOT NULL REFERENCES configuration_snapshots (
        configuration_snapshot_id
    ),
    consent_version TEXT,
    consented_at TIMESTAMPTZ,
    consent_profile TEXT,
    consent_withdrawn_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    completion_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT sessions_telemetry_thread_id_unique UNIQUE (telemetry_thread_id),
    CONSTRAINT sessions_status_check CHECK (
        status IN ('pending', 'active', 'paused', 'completed', 'expired')
    ),
    CONSTRAINT sessions_version_positive CHECK (version >= 1)
);

CREATE INDEX sessions_study_id_idx ON sessions (study_id);
CREATE INDEX sessions_status_idx ON sessions (status);

-- ---------------------------------------------------------------------------
-- Canonical turns
-- ---------------------------------------------------------------------------

CREATE TABLE canonical_turns (
    turn_id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions (session_id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    speaker TEXT NOT NULL,
    origin TEXT NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'verified',
    provider_item_id TEXT,
    provider_response_id TEXT,
    client_event_id UUID,
    source_mode TEXT NOT NULL,
    generated_text TEXT,
    delivered_text TEXT,
    display_text TEXT NOT NULL,
    interrupted BOOLEAN NOT NULL DEFAULT FALSE,
    content_hash TEXT NOT NULL,
    provider_created_at TIMESTAMPTZ,
    client_observed_at TIMESTAMPTZ,
    recorded_at TIMESTAMPTZ NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    CONSTRAINT canonical_turns_speaker_check CHECK (
        speaker IN ('participant', 'ai', 'system')
    ),
    CONSTRAINT canonical_turns_session_ordinal_unique UNIQUE (session_id, ordinal),
    CONSTRAINT canonical_turns_session_client_event_unique UNIQUE (session_id, client_event_id),
    CONSTRAINT canonical_turns_session_provider_item_unique UNIQUE (session_id, provider_item_id)
);

CREATE INDEX canonical_turns_session_id_idx ON canonical_turns (session_id);

-- ---------------------------------------------------------------------------
-- Client observations (allowlisted types; untrusted)
-- ---------------------------------------------------------------------------

CREATE TABLE observations (
    observation_id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions (session_id) ON DELETE CASCADE,
    observation_type TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    connection_state TEXT,
    client_first_audio_observed_ms INTEGER,
    client_first_transcript_observed_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT observations_type_check CHECK (
        observation_type IN (
            'session_opened',
            'microphone_permission',
            'muted',
            'unmuted',
            'interrupted_ai',
            'connection_lost',
            'connection_restored',
            'first_audio_heard',
            'first_transcript_seen',
            'client_reported_problem'
        )
    )
);

CREATE INDEX observations_session_id_idx ON observations (session_id);

-- ---------------------------------------------------------------------------
-- Audit events (no transcript text copies)
-- ---------------------------------------------------------------------------

CREATE TABLE audit_events (
    audit_event_id UUID PRIMARY KEY,
    study_id UUID NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT,
    action TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id TEXT NOT NULL,
    authorization_result TEXT NOT NULL,
    request_id TEXT,
    object_version INTEGER,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX audit_events_study_id_idx ON audit_events (study_id);
CREATE INDEX audit_events_object_idx ON audit_events (object_type, object_id);

-- ---------------------------------------------------------------------------
-- Row level security (tables are API-visible via Supabase Data API)
-- ---------------------------------------------------------------------------

ALTER TABLE configuration_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE canonical_turns ENABLE ROW LEVEL SECURITY;
ALTER TABLE observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;

-- Deny all access through the Supabase Data API; the Study API uses a direct role.
CREATE POLICY configuration_snapshots_deny_api ON configuration_snapshots
    FOR ALL USING (false);

CREATE POLICY invitations_deny_api ON invitations
    FOR ALL USING (false);

CREATE POLICY sessions_deny_api ON sessions
    FOR ALL USING (false);

CREATE POLICY canonical_turns_deny_api ON canonical_turns
    FOR ALL USING (false);

CREATE POLICY observations_deny_api ON observations
    FOR ALL USING (false);

CREATE POLICY audit_events_deny_api ON audit_events
    FOR ALL USING (false);
