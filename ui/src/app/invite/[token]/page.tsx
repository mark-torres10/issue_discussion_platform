import { redirect } from "next/navigation";
import { exchangeInvitation } from "@/lib/api/study-backend-client";
import { PARTICIPANT_ROUTES } from "@/lib/api/study-backend";

interface InvitePageProps {
  params: Promise<{ token: string }>;
}

export default async function InvitePage({ params }: InvitePageProps) {
  const { token } = await params;

  try {
    await exchangeInvitation(token);
  } catch {
    redirect(PARTICIPANT_ROUTES.unavailable);
  }

  redirect(PARTICIPANT_ROUTES.session);
}
