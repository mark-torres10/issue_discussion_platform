import { describe, expect, it, vi } from "vitest";
import {
  mapMicPermissionState,
} from "@/lib/realtime/state";
import {
  queryMicrophonePermission,
  requestMicrophoneAccess,
  stopMediaStream,
} from "@/lib/realtime/microphone";

describe("requestMicrophoneAccess", () => {
  it("returns unavailable when getUserMedia is missing", async () => {
    const result = await requestMicrophoneAccess(undefined);
    expect(result.status).toBe("unavailable");
    expect(result.stream).toBeNull();
  });

  it("returns denied when permission is rejected", async () => {
    const mediaDevices = {
      getUserMedia: vi.fn().mockRejectedValue(new Error("Permission denied")),
    } as unknown as MediaDevices;

    const result = await requestMicrophoneAccess(mediaDevices);
    expect(result.status).toBe("denied");
    expect(result.errorMessage).toMatch(/denied/i);
  });

  it("returns granted with a stream", async () => {
    const stream = { getTracks: () => [] } as unknown as MediaStream;
    const mediaDevices = {
      getUserMedia: vi.fn().mockResolvedValue(stream),
    } as unknown as MediaDevices;

    const result = await requestMicrophoneAccess(mediaDevices);
    expect(result.status).toBe("granted");
    expect(result.stream).toBe(stream);
  });
});

describe("queryMicrophonePermission", () => {
  it("falls back to prompt when permissions API is unavailable", async () => {
    const result = await queryMicrophonePermission(undefined);
    expect(result).toBe("prompt");
  });

  it("maps browser permission state", async () => {
    const permissions = {
      query: vi.fn().mockResolvedValue({ state: "granted" }),
    } as unknown as Permissions;
    const result = await queryMicrophonePermission(permissions);
    expect(result).toBe(mapMicPermissionState("granted"));
  });
});

describe("stopMediaStream", () => {
  it("stops all tracks", () => {
    const stop = vi.fn();
    const stream = {
      getTracks: () => [{ stop }, { stop }],
    } as unknown as MediaStream;
    stopMediaStream(stream);
    expect(stop).toHaveBeenCalledTimes(2);
  });
});
