-- Staff study membership for JWT-backed authorization (stub for v1).

CREATE TABLE staff_membership (
    membership_id UUID PRIMARY KEY,
    study_id UUID NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT staff_membership_study_user_unique UNIQUE (study_id, user_id),
    CONSTRAINT staff_membership_role_check CHECK (
        role IN ('operator', 'researcher', 'study_admin')
    )
);

CREATE INDEX staff_membership_user_id_idx ON staff_membership (user_id);
CREATE INDEX staff_membership_study_id_idx ON staff_membership (study_id);
