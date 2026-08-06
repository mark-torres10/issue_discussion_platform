"use client";

import { useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { AppFrame } from "@/components/session/app-frame";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { getStudySession } from "@/lib/api/study-backend";
import {
  conversationStorageKey,
  parseConversationSnapshot,
} from "@/lib/realtime/state";
import type { ConversationSnapshot } from "@/lib/types/session";

/**
 * Completion confirmation with mocked save status and next-step instruction.
 */
export default function CompletePageClient() {
  const params = useParams<{ sessionId: string }>();
  const searchParams = useSearchParams();
  const sessionId = params.sessionId;
  const reason = searchParams.get("reason");
  const session = getStudySession(sessionId);
  const [snapshot, setSnapshot] = useState<ConversationSnapshot | null>(() => {
    if (typeof window === "undefined") {
      return null;
    }
    const raw = sessionStorage.getItem(conversationStorageKey(sessionId));
    if (!raw) {
      return null;
    }
    return parseConversationSnapshot(raw);
  });
  const [retrying, setRetrying] = useState(false);

  async function handleRetrySave() {
    if (!snapshot) {
      return;
    }
    setRetrying(true);
    const retryingSnapshot: ConversationSnapshot = {
      ...snapshot,
      saveStatus: "retrying",
    };
    sessionStorage.setItem(
      conversationStorageKey(sessionId),
      JSON.stringify(retryingSnapshot),
    );
    setSnapshot(retryingSnapshot);

    await new Promise((resolve) => window.setTimeout(resolve, 500));
    const saved: ConversationSnapshot = {
      ...retryingSnapshot,
      saveStatus: "saved",
    };
    sessionStorage.setItem(
      conversationStorageKey(sessionId),
      JSON.stringify(saved),
    );
    setSnapshot(saved);
    setRetrying(false);
  }

  if (!session) {
    return (
      <AppFrame>
        <div className="px-5 py-8 text-sm text-muted-foreground">
          This session link is not available.
        </div>
      </AppFrame>
    );
  }

  const saveStatus = snapshot?.saveStatus ?? "saved";
  const saveFailed = saveStatus === "retrying";

  return (
    <AppFrame>
      <div className="flex flex-col gap-5 px-5 py-8 sm:px-7">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--ink)]">
            Session complete
          </h1>
          <p className="text-[15px] leading-relaxed text-muted-foreground">
            {saveFailed
              ? "The session is still saving. Keep this page open while the application retries."
              : "Your session was saved. Thank you for participating."}
          </p>
        </div>

        {reason === "time_expired" ? (
          <Alert>
            <AlertTitle>Time limit reached</AlertTitle>
            <AlertDescription>
              The assigned discussion time ended, so the session closed
              automatically.
            </AlertDescription>
          </Alert>
        ) : null}

        {saveFailed ? (
          <Alert variant="destructive">
            <AlertTitle>Save still in progress</AlertTitle>
            <AlertDescription>
              Do not close this page. Local session state is preserved while
              saving retries.
            </AlertDescription>
          </Alert>
        ) : (
          <Alert>
            <AlertTitle>Saved</AlertTitle>
            <AlertDescription>
              Transcript and approved study measures for this prototype session
              are marked saved locally.
            </AlertDescription>
          </Alert>
        )}

        <div className="flex flex-col gap-1 rounded-xl bg-[#F7F3EE] px-4 py-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Next step
          </p>
          <p className="text-sm leading-relaxed text-[var(--ink)]">
            {session.rules.completionNextStep}
          </p>
        </div>

        {saveFailed ? (
          <Button
            type="button"
            onClick={() => void handleRetrySave()}
            disabled={retrying}
            data-testid="retry-save"
          >
            Retry save
          </Button>
        ) : null}
      </div>
    </AppFrame>
  );
}
