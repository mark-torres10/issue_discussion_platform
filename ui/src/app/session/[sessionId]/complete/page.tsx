import { redirect } from "next/navigation";
import { PARTICIPANT_ROUTES } from "@/lib/api/study-backend";

export default function LegacyCompletePage() {
  redirect(PARTICIPANT_ROUTES.complete);
}
