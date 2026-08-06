"use client";

import Link from "next/link";
import { AvatarPresence } from "@/components/conversation/avatar-presence";
import { buttonVariants } from "@/components/ui/button";
import type { StudySession } from "@/lib/types/session";

interface ParticipantIntroductionProps {
  session: StudySession;
}

/**
 * Introduction and AI participant preview before the audio check.
 */
export function ParticipantIntroduction({
  session,
}: ParticipantIntroductionProps) {
  return (
    <div className="flex flex-col gap-6 px-5 py-6 sm:px-7 sm:py-8">
      <div className="flex flex-col gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-[var(--nw-purple)]">
          Study conversation
        </p>
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--ink)]">
          Before you begin
        </h1>
        <p className="text-[15px] leading-relaxed text-muted-foreground">
          You will have a short conversation with an AI participant about a
          contested issue. The discussion usually lasts about{" "}
          {session.rules.durationMinutes} minutes. You can use voice or text,
          and you can end the conversation at any time.
        </p>
      </div>

      <section className="flex flex-col gap-3" aria-labelledby="issue-heading">
        <h2
          id="issue-heading"
          className="text-sm font-semibold text-[var(--ink)]"
        >
          The issue
        </h2>
        <p className="text-[15px] font-medium leading-snug text-[var(--ink)]">
          {session.issue.title}
        </p>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {session.issue.summary}
        </p>
      </section>

      <section
        className="flex flex-col gap-4 rounded-xl bg-[#F7F3EE] px-4 py-4"
        aria-labelledby="ai-heading"
      >
        <h2
          id="ai-heading"
          className="text-sm font-semibold text-[var(--ink)]"
        >
          Meet the AI participant
        </h2>
        <AvatarPresence persona={session.aiPersona} size="large" />
        <p className="text-sm leading-relaxed text-muted-foreground">
          {session.aiPersona.shortIntroduction}
        </p>
        <div className="flex flex-col gap-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Assigned position
          </p>
          <p className="text-sm leading-relaxed text-[var(--ink)]">
            {session.aiPersona.assignedPosition}
          </p>
        </div>
      </section>

      <ul className="flex flex-col gap-2 text-sm leading-relaxed text-muted-foreground">
        <li>
          The study saves a transcript and the measures approved by the study
          protocol.
        </li>
        <li>Formal consent, if required, remains a separate study step.</li>
        <li>
          Headphones can reduce echo if you choose voice mode on the next
          screen.
        </li>
      </ul>

      <Link
        href={`/session/${session.sessionId}/audio-check`}
        className={buttonVariants({ size: "lg", className: "w-full" })}
        data-testid="continue-to-audio-check"
      >
        Continue to audio check
      </Link>
    </div>
  );
}
