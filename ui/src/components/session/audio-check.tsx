"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  audioCheckStorageKey,
  type AudioCheckPreferences,
} from "@/lib/session/audio-check-storage";
import {
  playTestTone,
  queryMicrophonePermission,
  requestMicrophoneAccess,
  stopMediaStream,
} from "@/lib/realtime/microphone";
import { amplitudeToLevelPercent } from "@/lib/realtime/state";
import type { ConversationMode, MicPermissionStatus } from "@/lib/types/session";

const TEST_TONE_DURATION_MS = 450;
const TEST_TONE_FREQUENCY_HZ = 528;
const LEVEL_POLL_MS = 100;

interface AudioCheckProps {
  sessionId: string;
}

/**
 * Microphone and speaker check before the discussion begins.
 */
export function AudioCheck({ sessionId }: AudioCheckProps) {
  const router = useRouter();
  const [mode, setMode] = useState<ConversationMode>("voice");
  const [micPermission, setMicPermission] =
    useState<MicPermissionStatus>("prompt");
  const [micLevel, setMicLevel] = useState(0);
  const [micReady, setMicReady] = useState(false);
  const [speakerReady, setSpeakerReady] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const levelTimerRef = useRef<number | null>(null);

  useEffect(() => {
    void queryMicrophonePermission(navigator.permissions).then(setMicPermission);

    return () => {
      if (levelTimerRef.current !== null) {
        window.clearInterval(levelTimerRef.current);
      }
      stopMediaStream(streamRef.current);
      void audioContextRef.current?.close();
    };
  }, []);

  function persistAndContinue(preferences: AudioCheckPreferences) {
    sessionStorage.setItem(
      audioCheckStorageKey(sessionId),
      JSON.stringify(preferences),
    );
    stopMediaStream(streamRef.current);
    streamRef.current = null;
    router.push(`/session/${sessionId}/conversation`);
  }

  function startLevelMeter(stream: MediaStream) {
    const AudioContextCtor = window.AudioContext;
    const context = new AudioContextCtor();
    const source = context.createMediaStreamSource(stream);
    const analyser = context.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    audioContextRef.current = context;
    analyserRef.current = analyser;

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

  async function handleEnableMicrophone() {
    setErrorMessage(null);
    const result = await requestMicrophoneAccess(navigator.mediaDevices);
    setMicPermission(result.status);
    if (result.status !== "granted" || !result.stream) {
      setMicReady(false);
      setErrorMessage(result.errorMessage);
      return;
    }

    stopMediaStream(streamRef.current);
    streamRef.current = result.stream;
    setMicReady(true);
    startLevelMeter(result.stream);
  }

  async function handlePlayTestSound() {
    setErrorMessage(null);
    try {
      await playTestTone(
        window.AudioContext,
        TEST_TONE_DURATION_MS,
        TEST_TONE_FREQUENCY_HZ,
      );
      setSpeakerReady(true);
    } catch {
      setSpeakerReady(false);
      setErrorMessage(
        "Could not play a test sound. Check your speakers or continue with text.",
      );
    }
  }

  function handleContinueWithText() {
    persistAndContinue({
      mode: "text",
      micReady: false,
      speakerReady: false,
    });
  }

  function handleStartDiscussion() {
    if (mode === "text") {
      handleContinueWithText();
      return;
    }
    persistAndContinue({
      mode: "voice",
      micReady,
      speakerReady,
    });
  }

  const canStartVoice = micReady;

  return (
    <div className="flex flex-col gap-6 px-5 py-6 sm:px-7 sm:py-8">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--ink)]">
          Check your audio
        </h1>
        <p className="text-[15px] leading-relaxed text-muted-foreground">
          Choose voice or text. Microphone access is requested only after you
          press the button below. Audio from this check is not saved.
        </p>
      </div>

      <div className="flex gap-2" role="group" aria-label="Conversation mode">
        <Button
          type="button"
          variant={mode === "voice" ? "default" : "outline"}
          onClick={() => setMode("voice")}
          data-testid="select-voice"
        >
          Voice
        </Button>
        <Button
          type="button"
          variant={mode === "text" ? "default" : "outline"}
          onClick={() => setMode("text")}
          data-testid="select-text"
        >
          Text
        </Button>
      </div>

      {mode === "voice" ? (
        <div className="flex flex-col gap-4">
          <p className="text-sm text-muted-foreground">
            Headphones can reduce echo. Speak after enabling the microphone to
            confirm input level.
          </p>
          <Button
            type="button"
            onClick={() => void handleEnableMicrophone()}
            data-testid="enable-microphone"
          >
            Enable microphone
          </Button>
          <div className="flex flex-col gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Input level
            </p>
            <div className="h-3 overflow-hidden rounded-full bg-[#E8E2D9]">
              <div
                className="h-full bg-[var(--nw-purple)] transition-[width] duration-150"
                style={{ width: `${micLevel}%` }}
                data-testid="audio-check-level"
              />
            </div>
            <p className="text-sm text-muted-foreground" data-testid="mic-status">
              Microphone status: {micPermission}
              {micReady ? " · ready" : ""}
            </p>
          </div>
          <Button
            type="button"
            variant="outline"
            onClick={() => void handlePlayTestSound()}
            data-testid="play-test-sound"
          >
            Play test sound
          </Button>
          <p className="text-sm text-muted-foreground">
            Speaker check: {speakerReady ? "heard" : "not confirmed yet"}
          </p>
        </div>
      ) : (
        <p className="text-sm leading-relaxed text-muted-foreground">
          Text mode uses a message box. You can switch to voice later from the
          discussion screen if your microphone becomes available.
        </p>
      )}

      {errorMessage ? (
        <Alert variant="destructive">
          <AlertTitle>Audio check issue</AlertTitle>
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      ) : null}

      <div className="flex flex-col gap-2">
        <Button
          type="button"
          size="lg"
          onClick={handleStartDiscussion}
          disabled={mode === "voice" && !canStartVoice}
          data-testid="start-discussion"
        >
          Start discussion
        </Button>
        {mode === "voice" ? (
          <Button
            type="button"
            variant="outline"
            onClick={handleContinueWithText}
            data-testid="continue-with-text"
          >
            Continue with text instead
          </Button>
        ) : null}
      </div>
    </div>
  );
}
