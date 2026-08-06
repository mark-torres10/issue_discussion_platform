"use client";

import { Button } from "@/components/ui/button";
import {
  formatElapsedTime,
  buildRemainingTimeLabel,
} from "@/lib/realtime/state";
import type { VoiceUiState } from "@/lib/types/session";

const CONNECTION_LABELS: Record<VoiceUiState, string> = {
  idle: "Connected",
  listening: "Connected",
  thinking: "Connected",
  speaking: "Connected",
  muted: "Connected",
  reconnecting: "Reconnecting",
};

interface SessionHeaderProps {
  issueTitle: string;
  elapsedSeconds: number;
  durationMinutes: number;
  warningBeforeEndSeconds: number;
  voiceState: VoiceUiState;
  onEndConversation: () => void;
}

/**
 * Compact discussion header with issue, time, status, and end control.
 */
export function SessionHeader({
  issueTitle,
  elapsedSeconds,
  durationMinutes,
  warningBeforeEndSeconds,
  voiceState,
  onEndConversation,
}: SessionHeaderProps) {
  return (
    <header className="flex flex-col gap-3 border-b border-black/5 px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex flex-col gap-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Discussion issue
          </p>
          <h1 className="text-sm font-semibold leading-snug text-[var(--ink)] sm:text-base">
            {issueTitle}
          </h1>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onEndConversation}
          data-testid="end-conversation"
        >
          End conversation
        </Button>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <p data-testid="elapsed-time">
          Elapsed {formatElapsedTime(elapsedSeconds)}
        </p>
        <p data-testid="remaining-time">
          {buildRemainingTimeLabel(
            elapsedSeconds,
            durationMinutes,
            warningBeforeEndSeconds,
          )}
        </p>
        <p data-testid="connection-status">
          {CONNECTION_LABELS[voiceState]}
        </p>
      </div>
    </header>
  );
}
