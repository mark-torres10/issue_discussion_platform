import type {
  ConversationMode,
  ConversationSnapshot,
  MicPermissionStatus,
  TranscriptMessage,
  VoiceUiState,
} from "@/lib/types/session";

export const CONVERSATION_STORAGE_PREFIX = "idp-conversation:";

export const DEFAULT_VOICE_STATE: VoiceUiState = "idle";

/**
 * Build a fresh conversation snapshot for a session.
 *
 * Parameters
 * ----------
 * sessionId
 *     Active study session id.
 * openingAiMessage
 *     First AI message shown when the discussion begins.
 * mode
 *     Initial voice or text mode.
 *
 * Returns
 * -------
 * ConversationSnapshot
 *     Initial local conversation state.
 */
export function createConversationSnapshot(
  sessionId: string,
  openingAiMessage: string,
  mode: ConversationMode,
): ConversationSnapshot {
  const openingMessage: TranscriptMessage = {
    id: "msg-ai-opening",
    speaker: "ai",
    text: openingAiMessage,
    createdAt: new Date().toISOString(),
  };

  return {
    sessionId,
    mode,
    voiceState: mode === "voice" ? "listening" : "idle",
    captionsEnabled: true,
    messages: [openingMessage],
    startedAt: new Date().toISOString(),
    endedAt: null,
    micPermission: "prompt",
    saveStatus: "idle",
  };
}

/**
 * Serialize a conversation snapshot for sessionStorage.
 *
 * Parameters
 * ----------
 * snapshot
 *     Current conversation state.
 *
 * Returns
 * -------
 * string
 *     JSON payload.
 */
export function serializeConversationSnapshot(
  snapshot: ConversationSnapshot,
): string {
  return JSON.stringify(snapshot);
}

/**
 * Parse a stored conversation snapshot.
 *
 * Parameters
 * ----------
 * raw
 *     JSON string from sessionStorage.
 *
 * Returns
 * -------
 * ConversationSnapshot | null
 *     Parsed snapshot, or null when invalid.
 */
