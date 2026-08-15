"use client";

import Link from "next/link";
import { AvatarPresence } from "@/components/conversation/avatar-presence";
import { buttonVariants } from "@/components/ui/button";
import { useUiCopy } from "@/lib/content/content-provider";
import type { StudySession } from "@/lib/types/session";

const DURATION_TOKEN = "{durationMinutes}";

interface ParticipantIntroductionProps {
  session: StudySession;
}

/**
 * Introduction and AI participant preview before the audio check.
 */
export function ParticipantIntroduction({
  session,
}: ParticipantIntroductionProps) {
  const copy = useUiCopy();
  const body = copy.introduction.body.replace(
    DURATION_TOKEN,
    String(session.rules.durationMinutes),
  );

  return (
    <div className="flex flex-col gap-6 px-5 py-6 sm:px-7 sm:py-8">
      <div className="flex flex-col gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-[var(--nw-purple)]">
          {copy.introduction.eyebrow}
        </p>
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--ink)]">
          {copy.introduction.heading}
        </h1>
        <p className="text-[15px] leading-relaxed text-muted-foreground">
          {body}
        </p>
      </div>

      <section className="flex flex-col gap-3" aria-labelledby="issue-heading">
        <h2
          id="issue-heading"
          className="text-sm font-semibold text-[var(--ink)]"
        >
          {copy.introduction.issueHeading}
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
          {copy.introduction.meetAiHeading}
        </h2>
        <AvatarPresence persona={session.aiPersona} size="large" />
        <p className="text-sm leading-relaxed text-muted-foreground">
          {session.aiPersona.shortIntroduction}
        </p>
        <div className="flex flex-col gap-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {copy.introduction.assignedPositionLabel}
          </p>
          <p className="text-sm leading-relaxed text-[var(--ink)]">
            {session.aiPersona.assignedPosition}
          </p>
        </div>
      </section>

      <ul className="flex flex-col gap-2 text-sm leading-relaxed text-muted-foreground">
        <li>{copy.introduction.noteTranscript}</li>
        <li>{copy.introduction.noteConsent}</li>
        <li>{copy.introduction.noteHeadphones}</li>
      </ul>

      <Link
        href={`/session/${session.sessionId}/audio-check`}
        className={buttonVariants({ size: "lg", className: "w-full" })}
        data-testid="continue-to-audio-check"
      >
        {copy.introduction.continueButton}
      </Link>
    </div>
  );
}
