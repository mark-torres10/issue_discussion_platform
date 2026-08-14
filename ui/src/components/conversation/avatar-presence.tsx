"use client";

import Image from "next/image";
import { Badge } from "@/components/ui/badge";
import { useUiCopy } from "@/lib/content/content-provider";
import { cn } from "@/lib/utils";
import type { AiPersona, VoiceUiState } from "@/lib/types/session";

interface AvatarPresenceProps {
  persona: AiPersona;
  voiceState?: VoiceUiState;
  size?: "large" | "compact";
  showState?: boolean;
}

/**
 * AI participant avatar with optional speaking/listening state.
 */
export function AvatarPresence({
  persona,
  voiceState = "idle",
  size = "large",
  showState = false,
}: AvatarPresenceProps) {
  const copy = useUiCopy();
  const dimension = size === "large" ? 112 : 64;
  const isSpeaking = voiceState === "speaking";
  const voiceStateLabels: Record<VoiceUiState, string> = {
    idle: copy.conversation.voiceStateReady,
    listening: copy.conversation.voiceStateListening,
    thinking: copy.conversation.voiceStateThinking,
    speaking: copy.conversation.voiceStateSpeaking,
    muted: copy.conversation.voiceStateMuted,
    reconnecting: copy.conversation.voiceStateReconnecting,
  };

  return (
    <div className="flex items-center gap-4">
      <div className="relative shrink-0">
        <div
          className={cn(
            "overflow-hidden rounded-full bg-[#EDE7DE] ring-2 ring-[#D9D0C4]",
            isSpeaking && "ring-[var(--nw-purple)] motion-safe:animate-pulse",
          )}
          style={{ width: dimension, height: dimension }}
        >
          <Image
            src={persona.avatarSrc}
            alt={persona.avatarAlt}
            width={dimension}
            height={dimension}
            className="size-full object-cover"
            priority
          />
        </div>
      </div>
      <div className="min-w-0 flex flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="truncate text-lg font-semibold tracking-tight text-[var(--ink)]">
            {persona.displayName}
          </p>
          <Badge variant="secondary">{persona.isAiLabel}</Badge>
        </div>
        {showState ? (
          <p
            className="text-sm text-muted-foreground"
            aria-live="polite"
            data-testid="voice-state"
          >
            {voiceStateLabels[voiceState]}
          </p>
        ) : null}
      </div>
    </div>
  );
}
