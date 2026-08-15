"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { AppFrame } from "@/components/session/app-frame";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useUiCopy } from "@/lib/content/content-provider";
import {
  conversationStorageKey,
  parseConversationSnapshot,
} from "@/lib/realtime/state";
import type { ConversationSnapshot, StudySession } from "@/lib/types/session";

interface CompletePageClientProps {
  session: StudySession;
}

/**
 * Completion confirmation with mocked save status and next-step instruction.
 */
export default function CompletePageClient({
  session,
}: CompletePageClientProps) {
  const copy = useUiCopy();
  const searchParams = useSearchParams();
  const reason = searchParams.get("reason");
  const [snapshot, setSnapshot] = useState<ConversationSnapshot | null>(() => {
    if (typeof window === "undefined") {
      return null;
    }
    const raw = sessionStorage.getItem(
      conversationStorageKey(session.sessionId),
    );
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
      conversationStorageKey(session.sessionId),
      JSON.stringify(retryingSnapshot),
    );
    setSnapshot(retryingSnapshot);

    await new Promise((resolve) => window.setTimeout(resolve, 500));
    const saved: ConversationSnapshot = {
      ...retryingSnapshot,
      saveStatus: "saved",
    };
    sessionStorage.setItem(
      conversationStorageKey(session.sessionId),
      JSON.stringify(saved),
    );
    setSnapshot(saved);
    setRetrying(false);
  }

  const saveStatus = snapshot?.saveStatus ?? "saved";
  const saveFailed = saveStatus === "retrying";

  return (
    <AppFrame>
      <div className="flex flex-col gap-5 px-5 py-8 sm:px-7">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--ink)]">
            {copy.complete.heading}
          </h1>
          <p className="text-[15px] leading-relaxed text-muted-foreground">
            {saveFailed ? copy.complete.savingBody : copy.complete.savedBody}
          </p>
        </div>

        {reason === "time_expired" ? (
          <Alert>
            <AlertTitle>{copy.complete.timeLimitTitle}</AlertTitle>
            <AlertDescription>{copy.complete.timeLimitBody}</AlertDescription>
          </Alert>
        ) : null}

        {saveFailed ? (
          <Alert variant="destructive">
            <AlertTitle>{copy.complete.saveInProgressTitle}</AlertTitle>
            <AlertDescription>
              {copy.complete.saveInProgressBody}
            </AlertDescription>
          </Alert>
        ) : (
          <Alert>
            <AlertTitle>{copy.complete.savedTitle}</AlertTitle>
            <AlertDescription>{copy.complete.savedDescription}</AlertDescription>
          </Alert>
        )}

        <div className="flex flex-col gap-1 rounded-xl bg-[#F7F3EE] px-4 py-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {copy.complete.nextStepLabel}
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
            {copy.complete.retrySave}
          </Button>
        ) : null}
      </div>
    </AppFrame>
  );
}
