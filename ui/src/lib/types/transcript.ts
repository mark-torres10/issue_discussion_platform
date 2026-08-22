/**
 * Study API transcript types (participant projection).
 */

export type ApiSpeaker = "participant" | "ai" | "system";

export interface TranscriptTurnView {
  turn_id: string;
  speaker: ApiSpeaker;
  ordinal: number;
  display_text: string;
  source_mode: "voice" | "text";
  interrupted: boolean;
  recorded_at: string;
}

export interface TranscriptResponse {
  version: number;
  turns: TranscriptTurnView[];
  cursor: string | null;
}

export interface MessageCreate {
  client_message_id: string;
  text: string;
  client_created_at?: string;
  expected_version: number;
}

export interface MessageResponse {
  operation_id: string;
  operation_status: string;
  participant_turn: TranscriptTurnView;
  ai_turn: TranscriptTurnView | null;
  status: string;
  version: number;
}
