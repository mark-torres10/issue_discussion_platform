import Link from "next/link";
import { AppFrame } from "@/components/session/app-frame";
import { buttonVariants } from "@/components/ui/button";
import { SAMPLE_SESSION_ID } from "@/lib/api/study-backend";
import { loadUiCopy } from "@/lib/content/loader";

export default function HomePage() {
  const copy = loadUiCopy();

  return (
    <AppFrame>
      <div className="flex flex-col gap-6 px-5 py-8 sm:px-7">
        <div className="flex flex-col gap-3">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--nw-purple)]">
            {copy.home.eyebrow}
          </p>
          <h1 className="font-heading text-3xl font-semibold tracking-tight text-[var(--ink)]">
            {copy.home.heading}
          </h1>
          <p className="text-[15px] leading-relaxed text-muted-foreground">
            {copy.home.body}
          </p>
        </div>
        <ol className="flex flex-col gap-2 text-sm leading-relaxed text-muted-foreground">
          <li>{copy.home.step1}</li>
          <li>{copy.home.step2}</li>
          <li>{copy.home.step3}</li>
          <li>{copy.home.step4}</li>
        </ol>
        <Link
          href={`/session/${SAMPLE_SESSION_ID}`}
          data-testid="open-sample-session"
          className={buttonVariants({
            size: "lg",
            className: "inline-flex w-full",
          })}
        >
          {copy.home.openSampleSession}
        </Link>
        <p className="text-xs text-muted-foreground">
          {copy.home.unavailablePrefix}
          <Link
            className="underline"
            href="/session/expired-demo/unavailable"
          >
            {copy.home.expiredLinkLabel}
          </Link>
          ,{" "}
          <Link
            className="underline"
            href="/session/completed-demo/unavailable"
          >
            {copy.home.completedLinkLabel}
          </Link>
          ,{" "}
          <Link className="underline" href="/session/paused-demo/unavailable">
            {copy.home.pausedLinkLabel}
          </Link>
          .
        </p>
      </div>
    </AppFrame>
  );
}
