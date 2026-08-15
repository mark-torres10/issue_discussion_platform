import { describe, expect, it } from "vitest";
import {
  loadSessionContent,
  loadUiCopy,
  parseSessionContent,
} from "@/lib/content/loader";

describe("loadUiCopy", () => {
  it("reads home.heading from the real YAML file", () => {
    const result = loadUiCopy();
    expect(result.home.heading).toBe("Issue Discussion Study");
  });
});

describe("loadSessionContent", () => {
  it("returns the active sample session with four scripted replies", () => {
    const result = loadSessionContent();
    expect(result.status).toBe("active");
    expect(result.issue.title).toBe(
      "Should universities limit invited speakers who hold contested views?",
    );
    expect(result.scriptedAiReplies).toHaveLength(4);
  });
});

describe("parseSessionContent", () => {
  it("throws when issue.title is missing", () => {
    const incomplete = {
      sessionId: "demo-campus-speech-001",
      studyWave: "pilot-2026-fall",
      status: "active",
      issue: {
        summary: "Summary without a title.",
      },
      aiPersona: {
        displayName: "Jordan",
        shortIntroduction: "Intro",
        assignedPosition: "Position",
        avatarSrc: "/avatars/jordan.svg",
        avatarAlt: "Alt",
        isAiLabel: "AI participant",
      },
      rules: {
        durationMinutes: 8,
        warningBeforeEndSeconds: 90,
        allowInterrupt: true,
        showExactRemainingTime: false,
        completionNextStep: "Next",
      },
      openingAiMessage: "Hello",
      scriptedAiReplies: ["One", "Two", "Three", "Four"],
    };

    expect(() =>
      parseSessionContent(incomplete, "content/sessions/demo-campus-speech-001.yaml"),
    ).toThrow(/issue\.title/);
  });
});
