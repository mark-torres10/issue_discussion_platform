import { describe, expect, it } from "vitest";
import { CAPABILITY_COOKIE_NAME, CSRF_HEADER_NAME, withCsrfHeaders } from "@/lib/api/csrf";
import {
  buildParticipantFetchInit,
  getParticipantCookieOptions,
  mapParticipantSessionView,
  parseCapabilityFromSetCookie,
  parseExchangeCookieValues,
  PARTICIPANT_ROUTES,
  SAMPLE_INVITATION_TOKEN,
  type ParticipantSessionView,
} from "@/lib/api/study-backend";

const SAMPLE_API_VIEW: ParticipantSessionView = {
  status: "pending",
  version: 1,
  writer_role: "writer",
  study_wave: "pilot-2026-fall",
  issue: {
    issue_id: "demo-campus-speech-001",
    title: "Should universities limit invited speakers who hold contested views?",
    summary: "Campus speech summary.",
  },
  ai_persona: {
    display_name: "Jordan",
    label: "AI participant",
    short_introduction: "Jordan will disagree respectfully.",
    avatar_url: "http://testserver/avatars/jordan.svg",
    avatar_version: "v1",
    assigned_position: "Protect invited speakers.",
  },
  rules: {
    target_duration_seconds: 480,
    warn_remaining_seconds: 90,
    allow_interrupt: true,
    allow_text_fallback: true,
    ai_speaks_first: true,
    show_exact_remaining_time: false,
    allow_resume: true,
  },
  preferred_mode: "text",
  started_at: null,
  ends_at: null,
  completed_at: null,
  next_instruction: null,
};

describe("TestExchangeRedirect", () => {
  it("test_maps_api_session_view", () => {
    const mapped = mapParticipantSessionView(SAMPLE_API_VIEW);
    expect(mapped.sessionId).toBe("demo-campus-speech-001");
    expect(mapped.status).toBe("active");
    expect(mapped.version).toBe(1);
    expect(mapped.aiPersona.displayName).toBe("Jordan");
    expect(mapped.aiPersona.isAiLabel).toBe("AI participant");
    expect(mapped.rules.durationMinutes).toBe(8);
    expect(mapped.aiSpeaksFirst).toBe(true);
    expect(mapped.aiPersona.avatarSrc).toBe("/avatars/jordan.svg");
  });
});

describe("TestCsrfHeader", () => {
  it("test_includes_csrf_on_post", () => {
    const headers = withCsrfHeaders({}, "csrf-test-token");
    expect(new Headers(headers).get(CSRF_HEADER_NAME)).toBe("csrf-test-token");

    const init = buildParticipantFetchInit({
      method: "POST",
      csrf: true,
      body: JSON.stringify({ invitation_token: SAMPLE_INVITATION_TOKEN }),
    });
    expect(init.credentials).toBe("include");
    const builtHeaders = new Headers(init.headers);
    expect(builtHeaders.get("content-type")).toBe("application/json");
  });
});

describe("TestNoSessionIdInPath", () => {
  it("test_session_routes_omit_id", () => {
    for (const route of Object.values(PARTICIPANT_ROUTES)) {
      expect(route).not.toMatch(/\/session\/[^/]+\//);
      expect(route).not.toMatch(/demo-campus-speech-001/);
    }
    expect(PARTICIPANT_ROUTES.conversation).toBe("/session/conversation");
    expect(PARTICIPANT_ROUTES.session).toBe("/session");
  });
});

describe("TestExchangeCookies", () => {
  it("test_parses_capability_from_set_cookie_headers", () => {
    const headers = [
      `${CAPABILITY_COOKIE_NAME}=cap-token-123; Path=/; HttpOnly`,
      "other=value; Path=/",
    ];
    expect(parseCapabilityFromSetCookie(headers)).toBe("cap-token-123");
  });

  it("test_parses_capability_from_raw_set_cookie", () => {
    const raw = `${CAPABILITY_COOKIE_NAME}=raw-token; Path=/; HttpOnly`;
    expect(parseCapabilityFromSetCookie([], raw)).toBe("raw-token");
  });

  it("test_parses_exchange_cookie_values", () => {
    const response = new Response(null, {
      headers: {
        [CSRF_HEADER_NAME]: "csrf-from-header",
        "set-cookie": `${CAPABILITY_COOKIE_NAME}=cap-from-response; Path=/`,
      },
    });

    expect(parseExchangeCookieValues(response)).toEqual({
      capabilityValue: "cap-from-response",
      csrfToken: "csrf-from-header",
    });
  });

  it("test_participant_cookie_options_secure_in_production", () => {
    const capability = getParticipantCookieOptions(true);
    expect(capability.httpOnly).toBe(true);
    expect(capability.sameSite).toBe("lax");
    expect(capability.path).toBe("/");
    expect(capability.secure).toBe(process.env.NODE_ENV === "production");
  });
});
