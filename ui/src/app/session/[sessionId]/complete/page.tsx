import { Suspense } from "react";
import { notFound } from "next/navigation";
import CompletePageClient from "./complete-client";
import { getStudySession } from "@/lib/api/study-backend";

interface CompletePageProps {
  params: Promise<{ sessionId: string }>;
}

export default async function CompletePage({ params }: CompletePageProps) {
  const { sessionId } = await params;
  const session = getStudySession(sessionId);
  if (!session) {
    notFound();
  }

  return (
    <Suspense
      fallback={
        <div className="px-5 py-8 text-sm text-muted-foreground">
          Loading completion…
        </div>
      }
    >
      <CompletePageClient session={session} />
    </Suspense>
  );
}
