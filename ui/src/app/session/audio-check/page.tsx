import { redirect } from "next/navigation";
import { AppFrame } from "@/components/session/app-frame";
import { AudioCheck } from "@/components/session/audio-check";
import {
  isSessionAvailable,
  PARTICIPANT_ROUTES,
} from "@/lib/api/study-backend";
import { fetchParticipantSession } from "@/lib/api/study-backend-client";

export default async function AudioCheckPage() {
  const session = await fetchParticipantSession();

  if (!session) {
    redirect(PARTICIPANT_ROUTES.unavailable);
  }

  if (!isSessionAvailable(session)) {
    redirect(PARTICIPANT_ROUTES.unavailable);
  }

  return (
    <AppFrame>
      <AudioCheck sessionId={session.sessionId} />
    </AppFrame>
  );
}
