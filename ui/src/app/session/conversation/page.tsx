import { redirect } from "next/navigation";
import { AppFrame } from "@/components/session/app-frame";
import {
  isSessionAvailable,
  PARTICIPANT_ROUTES,
} from "@/lib/api/study-backend";
import { fetchParticipantSession } from "@/lib/api/study-backend-client";
import { ConversationEntry } from "./conversation-entry";

export default async function ConversationPage() {
  const session = await fetchParticipantSession();

  if (!session) {
    redirect(PARTICIPANT_ROUTES.unavailable);
  }

  if (!isSessionAvailable(session)) {
    redirect(PARTICIPANT_ROUTES.unavailable);
  }

  return (
    <AppFrame className="overflow-hidden">
      <ConversationEntry session={session} />
    </AppFrame>
  );
}
