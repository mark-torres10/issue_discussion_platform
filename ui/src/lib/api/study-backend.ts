import type { StudySession } from "@/lib/types/session";

export const SAMPLE_SESSION_ID = "demo-campus-speech-001";

export const SAMPLE_SESSION: StudySession = {
  sessionId: SAMPLE_SESSION_ID,
  studyWave: "pilot-2026-fall",
  status: "active",
  issue: {
    title: "Should universities limit invited speakers who hold contested views?",
    summary:
      "Some students argue that universities should cancel or restrict speakers whose views many find harmful. Others argue that open debate is central to campus learning.",
  },
  aiPersona: {
    displayName: "Jordan",
    shortIntroduction:
      "Jordan will disagree respectfully, ask clarifying questions, and explain a different position on this issue.",
    assignedPosition:
      "Universities should generally protect invited speakers and respond with counter-speech rather than cancellation.",
    avatarSrc: "/avatars/jordan.svg",
    avatarAlt: "Illustrated portrait of Jordan, the AI participant",
    isAiLabel: "AI participant",
  },
  rules: {
    durationMinutes: 8,
    warningBeforeEndSeconds: 90,
    allowInterrupt: true,
    showExactRemainingTime: false,
    completionNextStep:
      "Return to the study survey tab and continue with the next questionnaire section.",
  },
  openingAiMessage:
    "Thanks for joining. I am Jordan, an AI participant in this study. I think universities should generally protect invited speakers and answer contested ideas with counter-speech. What is your view?",
  scriptedAiReplies: [
    "That is a fair concern. If a speaker spreads ideas that make some students feel unsafe, how should a university decide when speech crosses that line?",
    "I hear that. My worry is that cancellation can also teach people to avoid hard disagreements instead of practicing them. What would a better disagreement look like on campus?",
    "That helps. Suppose two groups strongly disagree about the same speaker. How should the university balance safety with open debate?",
    "I am still not fully convinced, but I understand your point. Before we wrap up, what is one practical step universities could take that you would support?",
  ],
};

const SESSION_REGISTRY: Record<string, StudySession> = {
  [SAMPLE_SESSION_ID]: SAMPLE_SESSION,
  "expired-demo": {
    ...SAMPLE_SESSION,
    sessionId: "expired-demo",
    status: "expired",
  },
  "completed-demo": {
    ...SAMPLE_SESSION,
    sessionId: "completed-demo",
    status: "completed",
  },
  "paused-demo": {
    ...SAMPLE_SESSION,
    sessionId: "paused-demo",
    status: "paused",
  },
};

/**
 * Load a study session by id from the prototype registry.
 *
 * Parameters
 * ----------
 * sessionId
 *     Study link identifier from the route.
 *
 * Returns
 * -------
 * StudySession | null
 *     Matching session configuration, or null when the link is unknown.
 */
export function getStudySession(sessionId: string): StudySession | null {
  return SESSION_REGISTRY[sessionId] ?? null;
}

/**
 * Return whether a session can continue the participant journey.
 *
 * Parameters
 * ----------
 * session
 *     Loaded study session.
 *
 * Returns
 * -------
 * boolean
 *     True when the session status is active.
 */
export function isSessionAvailable(session: StudySession): boolean {
  return session.status === "active";
}
