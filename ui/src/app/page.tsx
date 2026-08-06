import Link from "next/link";
import { AppFrame } from "@/components/session/app-frame";
import { buttonVariants } from "@/components/ui/button";
import { SAMPLE_SESSION_ID } from "@/lib/api/study-backend";

export default function HomePage() {
  return (
    <AppFrame>
      <div className="flex flex-col gap-6 px-5 py-8 sm:px-7">
        <div className="flex flex-col gap-3">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--nw-purple)]">
            Research prototype
          </p>
          <h1 className="font-heading text-3xl font-semibold tracking-tight text-[var(--ink)]">
            Issue Discussion Study
          </h1>
          <p className="text-[15px] leading-relaxed text-muted-foreground">
            In the live study, participants open a unique session link. This
            prototype uses fixed sample data so the team can review the
            introduction, audio check, discussion, and completion flow.
          </p>
        </div>
        <ol className="flex flex-col gap-2 text-sm leading-relaxed text-muted-foreground">
          <li>1. Read the introduction and meet the AI participant.</li>
          <li>2. Check microphone and speakers, or continue with text.</li>
          <li>3. Hold a short disagreement conversation.</li>
          <li>4. Confirm that the session was saved.</li>
        </ol>
        <Link
          href={`/session/${SAMPLE_SESSION_ID}`}
          data-testid="open-sample-session"
          className={buttonVariants({
            size: "lg",
            className: "inline-flex w-full",
          })}
        >
          Open sample session
        </Link>
        <p className="text-xs text-muted-foreground">
          Unavailable states:{" "}
          <Link
            className="underline"
            href="/session/expired-demo/unavailable"
          >
            expired
          </Link>
          ,{" "}
          <Link
            className="underline"
            href="/session/completed-demo/unavailable"
          >
            completed
          </Link>
          ,{" "}
          <Link className="underline" href="/session/paused-demo/unavailable">
            paused
          </Link>
          .
        </p>
      </div>
    </AppFrame>
  );
}
