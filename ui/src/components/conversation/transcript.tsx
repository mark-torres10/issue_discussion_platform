"use client";

import { useEffect, useRef } from "react";
import { TranscriptMessageView } from "@/components/conversation/transcript-message";
import type { TranscriptMessage } from "@/lib/types/session";

interface TranscriptProps {
  messages: TranscriptMessage[];
  aiDisplayName: string;
}

/**
 * Scrollable transcript that keeps new turns visible without moving controls.
 */
export function Transcript({ messages, aiDisplayName }: TranscriptProps) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  return (
    <div
      className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-4 py-4"
      role="log"
      aria-live="polite"
      aria-relevant="additions"
      data-testid="transcript"
    >
      {messages.map((message) => (
        <TranscriptMessageView
          key={message.id}
          message={message}
          aiDisplayName={aiDisplayName}
        />
      ))}
      <div ref={endRef} />
    </div>
  );
}
