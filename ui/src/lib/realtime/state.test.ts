import { describe, expect, it } from "vitest";
import {
  amplitudeToLevelPercent,
  appendParticipantMessage,
  buildRemainingTimeLabel,
  countParticipantTurns,
  createConversationSnapshot,
  formatElapsedTime,
  mapMicPermissionState,
  parseConversationSnapshot,
  resolveVoiceStateAfterControls,
  selectScriptedAiReply,
  serializeConversationSnapshot,
} from "@/lib/realtime/state";

describe("createConversationSnapshot", () => {
  it("seeds the opening AI message", () => {
    const result = createConversationSnapshot(
      "demo",
      "Hello from Jordan",
      "text",
    );
    expect(result.messages).toHaveLength(1);
    expect(result.messages[0]?.speaker).toBe("ai");
    expect(result.mode).toBe("text");
    expect(result.voiceState).toBe("idle");
  });
});

describe("appendParticipantMessage", () => {
  it("ignores blank input", () => {
    const snapshot = createConversationSnapshot("demo", "Hi", "text");
    const result = appendParticipantMessage(snapshot, "   ", "msg-1");
    expect(result).toEqual(snapshot);
  });

  it("appends a participant turn and enters thinking", () => {
    const snapshot = createConversationSnapshot("demo", "Hi", "text");
    const result = appendParticipantMessage(snapshot, "I disagree", "msg-1");
    expect(result.messages).toHaveLength(2);
    expect(result.voiceState).toBe("thinking");
    expect(countParticipantTurns(result.messages)).toBe(1);
  });
});

describe("selectScriptedAiReply", () => {
  it("clamps to the last scripted reply", () => {
    const replies = ["one", "two"];
    expect(selectScriptedAiReply(replies, 1)).toBe("one");
    expect(selectScriptedAiReply(replies, 2)).toBe("two");
    expect(selectScriptedAiReply(replies, 9)).toBe("two");
  });
});

describe("resolveVoiceStateAfterControls", () => {
  it("maps mute and mode combinations", () => {
    expect(resolveVoiceStateAfterControls("text", false, "granted")).toBe(
      "idle",
    );
    expect(resolveVoiceStateAfterControls("voice", true, "granted")).toBe(
      "muted",
    );
    expect(resolveVoiceStateAfterControls("voice", false, "denied")).toBe(
      "idle",
    );
    expect(resolveVoiceStateAfterControls("voice", false, "granted")).toBe(
      "listening",
    );
  });
});

describe("session timers and levels", () => {
  it("formats elapsed time", () => {
    expect(formatElapsedTime(65)).toBe("1:05");
  });

  it("builds calm remaining-time labels", () => {
    expect(buildRemainingTimeLabel(30, 8, 90)).toContain("minutes");
    expect(buildRemainingTimeLabel(7 * 60 + 30, 8, 90)).toBe(
      "The conversation is almost complete",
    );
    expect(buildRemainingTimeLabel(8 * 60, 8, 90)).toBe("Time is complete");
  });

  it("converts amplitude to a percent level", () => {
    expect(amplitudeToLevelPercent(0.5)).toBe(50);
    expect(amplitudeToLevelPercent(2)).toBe(100);
  });
});

describe("conversation snapshot serialization", () => {
  it("round-trips a valid snapshot", () => {
    const snapshot = createConversationSnapshot("demo", "Hi", "voice");
    const raw = serializeConversationSnapshot(snapshot);
    const result = parseConversationSnapshot(raw);
    expect(result?.sessionId).toBe("demo");
    expect(result?.mode).toBe("voice");
  });

  it("returns null for invalid JSON", () => {
    expect(parseConversationSnapshot("{bad")).toBeNull();
  });
});

describe("mapMicPermissionState", () => {
  it("normalizes permission states", () => {
    expect(mapMicPermissionState("granted")).toBe("granted");
    expect(mapMicPermissionState("denied")).toBe("denied");
    expect(mapMicPermissionState("prompt")).toBe("prompt");
    expect(mapMicPermissionState("unavailable")).toBe("unavailable");
  });
});
