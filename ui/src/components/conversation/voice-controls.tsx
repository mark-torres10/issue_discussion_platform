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
import { useUiCopy } from "@/lib/content/content-provider";
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
  const copy = useUiCopy();
  const micLabel =
    voiceState === "listening"
      ? copy.conversation.microphoneOn
      : voiceState === "muted"
        ? copy.conversation.microphoneMuted
        : copy.conversation.microphone;

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
            {copy.conversation.micColorHint}
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
              {isMuted ? copy.conversation.unmute : copy.conversation.mute}
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
              {copy.conversation.stopAiAudio}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onSwitchMode("text")}
              data-testid="switch-to-text"
            >
              <Keyboard data-icon="inline-start" />
              {copy.conversation.switchToText}
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
            {copy.conversation.switchToVoice}
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
          {captionsEnabled
            ? copy.conversation.hideCaptions
            : copy.conversation.showCaptions}
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onReportConnectionProblem}
          data-testid="report-connection"
        >
          <TriangleAlert data-icon="inline-start" />
          {copy.conversation.reportConnectionProblem}
        </Button>
      </div>
    </div>
  );
}