export function parseConversationSnapshot(
  raw: string,
): ConversationSnapshot | null {
  try {
    const parsed = JSON.parse(raw) as ConversationSnapshot;
    if (
      typeof parsed.sessionId !== "string" ||
      !Array.isArray(parsed.messages)
    ) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

/**
 * Storage key for a conversation snapshot.
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
export function conversationStorageKey(sessionId: string): string {
  return `${CONVERSATION_STORAGE_PREFIX}${sessionId}`;
}

/**
 * Append a completed participant message and move into thinking state.
 *
 * Parameters
 * ----------
 * snapshot
 *     Current conversation state.
 * text
 *     Participant message text.
 * messageId
 *     Stable id for the new message.
 *
 * Returns
 * -------
 * ConversationSnapshot
 *     Updated snapshot.
 */
export function appendParticipantMessage(
  snapshot: ConversationSnapshot,
  text: string,
  messageId: string,
): ConversationSnapshot {
  const trimmed = text.trim();
  if (!trimmed) {
    return snapshot;
  }

  const message: TranscriptMessage = {
    id: messageId,
    speaker: "participant",
    text: trimmed,
    createdAt: new Date().toISOString(),
  };

  return {
    ...snapshot,
    voiceState: "thinking",
    messages: [...snapshot.messages, message],
  };
}

/**
 * Start a partial AI reply for simulated streaming.
 *
 * Parameters
 * ----------
 * snapshot
 *     Current conversation state.
 * messageId
 *     Stable id for the streaming AI message.
 *
 * Returns
 * -------
 * ConversationSnapshot
 *     Snapshot with a partial AI message and speaking state.
 */
export function beginAiStreamingReply(
  snapshot: ConversationSnapshot,
  messageId: string,
): ConversationSnapshot {
  const message: TranscriptMessage = {
    id: messageId,
    speaker: "ai",
    text: "",
    createdAt: new Date().toISOString(),
    isPartial: true,
  };

  return {
    ...snapshot,
    voiceState: "speaking",
    messages: [...snapshot.messages, message],
  };
}

/**
 * Update the partial AI message text during simulated streaming.
 *
 * Parameters
 * ----------
 * snapshot
 *     Current conversation state.
 * messageId
 *     Streaming AI message id.
 * text
 *     Full text revealed so far.
 *
 * Returns
 * -------
 * ConversationSnapshot
 *     Snapshot with updated partial text.
 */
export function updateAiStreamingReply(
  snapshot: ConversationSnapshot,
  messageId: string,
  text: string,
): ConversationSnapshot {
  return {
    ...snapshot,
    messages: snapshot.messages.map((message) =>
      message.id === messageId
        ? { ...message, text, isPartial: true }
        : message,
    ),
  };
}

/**
 * Finalize a streaming AI reply.
 *
 * Parameters
 * ----------
 * snapshot
 *     Current conversation state.
 * messageId
 *     Streaming AI message id.
 * text
 *     Final message text.
 * nextVoiceState
 *     State after the AI finishes speaking.
 *
 * Returns
 * -------
 * ConversationSnapshot
 *     Snapshot with a completed AI message.
 */
export function finalizeAiStreamingReply(
  snapshot: ConversationSnapshot,
  messageId: string,
  text: string,
  nextVoiceState: VoiceUiState,
): ConversationSnapshot {
  return {
    ...snapshot,
    voiceState: nextVoiceState,
    messages: snapshot.messages.map((message) =>
      message.id === messageId
        ? { ...message, text, isPartial: false }
        : message,
    ),
  };
}

/**
 * Choose the next scripted AI reply based on participant turn count.
 *
 * Parameters
 * ----------
 * scriptedReplies
 *     Ordered list of prototype AI replies.
 * participantTurnCount
 *     Number of completed participant turns so far.
 *
 * Returns
 * -------
 * string
 *     Reply text for the next AI turn.
 */
export function selectScriptedAiReply(
  scriptedReplies: string[],
  participantTurnCount: number,
): string {
  if (scriptedReplies.length === 0) {
    return "Thanks for sharing that perspective.";
  }

  const index = Math.min(
    Math.max(participantTurnCount - 1, 0),
    scriptedReplies.length - 1,
  );
  return scriptedReplies[index];
}

/**
 * Count completed participant messages in a transcript.
 *
 * Parameters
 * ----------
 * messages
 *     Transcript messages.
 *
 * Returns
 * -------
 * number
 *     Count of participant turns.
 */
export function countParticipantTurns(messages: TranscriptMessage[]): number {
  return messages.filter((message) => message.speaker === "participant").length;
}

/**
 * Resolve the next voice UI state after a mode or mute change.
 *
 * Parameters
 * ----------
 * mode
 *     Active conversation mode.
 * isMuted
 *     Whether the microphone is muted.
 * micPermission
 *     Current browser microphone permission.
 *
 * Returns
 * -------
 * VoiceUiState
 *     Visible conversation state label.
 */
export function resolveVoiceStateAfterControls(
  mode: ConversationMode,
  isMuted: boolean,
  micPermission: MicPermissionStatus,
): VoiceUiState {
  if (mode === "text") {
    return "idle";
  }
  if (micPermission === "denied" || micPermission === "unavailable") {
    return "idle";
  }
  if (isMuted) {
    return "muted";
  }
  return "listening";
}

/**
 * Format elapsed session time as m:ss.
 *
 * Parameters
 * ----------
 * elapsedSeconds
 *     Seconds since conversation start.
 *
 * Returns
 * -------
 * string
 *     Formatted elapsed time.
 */
export function formatElapsedTime(elapsedSeconds: number): string {
  const safeSeconds = Math.max(0, Math.floor(elapsedSeconds));
  const minutes = Math.floor(safeSeconds / 60);
  const seconds = safeSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

/**
 * Build a calm remaining-time statement without an exact countdown.
 *
 * Parameters
 * ----------
 * elapsedSeconds
 *     Seconds since conversation start.
 * durationMinutes
 *     Assigned discussion length.
 * warningBeforeEndSeconds
 *     Threshold for the near-end notice.
 *
 * Returns
 * -------
 * string
 *     Participant-facing remaining time copy.
 */
export function buildRemainingTimeLabel(
  elapsedSeconds: number,
  durationMinutes: number,
  warningBeforeEndSeconds: number,
): string {
  const totalSeconds = durationMinutes * 60;
  const remainingSeconds = Math.max(0, totalSeconds - elapsedSeconds);

  if (remainingSeconds === 0) {
    return "Time is complete";
  }
  if (remainingSeconds <= warningBeforeEndSeconds) {
    return "The conversation is almost complete";
  }
  if (remainingSeconds <= totalSeconds / 2) {
    return "About halfway through";
  }
  return `About ${durationMinutes} minutes total`;
}

/**
 * Map a browser permission state string to MicPermissionStatus.
 *
 * Parameters
 * ----------
 * state
 *     Browser PermissionState or custom probe result.
 *
 * Returns
 * -------
 * MicPermissionStatus
 *     Normalized microphone status.
 */
export function mapMicPermissionState(
  state: PermissionState | "unavailable",
): MicPermissionStatus {
  if (state === "unavailable") {
    return "unavailable";
  }
  if (state === "granted") {
    return "granted";
  }
  if (state === "denied") {
    return "denied";
  }
  return "prompt";
}

/**
 * Convert a measured amplitude into a 0-100 microphone level.
 *
 * Parameters
 * ----------
 * amplitude
 *     Root-mean-square amplitude in [0, 1].
 *
 * Returns
 * -------
 * number
 *     Rounded level percentage in [0, 100].
 */
export function amplitudeToLevelPercent(amplitude: number): number {
  const clamped = Math.min(1, Math.max(0, amplitude));
  return Math.round(clamped * 100);
}
