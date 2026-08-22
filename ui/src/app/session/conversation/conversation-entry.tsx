"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ConversationShell } from "@/components/conversation/conversation-shell";
import { PARTICIPANT_ROUTES } from "@/lib/api/study-backend";
import { startParticipantSessionAction } from "@/lib/api/study-backend-client";
import { useUiCopy } from "@/lib/content/content-provider";
import {
  parseAudioCheckPreferences,
  audioCheckStorageKey,
} from "@/lib/session/audio-check-storage";
import {
  conversationStorageKey,
  createConversationSnapshot,
  serializeConversationSnapshot,
} from "@/lib/realtime/state";
import type { ConversationMode, StudySession } from "@/lib/types/session";

interface ConversationEntryProps {
  session: StudySession;
}

/**
 * Prime session start and sessionStorage before ConversationShell mounts.
 */
export function ConversationEntry({ session }: ConversationEntryProps) {
  const copy = useUiCopy();
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const storageKey = conversationStorageKey(session.sessionId);
    if (sessionStorage.getItem(storageKey)) {
      setReady(true);
      return;
    }

    const audioRaw = sessionStorage.getItem(
      audioCheckStorageKey(session.sessionId),
    );
    const preferences = audioRaw
      ? parseAudioCheckPreferences(audioRaw)
      : null;
    const mode: ConversationMode =
      preferences?.mode ?? session.preferredMode ?? "text";

    void (async () => {
      try {
        const started = await startParticipantSessionAction(
          mode,
          session.version ?? 1,
          `start-${session.sessionId}`,
        );
        const openingText =
          (session.aiSpeaksFirst ?? true) && started.opening_turn
            ? started.opening_turn.display_text
            : "";
        const initial = createConversationSnapshot(
          session.sessionId,
          openingText,
          mode,
        );
        sessionStorage.setItem(storageKey, serializeConversationSnapshot(initial));
        setReady(true);
      } catch {
        setFailed(true);
      }
    })();
  }, [
    session.aiSpeaksFirst,
    session.preferredMode,
    session.sessionId,
    session.version,
  ]);

  if (failed) {
    router.replace(PARTICIPANT_ROUTES.unavailable);
    return (
      <div className="px-5 py-8 text-sm text-muted-foreground">
        {copy.unavailable.invalid.body}
      </div>
    );
  }

  if (!ready) {
    return (
      <div className="px-5 py-8 text-sm text-muted-foreground">
        {copy.conversation.loading}
      </div>
    );
  }

  return <ConversationShell session={session} />;
}
