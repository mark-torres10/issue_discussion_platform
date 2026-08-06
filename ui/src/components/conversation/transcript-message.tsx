"use client";

import { cn } from "@/lib/utils";
import type { TranscriptMessage } from "@/lib/types/session";

interface TranscriptMessageProps {
  message: TranscriptMessage;
  aiDisplayName: string;
}

/**
 * Single transcript turn with speaker distinction.
 */
export function TranscriptMessageView({
  message,
  aiDisplayName,
}: TranscriptMessageProps) {
  const isAi = message.speaker === "ai";

  return (
    <article
      className={cn(
        "flex flex-col gap-1 rounded-xl px-3 py-2.5",
        isAi ? "bg-[#F4F0EA]" : "bg-[var(--nw-purple-soft)]",
      )}
      data-speaker={message.speaker}
      aria-label={`${isAi ? aiDisplayName : "You"}: ${message.text}`}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {isAi ? aiDisplayName : "You"}
        {message.isPartial ? " · typing" : ""}
      </p>
      <p className="text-[15px] leading-relaxed text-[var(--ink)] whitespace-pre-wrap">
        {message.text || (message.isPartial ? "…" : "")}
      </p>
    </article>
  );
}
