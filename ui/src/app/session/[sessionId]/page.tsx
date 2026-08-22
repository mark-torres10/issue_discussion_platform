import { redirect } from "next/navigation";
import { PARTICIPANT_ROUTES } from "@/lib/api/study-backend";

export default function LegacySessionIntroductionPage() {
  redirect(PARTICIPANT_ROUTES.session);
}
