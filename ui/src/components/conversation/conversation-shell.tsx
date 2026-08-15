"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AvatarPresence } from "@/components/conversation/avatar-presence";
import { SessionHeader } from "@/components/conversation/session-header";
import { TextComposer } from "@/components/conversation/text-composer";
import { Transcript } from "@/components/conversation/transcript";
import { VoiceControls } from "@/components/conversation/voice-controls";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  parseAudioCheckPreferences,
  audioCheckStorageKey,
} from "@/lib/session/audio-check-storage";
import {
  appendParticipantMessage,
  beginAiStreamingReply,
  conversationStorageKey,
  countParticipantTurns,
  createConversationSnapshot,
  finalizeAiStreamingReply,
  parseConversationSnapshot,
  resolveVoiceStateAfterControls,
  selectScriptedAiReply,
  serializeConversationSnapshot,
  updateAiStreamingReply,
} from "@/lib/realtime/state";
import {
  requestMicrophoneAccess,
  stopMediaStream,
} from "@/lib/realtime/microphone";
import { amplitudeToLevelPercent } from "@/lib/realtime/state";
import { useUiCopy } from "@/lib/content/content-provider";
import type {
  ConversationMode,
  ConversationSnapshot,
  MicPermissionStatus,
  StudySession,
  VoiceUiState,
} from "@/lib/types/session";

const STREAM_CHUNK_CHARS = 4;
const STREAM_TICK_MS = 28;
const THINKING_DELAY_MS = 650;
const LEVEL_POLL_MS = 120;
const TIMER_TICK_MS = 1000;

interface ConversationShellProps {
  session: StudySession;
}

/**
 * Interactive discussion surface with mocked backend behavior.
 */
