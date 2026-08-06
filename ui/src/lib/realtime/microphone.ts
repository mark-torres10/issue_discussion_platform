import type { MicPermissionStatus } from "@/lib/types/session";
import { mapMicPermissionState } from "@/lib/realtime/state";

export interface MicrophoneProbeResult {
  status: MicPermissionStatus;
  stream: MediaStream | null;
  errorMessage: string | null;
}

/**
 * Request microphone access for the audio check or voice mode.
 *
 * Parameters
 * ----------
 * mediaDevices
 *     Browser mediaDevices API.
 *
 * Returns
 * -------
 * Promise<MicrophoneProbeResult>
 *     Permission result and optional live stream.
 */
export async function requestMicrophoneAccess(
  mediaDevices: MediaDevices | undefined,
): Promise<MicrophoneProbeResult> {
  if (!mediaDevices?.getUserMedia) {
    return {
      status: "unavailable",
      stream: null,
      errorMessage:
        "This browser does not support microphone access. You can continue with text.",
    };
  }

  try {
    const stream = await mediaDevices.getUserMedia({ audio: true });
    return {
      status: "granted",
      stream,
      errorMessage: null,
    };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Microphone permission failed.";
    const denied =
      message.toLowerCase().includes("denied") ||
      message.toLowerCase().includes("permission");

    return {
      status: denied ? "denied" : "unavailable",
      stream: null,
      errorMessage: denied
        ? "Microphone permission was denied. You can retry or continue with text."
        : "No microphone was found. You can continue with text.",
    };
  }
}

/**
 * Stop all tracks on a media stream.
 *
 * Parameters
 * ----------
 * stream
 *     Active media stream, if any.
 */
export function stopMediaStream(stream: MediaStream | null): void {
  if (!stream) {
    return;
  }
  for (const track of stream.getTracks()) {
    track.stop();
  }
}

/**
 * Query the browser microphone permission state when available.
 *
 * Parameters
 * ----------
 * permissions
 *     Browser permissions API.
 *
 * Returns
 * -------
 * Promise<MicPermissionStatus>
 *     Normalized permission status.
 */
export async function queryMicrophonePermission(
  permissions: Permissions | undefined,
): Promise<MicPermissionStatus> {
  if (!permissions?.query) {
    return "prompt";
  }

  try {
    const result = await permissions.query({
      name: "microphone" as PermissionName,
    });
    return mapMicPermissionState(result.state);
  } catch {
    return "prompt";
  }
}

/**
 * Play a short local test tone through the selected output.
 *
 * Parameters
 * ----------
 * audioContext
 *     Web Audio context factory.
 * durationMs
 *     Tone length in milliseconds.
 * frequencyHz
 *     Tone frequency.
 *
 * Returns
 * -------
 * Promise<void>
 *     Resolves when the tone finishes.
 */
export async function playTestTone(
  audioContext: { new (): AudioContext },
  durationMs: number,
  frequencyHz: number,
): Promise<void> {
  const context = new audioContext();
  const oscillator = context.createOscillator();
  const gain = context.createGain();

  oscillator.type = "sine";
  oscillator.frequency.value = frequencyHz;
  gain.gain.value = 0.05;
  oscillator.connect(gain);
  gain.connect(context.destination);
  oscillator.start();

  await new Promise((resolve) => {
    window.setTimeout(resolve, durationMs);
  });

  oscillator.stop();
  await context.close();
}
