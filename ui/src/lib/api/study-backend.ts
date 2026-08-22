import {
  CAPABILITY_COOKIE_NAME,
  CSRF_HEADER_NAME,
  withCsrfHeaders,
} from "@/lib/api/csrf";
import type { StudySession, SessionStatus } from "@/lib/types/session";

export const SAMPLE_SESSION_ID = "demo-campus-speech-001";

export const SAMPLE_INVITATION_TOKEN =
  "demo-campus-speech-001-invitation-token-for-contract-tests";

export const IDEMPOTENCY_HEADER_NAME = "Idempotency-Key";

/** Cookie-scoped participant routes (no public session id in the path). */
export const PARTICIPANT_ROUTES = {
  session: "/session",
  audioCheck: "/session/audio-check",
  conversation: "/session/conversation",
  complete: "/session/complete",
  unavailable: "/session/unavailable",
} as const;

export interface ParticipantSessionView {
  status: string;
  version: number;
  writer_role: "writer" | "read_only";
  study_wave: string;
  issue: {
    issue_id: string;
    title: string;
    summary: string;
  };
  ai_persona: {
    display_name: string;
    label: string;
    short_introduction: string;
    avatar_url: string;
    avatar_version: string;
    assigned_position: string;
  };
  rules: {
    target_duration_seconds: number;
    warn_remaining_seconds: number;
    allow_interrupt: boolean;
    allow_text_fallback: boolean;
    ai_speaks_first: boolean;
    show_exact_remaining_time: boolean;
    allow_resume: boolean;
  };
  preferred_mode: "voice" | "text";
  started_at: string | null;
  ends_at: string | null;
  completed_at: string | null;
  next_instruction: string | null;
}

export interface SessionStartResponse {
  session: ParticipantSessionView;
  opening_turn: {
    turn_id: string;
    speaker: string;
    display_text: string;
    recorded_at: string;
  } | null;
}

export interface SessionCompleteResponse {
  session: ParticipantSessionView;
  saved_turn_count: number;
}

export class StudyApiError extends Error {
  constructor(
    readonly statusCode: number,
    readonly errorCode: string,
    message: string,
  ) {
    super(message);
    this.name = "StudyApiError";
  }
}

/**
 * Resolve the public Study API origin for server and browser calls.
 */
export function getStudyApiOrigin(): string {
  return (
    process.env.NEXT_PUBLIC_STUDY_API_ORIGIN?.replace(/\/$/, "") ??
    "http://127.0.0.1:8000"
  );
}

/**
 * Build fetch init for participant Study API calls from the browser.
 */
export function buildParticipantFetchInit(
  init: RequestInit & { csrf?: boolean; idempotencyKey?: string } = {},
): RequestInit {
  const headers = new Headers(
    init.csrf ? withCsrfHeaders(init.headers) : init.headers,
  );
  if (init.idempotencyKey) {
    headers.set(IDEMPOTENCY_HEADER_NAME, init.idempotencyKey);
  }
  if (init.body && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }
  return {
    ...init,
    headers,
    credentials: "include",
  };
}

function mapApiStatus(status: string): SessionStatus {
  switch (status) {
    case "pending":
    case "active":
      return "active";
    case "paused":
      return "paused";
    case "completed":
      return "completed";
    case "expired":
      return "expired";
    default:
      return "invalid";
  }
}

function resolveAvatarSrc(avatarUrl: string): string {
  if (avatarUrl.startsWith("http://testserver/")) {
    return avatarUrl.replace("http://testserver", "");
  }
  try {
    const parsed = new URL(avatarUrl);
    return parsed.pathname;
  } catch {
    return avatarUrl;
  }
}

/**
 * Map a Study API session view to the participant UI session model.
 */
export function mapParticipantSessionView(
  view: ParticipantSessionView,
): StudySession {
  const durationMinutes = Math.max(
    1,
    Math.round(view.rules.target_duration_seconds / 60),
  );

  return {
    sessionId: view.issue.issue_id,
    studyWave: view.study_wave,
    status: mapApiStatus(view.status),
    version: view.version,
    writerRole: view.writer_role,
    issue: {
      title: view.issue.title,
      summary: view.issue.summary,
    },
    aiPersona: {
      displayName: view.ai_persona.display_name,
      shortIntroduction: view.ai_persona.short_introduction,
      assignedPosition: view.ai_persona.assigned_position,
      avatarSrc: resolveAvatarSrc(view.ai_persona.avatar_url),
      avatarAlt: `Illustrated portrait of ${view.ai_persona.display_name}, the AI participant`,
      isAiLabel: view.ai_persona.label,
    },
    rules: {
      durationMinutes,
      warningBeforeEndSeconds: view.rules.warn_remaining_seconds,
      allowInterrupt: view.rules.allow_interrupt,
      showExactRemainingTime: view.rules.show_exact_remaining_time,
      completionNextStep:
        view.next_instruction ??
        "Return to the study survey tab and continue with the next questionnaire section.",
    },
    openingAiMessage: "",
    aiSpeaksFirst: view.rules.ai_speaks_first,
    preferredMode: view.preferred_mode,
    startedAt: view.started_at,
    endsAt: view.ends_at,
  };
}

/**
 * Return whether a session can continue the participant journey.
 */
export function isSessionAvailable(session: StudySession): boolean {
  return session.status === "active";
}

export interface ExchangeCookieValues {
  capabilityValue?: string;
  csrfToken: string | null;
}

export interface ParticipantCookieOptions {
  httpOnly: boolean;
  sameSite: "lax";
  path: "/";
  secure: boolean;
}

/**
 * Parse the capability token from Set-Cookie response headers.
 */
export function parseCapabilityFromSetCookie(
  setCookieHeaders: string[],
  rawSetCookie?: string | null,
): string | undefined {
  const capabilityCookie =
    setCookieHeaders.find((entry) =>
      entry.startsWith(`${CAPABILITY_COOKIE_NAME}=`),
    ) ??
    (rawSetCookie?.startsWith(`${CAPABILITY_COOKIE_NAME}=`)
      ? rawSetCookie
      : undefined);

  return capabilityCookie
    ?.split(";")[0]
    ?.slice(`${CAPABILITY_COOKIE_NAME}=`.length);
}

/**
 * Extract participant cookie values from an exchange response.
 */
export function parseExchangeCookieValues(
  response: Pick<Response, "headers">,
): ExchangeCookieValues {
  const setCookieHeaders =
    typeof response.headers.getSetCookie === "function"
      ? response.headers.getSetCookie()
      : [];
  const rawSetCookie = response.headers.get("set-cookie");

  return {
    capabilityValue: parseCapabilityFromSetCookie(
      setCookieHeaders,
      rawSetCookie,
    ),
    csrfToken: response.headers.get(CSRF_HEADER_NAME),
  };
}

/**
 * Cookie attributes for participant capability and CSRF cookies.
 */
export function getParticipantCookieOptions(
  httpOnly: boolean,
): ParticipantCookieOptions {
  return {
    httpOnly,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
  };
}

export { CSRF_HEADER_NAME };
