import { redirect } from "next/navigation";
import { PARTICIPANT_ROUTES } from "@/lib/api/study-backend";

export default function LegacyUnavailablePage() {
  redirect(PARTICIPANT_ROUTES.unavailable);
}
