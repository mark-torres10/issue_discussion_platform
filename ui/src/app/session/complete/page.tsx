import { Suspense } from "react";
import { redirect } from "next/navigation";
import CompletePageClient from "../[sessionId]/complete/complete-client";
import {
  PARTICIPANT_ROUTES,
} from "@/lib/api/study-backend";
import { fetchParticipantSession } from "@/lib/api/study-backend-client";
import { loadUiCopy } from "@/lib/content/loader";

export default async function CompletePage() {
  const session = await fetchParticipantSession();
  if (!session) {
    redirect(PARTICIPANT_ROUTES.unavailable);
  }

  const copy = loadUiCopy();

  return (
    <Suspense
      fallback={
        <div className="px-5 py-8 text-sm text-muted-foreground">
          {copy.complete.loading}
        </div>
      }
    >
      <CompletePageClient session={session} />
    </Suspense>
  );
}
