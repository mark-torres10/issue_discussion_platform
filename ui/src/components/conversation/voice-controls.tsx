"use client";

import {
  Captions,
  CaptionsOff,
  Keyboard,
  Mic,
  MicOff,
  Square,
  TriangleAlert,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ConversationMode, VoiceUiState } from "@/lib/types/session";

interface VoiceControlsProps {
  mode: ConversationMode;
  voiceState: VoiceUiState;
  isMuted: boolean;
  captionsEnabled: boolean;
  micLevel: number;
  canUseVoice: boolean;
  onToggleMute: () => void;
  onStopAiAudio: () => void;
  onSwitchMode: (mode: ConversationMode) => void;
  onToggleCaptions: () => void;
  onReportConnectionProblem: () => void;
  onPrimaryMicPress: () => void;
}

/**
 * Fixed control area for microphone, mute, captions, and mode switching.
 */
export function VoiceControls({
  mode,
  voiceState,
  isMuted,
  captionsEnabled,
  micLevel,
  canUseVoice,
  onToggleMute,
  onStopAiAudio,
  onSwitchMode,
  onToggleCaptions,
  onReportConnectionProblem,
  onPrimaryMicPress,
}: VoiceControlsProps) {
  const micLabel =
    voiceState === "listening"
      ? "Microphone on"
      : voiceState === "muted"
        ? "Microphone muted"
        : "Microphone";

  return (
    <div className="flex flex-col gap-3 border-t border-black/5 bg-white px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
      {mode === "voice" ? (
        <div className="flex flex-col items-center gap-2">
          <Button
            type="button"
            size="lg"
            className="h-14 min-w-44 rounded-full"
            onClick={onPrimaryMicPress}
            disabled={!canUseVoice}
            aria-pressed={voiceState === "listening"}
            data-testid="primary-mic"
          >
            {isMuted ? (
              <MicOff data-icon="inline-start" />
            ) : (
              <Mic data-icon="inline-start" />
            )}
            {micLabel}
          </Button>
          <div
            className="h-2 w-full max-w-xs overflow-hidden rounded-full bg-[#E8E2D9]"
            aria-hidden="true"
          >
            <div
              className="h-full bg-[var(--nw-purple)] transition-[width] duration-150"
              style={{ width: `${micLevel}%` }}
              data-testid="mic-level"
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Color alone does not show mic state. The label above does.
          </p>
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {mode === "voice" ? (
          <>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onToggleMute}
              data-testid="toggle-mute"
            >
              {isMuted ? (
                <Mic data-icon="inline-start" />
              ) : (
                <MicOff data-icon="inline-start" />
              )}
              {isMuted ? "Unmute" : "Mute"}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onStopAiAudio}
              disabled={voiceState !== "speaking"}
              data-testid="stop-ai-audio"
            >
              <Square data-icon="inline-start" />
              Stop AI audio
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onSwitchMode("text")}
              data-testid="switch-to-text"
            >
              <Keyboard data-icon="inline-start" />
              Switch to text
            </Button>
          </>
        ) : (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onSwitchMode("voice")}
            data-testid="switch-to-voice"
          >
            <Mic data-icon="inline-start" />
            Switch to voice
          </Button>
        )}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onToggleCaptions}
          data-testid="toggle-captions"
        >
          {captionsEnabled ? (
            <CaptionsOff data-icon="inline-start" />
          ) : (
            <Captions data-icon="inline-start" />
          )}
          {captionsEnabled ? "Hide captions" : "Show captions"}
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onReportConnectionProblem}
          data-testid="report-connection"
        >
          <TriangleAlert data-icon="inline-start" />
          Report connection problem
        </Button>
      </div>
    </div>
  );
}