export function ConversationShell({ session }: ConversationShellProps) {
  const copy = useUiCopy();
  const router = useRouter();
  const [snapshot, setSnapshot] = useState<ConversationSnapshot | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isMuted, setIsMuted] = useState(false);
  const [micLevel, setMicLevel] = useState(0);
  const [endDialogOpen, setEndDialogOpen] = useState(false);
  const [nearEndNoticed, setNearEndNoticed] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const replyTimerRef = useRef<number | null>(null);
  const streamTimerRef = useRef<number | null>(null);
  const levelTimerRef = useRef<number | null>(null);
  const completeSessionRef = useRef<
    ((reason: "user_ended" | "time_expired") => Promise<void>) | null
  >(null);

  const persistSnapshot = useCallback((next: ConversationSnapshot) => {
    sessionStorage.setItem(
      conversationStorageKey(session.sessionId),
      serializeConversationSnapshot(next),
    );
    setSnapshot(next);
  }, [session.sessionId]);

  useEffect(() => {
    const storedConversation = sessionStorage.getItem(
      conversationStorageKey(session.sessionId),
    );
    if (storedConversation) {
      const parsed = parseConversationSnapshot(storedConversation);
      if (parsed) {
        // Hydrate from sessionStorage after mount (refresh recovery).
        // eslint-disable-next-line react-hooks/set-state-in-effect -- intentional client hydration
        setSnapshot(parsed);
        if (parsed.startedAt) {
          const startedMs = Date.parse(parsed.startedAt);
          setElapsedSeconds(
            Number.isNaN(startedMs)
              ? 0
              : Math.floor((Date.now() - startedMs) / 1000),
          );
        }
        return;
      }
    }

    const audioRaw = sessionStorage.getItem(
      audioCheckStorageKey(session.sessionId),
    );
    const preferences = audioRaw
      ? parseAudioCheckPreferences(audioRaw)
      : null;
    const mode: ConversationMode = preferences?.mode ?? "text";
    const initial = createConversationSnapshot(
      session.sessionId,
      session.openingAiMessage,
      mode,
    );
    persistSnapshot(initial);
  }, [persistSnapshot, session.openingAiMessage, session.sessionId]);

  useEffect(() => {
    if (!snapshot?.startedAt || snapshot.endedAt) {
      return;
    }

    const startedAt = snapshot.startedAt;
    const timerId = window.setInterval(() => {
      const startedMs = Date.parse(startedAt);
      if (Number.isNaN(startedMs)) {
        return;
      }
      const nextElapsed = Math.floor((Date.now() - startedMs) / 1000);
      setElapsedSeconds(nextElapsed);

      const totalSeconds = session.rules.durationMinutes * 60;
      const remaining = totalSeconds - nextElapsed;
      if (remaining <= session.rules.warningBeforeEndSeconds && remaining > 0) {
        setNearEndNoticed(true);
      }
      if (remaining <= 0) {
        void completeSessionRef.current?.("time_expired");
      }
    }, TIMER_TICK_MS);

    return () => window.clearInterval(timerId);
  }, [
    snapshot?.startedAt,
    snapshot?.endedAt,
    session.rules.durationMinutes,
    session.rules.warningBeforeEndSeconds,
  ]);

  useEffect(() => {
    return () => {
      if (replyTimerRef.current !== null) {
        window.clearTimeout(replyTimerRef.current);
      }
      if (streamTimerRef.current !== null) {
        window.clearInterval(streamTimerRef.current);
      }
      if (levelTimerRef.current !== null) {
        window.clearInterval(levelTimerRef.current);
      }
      stopMediaStream(streamRef.current);
    };
  }, []);

  function clearReplyTimers() {
    if (replyTimerRef.current !== null) {
      window.clearTimeout(replyTimerRef.current);
      replyTimerRef.current = null;
    }
    if (streamTimerRef.current !== null) {
      window.clearInterval(streamTimerRef.current);
      streamTimerRef.current = null;
    }
  }

  function startMicLevelMeter(stream: MediaStream) {
    if (levelTimerRef.current !== null) {
      window.clearInterval(levelTimerRef.current);
    }
    const context = new window.AudioContext();
    const source = context.createMediaStreamSource(stream);
    const analyser = context.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    const data = new Uint8Array(analyser.frequencyBinCount);

    levelTimerRef.current = window.setInterval(() => {
      analyser.getByteTimeDomainData(data);
      let sumSquares = 0;
      for (const value of data) {
        const normalized = (value - 128) / 128;
        sumSquares += normalized * normalized;
      }
      const rms = Math.sqrt(sumSquares / data.length);
      setMicLevel(amplitudeToLevelPercent(Math.min(1, rms * 4)));
    }, LEVEL_POLL_MS);
  }

  async function ensureMicrophone(
    nextPermissionHint?: MicPermissionStatus,
  ): Promise<boolean> {
    if (!snapshot) {
      return false;
    }
    if (streamRef.current) {
      return true;
    }

    const result = await requestMicrophoneAccess(navigator.mediaDevices);
    const nextPermission = nextPermissionHint ?? result.status;
    persistSnapshot({
      ...snapshot,
      micPermission: nextPermission,
      voiceState: resolveVoiceStateAfterControls(
        snapshot.mode,
        isMuted,
        nextPermission,
      ),
    });

    if (result.status !== "granted" || !result.stream) {
      setErrorMessage(result.errorMessage);
      return false;
    }

    streamRef.current = result.stream;
    startMicLevelMeter(result.stream);
    setErrorMessage(null);
    return true;
  }

  function streamAiReply(current: ConversationSnapshot, replyText: string) {
    const messageId = `msg-ai-${Date.now()}`;
    let withPartial = beginAiStreamingReply(current, messageId);
    persistSnapshot(withPartial);

    let cursor = 0;
    streamTimerRef.current = window.setInterval(() => {
      cursor = Math.min(replyText.length, cursor + STREAM_CHUNK_CHARS);
      const nextText = replyText.slice(0, cursor);
      withPartial = updateAiStreamingReply(withPartial, messageId, nextText);
      persistSnapshot(withPartial);

      if (cursor >= replyText.length) {
        clearReplyTimers();
        const nextVoiceState = resolveVoiceStateAfterControls(
          withPartial.mode,
          isMuted,
          withPartial.micPermission,
        );
        const finalized = finalizeAiStreamingReply(
          withPartial,
          messageId,
          replyText,
          nextVoiceState,
        );
        persistSnapshot(finalized);
      }
    }, STREAM_TICK_MS);
  }

  function handleParticipantTurn(text: string) {
    if (!snapshot || snapshot.endedAt) {
      return;
    }
    if (
      snapshot.voiceState === "thinking" ||
      snapshot.voiceState === "speaking"
    ) {
      return;
    }

    clearReplyTimers();
    const messageId = `msg-participant-${Date.now()}`;
    const withParticipant = appendParticipantMessage(snapshot, text, messageId);
    persistSnapshot(withParticipant);

    const participantTurns = countParticipantTurns(withParticipant.messages);
    const replyText = selectScriptedAiReply(
      session.scriptedAiReplies,
      participantTurns,
    );

    replyTimerRef.current = window.setTimeout(() => {
      streamAiReply(withParticipant, replyText);
    }, THINKING_DELAY_MS);
  }

  function handlePrimaryMicPress() {
    if (!snapshot) {
      return;
    }
    if (snapshot.mode !== "voice") {
      return;
    }
    if (isMuted) {
      setIsMuted(false);
      persistSnapshot({
        ...snapshot,
        voiceState: "listening",
      });
      return;
    }
    void ensureMicrophone();
  }

  function handleToggleMute() {
    if (!snapshot) {
      return;
    }
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    persistSnapshot({
      ...snapshot,
      voiceState: resolveVoiceStateAfterControls(
        snapshot.mode,
        nextMuted,
        snapshot.micPermission,
      ),
    });
  }

  function handleStopAiAudio() {
    if (!snapshot || snapshot.voiceState !== "speaking") {
      return;
    }
    clearReplyTimers();
    const messages = snapshot.messages.map((message) =>
      message.isPartial ? { ...message, isPartial: false } : message,
    );
    persistSnapshot({
      ...snapshot,
      voiceState: resolveVoiceStateAfterControls(
        snapshot.mode,
        isMuted,
        snapshot.micPermission,
      ),
      messages,
    });
  }

  async function handleSwitchMode(mode: ConversationMode) {
    if (!snapshot) {
      return;
    }
    if (mode === "voice") {
      const granted = await ensureMicrophone();
      if (!granted) {
        return;
      }
    } else {
      stopMediaStream(streamRef.current);
      streamRef.current = null;
      setMicLevel(0);
    }

    const nextPermission = snapshot.micPermission;
    persistSnapshot({
      ...snapshot,
      mode,
      voiceState: resolveVoiceStateAfterControls(mode, isMuted, nextPermission),
    });
  }

  function handleReportConnectionProblem() {
    if (!snapshot) {
      return;
    }
    persistSnapshot({
      ...snapshot,
      voiceState: "reconnecting" satisfies VoiceUiState,
    });
    window.setTimeout(() => {
      setSnapshot((current) => {
        if (!current) {
          return current;
        }
        const restored: ConversationSnapshot = {
          ...current,
          voiceState: resolveVoiceStateAfterControls(
            current.mode,
            isMuted,
            current.micPermission,
          ),
        };
        sessionStorage.setItem(
          conversationStorageKey(session.sessionId),
          serializeConversationSnapshot(restored),
        );
        return restored;
      });
    }, 1600);
  }

  const completeSession = useCallback(
    async (reason: "user_ended" | "time_expired") => {
      if (!snapshot) {
        return;
      }
      clearReplyTimers();
      stopMediaStream(streamRef.current);
      streamRef.current = null;

      const saving: ConversationSnapshot = {
        ...snapshot,
        endedAt: new Date().toISOString(),
        saveStatus: "saving",
        voiceState: "idle",
      };
      persistSnapshot(saving);

      await new Promise((resolve) => window.setTimeout(resolve, 400));
      const saved: ConversationSnapshot = {
        ...saving,
        saveStatus: "saved",
      };
      persistSnapshot(saved);
      router.push(`/session/${session.sessionId}/complete?reason=${reason}`);
    },
    [persistSnapshot, router, session.sessionId, snapshot],
  );

  useEffect(() => {
    completeSessionRef.current = completeSession;
  }, [completeSession]);

  if (!snapshot) {
    return (
      <div className="px-5 py-8 text-sm text-muted-foreground">
        {copy.conversation.loading}
      </div>
    );
  }

  const captionsVisible = snapshot.captionsEnabled || snapshot.mode === "text";

  return (
    <div className="flex h-[min(760px,calc(100dvh-3rem))] flex-col">
      <SessionHeader
        issueTitle={session.issue.title}
        elapsedSeconds={elapsedSeconds}
        durationMinutes={session.rules.durationMinutes}
        warningBeforeEndSeconds={session.rules.warningBeforeEndSeconds}
        voiceState={snapshot.voiceState}
        onEndConversation={() => setEndDialogOpen(true)}
      />

      <div className="border-b border-black/5 px-4 py-3">
        <AvatarPresence
          persona={session.aiPersona}
          voiceState={snapshot.voiceState}
          size={snapshot.messages.length > 2 ? "compact" : "large"}
          showState
        />
      </div>

      {nearEndNoticed ? (
        <Alert className="mx-4 mt-3">
          <AlertTitle>{copy.conversation.almostCompleteTitle}</AlertTitle>
          <AlertDescription>
            {copy.conversation.almostCompleteBody}
          </AlertDescription>
        </Alert>
      ) : null}

      {errorMessage ? (
        <Alert variant="destructive" className="mx-4 mt-3">
          <AlertTitle>{copy.conversation.microphoneIssueTitle}</AlertTitle>
          <AlertDescription>
            {errorMessage}{" "}
            <button
              type="button"
              className="underline"
              onClick={() => void handleSwitchMode("text")}
            >
              {copy.conversation.continueWithText}
            </button>
          </AlertDescription>
        </Alert>
      ) : null}

      {captionsVisible ? (
        <Transcript
          messages={snapshot.messages}
          aiDisplayName={session.aiPersona.displayName}
        />
      ) : (
        <div className="flex flex-1 items-center justify-center px-4 text-sm text-muted-foreground">
          {copy.conversation.captionsHidden}
        </div>
      )}

      <div className="flex flex-col gap-2">
        {snapshot.mode === "text" || !captionsVisible ? (
          <div className="px-4 pt-2">
            <TextComposer
              disabled={
                snapshot.voiceState === "thinking" ||
                snapshot.voiceState === "speaking" ||
                Boolean(snapshot.endedAt)
              }
              onSend={handleParticipantTurn}
            />
          </div>
        ) : null}
        {snapshot.mode === "voice" && captionsVisible ? (
          <div className="px-4 pt-2">
            <TextComposer
              disabled={
                snapshot.voiceState === "thinking" ||
                snapshot.voiceState === "speaking" ||
                Boolean(snapshot.endedAt)
              }
              onSend={handleParticipantTurn}
            />
          </div>
        ) : null}
        <VoiceControls
          mode={snapshot.mode}
          voiceState={snapshot.voiceState}
          isMuted={isMuted}
          captionsEnabled={snapshot.captionsEnabled}
          micLevel={micLevel}
          canUseVoice={snapshot.micPermission !== "unavailable"}
          onToggleMute={handleToggleMute}
          onStopAiAudio={handleStopAiAudio}
          onSwitchMode={(mode) => void handleSwitchMode(mode)}
          onToggleCaptions={() =>
            persistSnapshot({
              ...snapshot,
              captionsEnabled: !snapshot.captionsEnabled,
            })
          }
          onReportConnectionProblem={handleReportConnectionProblem}
          onPrimaryMicPress={handlePrimaryMicPress}
        />
      </div>

      <Dialog open={endDialogOpen} onOpenChange={setEndDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{copy.conversation.endDialogTitle}</DialogTitle>
            <DialogDescription>
              {copy.conversation.endDialogDescription}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setEndDialogOpen(false)}
            >
              {copy.conversation.keepTalking}
            </Button>
            <Button
              type="button"
              onClick={() => void completeSession("user_ended")}
              data-testid="confirm-end"
            >
              {copy.conversation.endConversationConfirm}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
