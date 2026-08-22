"""In-memory sample session seed data."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.models.enums import SessionStatus
from app.models.session import (
    AiPersonaPublic,
    IssueConfig,
    SessionRecord,
    SessionRulesPublic,
)
from app.sample_data.invitations import (
    SAMPLE_WRITER_INVITATION_TOKEN,
    hash_invitation_token,
)

DEMO_SESSION_ID = UUID("018f5a20-7c3a-7000-8000-000000000001")
DEMO_STUDY_ID = UUID("018f5a20-7c3a-7000-8000-000000000002")
DEMO_SNAPSHOT_ID = UUID("018f5a20-7c3a-7000-8000-000000000003")
DEMO_TELEMETRY_THREAD_ID = UUID("018f5a20-7c3a-7000-8000-000000000004")

DEMO_ISSUE = IssueConfig(
    issue_id="demo-campus-speech-001",
    title="Should universities limit invited speakers who hold contested views?",
    summary=(
        "Some students argue that universities should cancel or restrict speakers "
        "whose views many find harmful. Others argue that open debate is central "
        "to campus learning."
    ),
)

DEMO_AI_PERSONA = AiPersonaPublic(
    display_name="Jordan",
    short_introduction=(
        "Jordan will disagree respectfully, ask clarifying questions, and explain a "
        "different position on this issue."
    ),
    avatar_url="http://testserver/avatars/jordan.svg",
    avatar_version="v1",
    assigned_position=(
        "Universities should generally protect invited speakers and respond with "
        "counter-speech rather than cancellation."
    ),
)

DEMO_RULES = SessionRulesPublic(
    target_duration_seconds=8 * 60,
    warn_remaining_seconds=90,
    allow_interrupt=True,
    allow_text_fallback=True,
    ai_speaks_first=True,
    show_exact_remaining_time=False,
    allow_resume=True,
)

DEMO_OPENING_MESSAGE = (
    "Thanks for joining. I am Jordan, an AI participant in this study. I think "
    "universities should generally protect invited speakers and answer contested "
    "ideas with counter-speech. What is your view?"
)

DEMO_SCRIPTED_AI_REPLIES = [
    (
        "That is a fair concern. If a speaker spreads ideas that make some students "
        "feel unsafe, how should a university decide when speech crosses that line?"
    ),
    (
        "I hear that. My worry is that cancellation can also teach people to avoid "
        "hard disagreements instead of practicing them. What would a better "
        "disagreement look like on campus?"
    ),
    (
        "That helps. Suppose two groups strongly disagree about the same speaker. How "
        "should the university balance safety with open debate?"
    ),
    (
        "I am still not fully convinced, but I understand your point. Before we wrap "
        "up, what is one practical step universities could take that you would "
        "support?"
    ),
]

DEMO_COMPLETION_NEXT_STEP = (
    "Return to the study survey tab and continue with the next questionnaire section."
)

DEMO_PROMPT_VERSION = "demo-v1"
DEMO_STUDY_WAVE = "pilot-2026-fall"
DEMO_CONSENT_REQUIRED = False


class ConfigurationSnapshot:
    def __init__(self) -> None:
        self.snapshot_id = DEMO_SNAPSHOT_ID
        self.study_wave = DEMO_STUDY_WAVE
        self.issue = DEMO_ISSUE
        self.ai_persona = DEMO_AI_PERSONA
        self.rules = DEMO_RULES
        self.prompt_version = DEMO_PROMPT_VERSION
        self.opening_message = DEMO_OPENING_MESSAGE
        self.scripted_ai_replies = list(DEMO_SCRIPTED_AI_REPLIES)
        self.completion_next_step = DEMO_COMPLETION_NEXT_STEP
        self.consent_required = DEMO_CONSENT_REQUIRED


def build_demo_session_record() -> SessionRecord:
    now = datetime.now(UTC)
    return SessionRecord(
        session_id=DEMO_SESSION_ID,
        study_id=DEMO_STUDY_ID,
        participant_capability_hash="",
        telemetry_thread_id=DEMO_TELEMETRY_THREAD_ID,
        status=SessionStatus.pending,
        version=1,
        configuration_snapshot_id=DEMO_SNAPSHOT_ID,
        started_at=None,
        completed_at=None,
    )


INVITATION_TOKEN_HASHES: dict[str, UUID] = {
    hash_invitation_token(SAMPLE_WRITER_INVITATION_TOKEN): DEMO_SESSION_ID,
}
