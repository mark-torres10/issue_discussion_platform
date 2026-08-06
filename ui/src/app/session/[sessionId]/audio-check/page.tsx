import { notFound, redirect } from "next/navigation";
import { AppFrame } from "@/components/session/app-frame";
import { AudioCheck } from "@/components/session/audio-check";
import {
  getStudySession,
  isSessionAvailable,
} from "@/lib/api/study-backend";

interface AudioCheckPageProps {
  params: Promise<{ sessionId: string }>;
}

export default async function AudioCheckPage({ params }: AudioCheckPageProps) {
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
      <AudioCheck sessionId={session.sessionId} />
    </AppFrame>
  );
}
