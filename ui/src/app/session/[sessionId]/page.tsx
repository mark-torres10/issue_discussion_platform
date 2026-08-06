import { notFound, redirect } from "next/navigation";
import { AppFrame } from "@/components/session/app-frame";
import { ParticipantIntroduction } from "@/components/session/participant-introduction";
import {
  getStudySession,
  isSessionAvailable,
} from "@/lib/api/study-backend";

interface SessionPageProps {
  params: Promise<{ sessionId: string }>;
}

export default async function SessionIntroductionPage({
  params,
}: SessionPageProps) {
  const { sessionId } = await params;
  const session = getStudySession(sessionId);

  if (!session) {
    notFound();
  }

  if (!isSessionAvailable(session)) {
    redirect(`/session/${sessionId}/unavailable`);
  }

  return (
    <AppFrame>
      <ParticipantIntroduction session={session} />
    </AppFrame>
  );
}
