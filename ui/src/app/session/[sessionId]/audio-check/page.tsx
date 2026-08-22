import { redirect } from "next/navigation";
import { PARTICIPANT_ROUTES } from "@/lib/api/study-backend";

export default function LegacyAudioCheckPage() {
  redirect(PARTICIPANT_ROUTES.audioCheck);
}
