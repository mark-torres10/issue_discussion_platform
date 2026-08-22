import { NextResponse } from "next/server";
import {
  CAPABILITY_COOKIE_NAME,
  CSRF_COOKIE_NAME,
} from "@/lib/api/csrf";
import {
  getParticipantCookieOptions,
  getStudyApiOrigin,
  PARTICIPANT_ROUTES,
  parseExchangeCookieValues,
  StudyApiError,
} from "@/lib/api/study-backend";

interface InviteRouteContext {
  params: Promise<{ token: string }>;
}

function redirectTo(request: Request, path: string): NextResponse {
  return NextResponse.redirect(new URL(path, request.url));
}

function applyExchangeCookies(
  response: NextResponse,
  cookies: ReturnType<typeof parseExchangeCookieValues>,
): void {
  if (cookies.capabilityValue) {
    response.cookies.set(
      CAPABILITY_COOKIE_NAME,
      cookies.capabilityValue,
      getParticipantCookieOptions(true),
    );
  }
  if (cookies.csrfToken) {
    response.cookies.set(
      CSRF_COOKIE_NAME,
      cookies.csrfToken,
      getParticipantCookieOptions(false),
    );
  }
}

export async function GET(
  request: Request,
  context: InviteRouteContext,
): Promise<NextResponse> {
  const { token } = await context.params;

  try {
    const exchangeResponse = await fetch(
      `${getStudyApiOrigin()}/v1/participant-access/exchange`,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ invitation_token: token }),
        cache: "no-store",
      },
    );

    if (!exchangeResponse.ok) {
      return redirectTo(request, PARTICIPANT_ROUTES.unavailable);
    }

    void (await exchangeResponse.json());
    const cookies = parseExchangeCookieValues(exchangeResponse);
    const redirect = redirectTo(request, PARTICIPANT_ROUTES.session);
    applyExchangeCookies(redirect, cookies);
    return redirect;
  } catch (error) {
    if (error instanceof StudyApiError) {
      return redirectTo(request, PARTICIPANT_ROUTES.unavailable);
    }
    return redirectTo(request, PARTICIPANT_ROUTES.unavailable);
  }
}
