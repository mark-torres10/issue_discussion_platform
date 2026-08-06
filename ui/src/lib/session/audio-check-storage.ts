import type { ConversationMode } from "@/lib/types/session";

export const AUDIO_CHECK_STORAGE_PREFIX = "idp-audio-check:";

export interface AudioCheckPreferences {
  mode: ConversationMode;
  micReady: boolean;
  speakerReady: boolean;
}

/**
 * Storage key for audio-check preferences.
 *
 * Parameters
 * ----------
 * sessionId
 *     Study session id.
 *
 * Returns
 * -------
 * string
 *     sessionStorage key.
 */
export function audioCheckStorageKey(sessionId: string): string {
  return `${AUDIO_CHECK_STORAGE_PREFIX}${sessionId}`;
}

/**
 * Parse stored audio-check preferences.
 *
 * Parameters
 * ----------
 * raw
 *     JSON string from sessionStorage.
 *
 * Returns
 * -------
 * AudioCheckPreferences | null
 *     Parsed preferences, or null when invalid.
 */
export function parseAudioCheckPreferences(
  raw: string,
): AudioCheckPreferences | null {
  try {
    const parsed = JSON.parse(raw) as AudioCheckPreferences;
    if (parsed.mode !== "voice" && parsed.mode !== "text") {
      return null;
    }
    return {
      mode: parsed.mode,
      micReady: Boolean(parsed.micReady),
      speakerReady: Boolean(parsed.speakerReady),
    };
  } catch {
    return null;
  }
}
