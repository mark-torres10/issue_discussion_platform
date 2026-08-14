import "server-only";

import { loadSessionContent } from "@/lib/content/loader";
import type { StudySession } from "@/lib/types/session";

export const SAMPLE_SESSION_ID = "demo-campus-speech-001";

const STATUS_OVERLAY_IDS = {
  "expired-demo": "expired",
  "completed-demo": "completed",
  "paused-demo": "paused",
} as const;

type StatusOverlayId = keyof typeof STATUS_OVERLAY_IDS;

/**
 * Load a study session by id from YAML plus status overlays.
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
  if (sessionId === SAMPLE_SESSION_ID) {
    return loadSessionContent();
  }

  if (sessionId in STATUS_OVERLAY_IDS) {
    const sample = loadSessionContent();
    const overlayId = sessionId as StatusOverlayId;
    return {
      ...sample,
      sessionId: overlayId,
      status: STATUS_OVERLAY_IDS[overlayId],
    };
  }

  return null;
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
