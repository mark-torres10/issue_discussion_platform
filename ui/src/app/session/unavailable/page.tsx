import Link from "next/link";
import { AppFrame } from "@/components/session/app-frame";
import { buttonVariants } from "@/components/ui/button";
import { fetchParticipantSession } from "@/lib/api/study-backend-client";
import { loadUiCopy } from "@/lib/content/loader";
import type { SessionStatus } from "@/lib/types/session";

const UNAVAILABLE_STATUSES = new Set<SessionStatus>([
  "expired",
  "completed",
  "paused",
  "invalid",
]);

export default async function UnavailablePage() {
  const session = await fetchParticipantSession();
  const copy = loadUiCopy();
  const status = session?.status ?? "invalid";
  const statusCopy = UNAVAILABLE_STATUSES.has(status)
    ? copy.unavailable[status as "expired" | "completed" | "paused" | "invalid"]
    : copy.unavailable.invalid;

  return (
    <AppFrame>
      <div className="flex flex-col gap-5 px-5 py-8 sm:px-7">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--ink)]">
            {statusCopy.title}
          </h1>
          <p className="text-[15px] leading-relaxed text-muted-foreground">
            {statusCopy.body}
          </p>
        </div>
        <Link href="/" className={buttonVariants({ variant: "outline" })}>
          {copy.unavailable.backHome}
        </Link>
      </div>
    </AppFrame>
  );
}
