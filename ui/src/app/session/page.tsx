import { redirect } from "next/navigation";
import { AppFrame } from "@/components/session/app-frame";
import { ParticipantIntroduction } from "@/components/session/participant-introduction";
import {
  isSessionAvailable,
  PARTICIPANT_ROUTES,
} from "@/lib/api/study-backend";
import { fetchParticipantSession } from "@/lib/api/study-backend-client";

export default async function SessionIntroductionPage() {
  const session = await fetchParticipantSession();

  if (!session) {
    redirect(PARTICIPANT_ROUTES.unavailable);
  }

  if (!isSessionAvailable(session)) {
    redirect(PARTICIPANT_ROUTES.unavailable);
  }

  return (
    <AppFrame>
      <ParticipantIntroduction
        session={session}
        audioCheckHref={PARTICIPANT_ROUTES.audioCheck}
      />
    </AppFrame>
  );
}
