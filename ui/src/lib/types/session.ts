/**
 * Session and conversation domain types for the participant UI prototype.
 */

export type SessionStatus =
  | "active"
  | "completed"
  | "expired"
  | "paused"
  | "invalid";

export type ConversationMode = "voice" | "text";

export type VoiceUiState =
  | "idle"
  | "listening"
  | "thinking"
  | "speaking"
  | "muted"
  | "reconnecting";

export type Speaker = "participant" | "ai";

export type MicPermissionStatus =
  | "prompt"
  | "granted"
  | "denied"
  | "unavailable";

export interface AiPersona {
  displayName: string;
  shortIntroduction: string;
  assignedPosition: string;
  avatarSrc: string;
  avatarAlt: string;
  isAiLabel: string;
}

export interface StudyIssue {
  title: string;
  summary: string;
}

export interface SessionRules {
  durationMinutes: number;
  warningBeforeEndSeconds: number;
  allowInterrupt: boolean;
  showExactRemainingTime: boolean;
  completionNextStep: string;
}

export interface StudySession {
  sessionId: string;
  studyWave: string;
  status: SessionStatus;
  issue: StudyIssue;
  aiPersona: AiPersona;
  rules: SessionRules;
  openingAiMessage: string;
  scriptedAiReplies: string[];
}

export interface TranscriptMessage {
  id: string;
  speaker: Speaker;
  text: string;
  createdAt: string;
  isPartial?: boolean;
}

export interface ConversationSnapshot {
  sessionId: string;
  mode: ConversationMode;
  voiceState: VoiceUiState;
  captionsEnabled: boolean;
  messages: TranscriptMessage[];
  startedAt: string | null;
  endedAt: string | null;
  micPermission: MicPermissionStatus;
  saveStatus: "idle" | "saving" | "saved" | "retrying";
}
