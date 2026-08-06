import Link from "next/link";
import { AppFrame } from "@/components/session/app-frame";
import { buttonVariants } from "@/components/ui/button";
import { getStudySession } from "@/lib/api/study-backend";

interface UnavailablePageProps {
  params: Promise<{ sessionId: string }>;
}

const STATUS_COPY: Record<string, { title: string; body: string }> = {
  expired: {
    title: "This session has expired",
    body: "The study link is no longer active. Contact the research team if you believe this is a mistake.",
  },
  completed: {
    title: "This session is already complete",
    body: "You have already finished this conversation. Return to the study survey for the next step.",
  },
  paused: {
    title: "This session is paused",
    body: "The research team has temporarily paused this session. Please wait for further instructions.",
  },
  invalid: {
    title: "This session is unavailable",
    body: "The study link is invalid or cannot be opened right now.",
  },
};

export default async function UnavailablePage({
  params,
}: UnavailablePageProps) {
  const { sessionId } = await params;
  const session = getStudySession(sessionId);
  const status = session?.status ?? "invalid";
  const copy = STATUS_COPY[status] ?? STATUS_COPY.invalid;

  return (
    <AppFrame>
      <div className="flex flex-col gap-5 px-5 py-8 sm:px-7">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--ink)]">
            {copy.title}
          </h1>
          <p className="text-[15px] leading-relaxed text-muted-foreground">
            {copy.body}
          </p>
        </div>
        <Link
          href="/"
          className={buttonVariants({ variant: "outline" })}
        >
          Back to prototype home
        </Link>
      </div>
    </AppFrame>
  );
}
