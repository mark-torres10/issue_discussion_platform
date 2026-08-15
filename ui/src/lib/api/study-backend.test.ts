import { describe, expect, it } from "vitest";
import {
  getStudySession,
  isSessionAvailable,
  SAMPLE_SESSION_ID,
} from "@/lib/api/study-backend";

describe("getStudySession", () => {
  it("returns the sample active session", () => {
    const result = getStudySession(SAMPLE_SESSION_ID);
    expect(result?.status).toBe("active");
    expect(result?.aiPersona.isAiLabel).toBe("AI participant");
  });

  it("returns null for unknown session ids", () => {
    const result = getStudySession("missing-session");
    expect(result).toBeNull();
  });

  it("shares the sample issue title for expired-demo", () => {
    const sample = getStudySession(SAMPLE_SESSION_ID);
    const expired = getStudySession("expired-demo");
    expect(expired?.status).toBe("expired");
    expect(expired?.issue.title).toBe(sample?.issue.title);
  });
});

describe("isSessionAvailable", () => {
  it("allows only active sessions", () => {
    const active = getStudySession(SAMPLE_SESSION_ID);
    const expired = getStudySession("expired-demo");
    expect(active && isSessionAvailable(active)).toBe(true);
    expect(expired && isSessionAvailable(expired)).toBe(false);
  });
});
