import { notFound, redirect } from "next/navigation";
import { AppFrame } from "@/components/session/app-frame";
import { ConversationShell } from "@/components/conversation/conversation-shell";
import {
  getStudySession,
  isSessionAvailable,
} from "@/lib/api/study-backend";

interface ConversationPageProps {
  params: Promise<{ sessionId: string }>;
}

export default async function ConversationPage({
  params,
}: ConversationPageProps) {
  const { sessionId } = await params;
  const session = getStudySession(sessionId);

  if (!session) {
    notFound();
  }

  if (!isSessionAvailable(session)) {
    redirect(`/session/${sessionId}/unavailable`);
  }

  return (
    <AppFrame className="overflow-hidden">
      <ConversationShell session={session} />
    </AppFrame>
  );
}
