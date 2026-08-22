"use server";

import { cookies } from "next/headers";
import {
  CAPABILITY_COOKIE_NAME,
  CSRF_COOKIE_NAME,
  CSRF_HEADER_NAME,
} from "@/lib/api/csrf";
import {
  getParticipantCookieOptions,
  getStudyApiOrigin,
  IDEMPOTENCY_HEADER_NAME,
  mapParticipantSessionView,
  parseExchangeCookieValues,
  StudyApiError,
  type ExchangeCookieValues,
  type ParticipantSessionView,
  type SessionCompleteResponse,
  type SessionStartResponse,
} from "@/lib/api/study-backend";
import type { StudySession } from "@/lib/types/session";
import type { MessageResponse, TranscriptResponse } from "@/lib/types/transcript";

async function readParticipantCookies(): Promise<{
  capability: string | undefined;
  csrf: string | undefined;
}> {
  const cookieStore = await cookies();
  return {
    capability: cookieStore.get(CAPABILITY_COOKIE_NAME)?.value,
    csrf: cookieStore.get(CSRF_COOKIE_NAME)?.value,
  };
}

function buildCookieHeader(capability?: string): string | undefined {
  if (!capability) {
    return undefined;
  }
  return `${CAPABILITY_COOKIE_NAME}=${capability}`;
}

async function participantApiFetch<T>(
  path: string,
  init: RequestInit & { csrf?: boolean } = {},
): Promise<T> {
  const { capability, csrf } = await readParticipantCookies();
  const headers = new Headers(init.headers);
  if (init.csrf && csrf) {
    headers.set(CSRF_HEADER_NAME, csrf);
  }
  const cookieHeader = buildCookieHeader(capability);
  if (cookieHeader) {
    headers.set("cookie", cookieHeader);
  }
  if (init.body && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }

  const response = await fetch(`${getStudyApiOrigin()}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    let errorCode = "request_failed";
    let message = `Study API request failed (${response.status})`;
    try {
      const body = (await response.json()) as {
        error_code?: string;
        message?: string;
      };
      if (body.error_code) {
        errorCode = body.error_code;
      }
      if (body.message) {
        message = body.message;
      }
    } catch {
      // Keep default message when the body is not JSON.
    }
    throw new StudyApiError(response.status, errorCode, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function exchangeInvitationToken(
  invitationToken: string,
): Promise<{
  view: ParticipantSessionView;
  cookies: ExchangeCookieValues;
}> {
  const response = await fetch(
    `${getStudyApiOrigin()}/v1/participant-access/exchange`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ invitation_token: invitationToken }),
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new StudyApiError(
      response.status,
      "exchange_failed",
      "Invitation exchange failed",
    );
  }

  const view = (await response.json()) as ParticipantSessionView;
  return {
    view,
    cookies: parseExchangeCookieValues(response),
  };
}

/**
 * Exchange an invitation and persist cookies (Server Action / Route Handler only).
 */
export async function exchangeInvitation(
  invitationToken: string,
): Promise<ParticipantSessionView> {
  const { view, cookies: exchangeCookies } =
    await exchangeInvitationToken(invitationToken);
  const cookieStore = await cookies();

  if (exchangeCookies.capabilityValue) {
    cookieStore.set(
      CAPABILITY_COOKIE_NAME,
      exchangeCookies.capabilityValue,
      getParticipantCookieOptions(true),
    );
  }
  if (exchangeCookies.csrfToken) {
    cookieStore.set(
      CSRF_COOKIE_NAME,
      exchangeCookies.csrfToken,
      getParticipantCookieOptions(false),
    );
  }

  return view;
}

const MISSING_SESSION_STATUS_CODES = new Set([401, 404, 410, 500]);

export async function fetchParticipantSession(): Promise<StudySession | null> {
  try {
    const view = await participantApiFetch<ParticipantSessionView>(
      "/v1/participant-session",
    );
    return mapParticipantSessionView(view);
  } catch (error) {
    if (
      error instanceof StudyApiError &&
      MISSING_SESSION_STATUS_CODES.has(error.statusCode)
    ) {
      return null;
    }
    return null;
  }
}

export async function startParticipantSessionAction(
  preferredMode: "voice" | "text",
  expectedVersion: number,
  idempotencyKey: string,
): Promise<SessionStartResponse> {
  return participantApiFetch<SessionStartResponse>(
    "/v1/participant-session/start",
    {
      method: "POST",
      csrf: true,
      headers: {
        [IDEMPOTENCY_HEADER_NAME]: idempotencyKey,
      },
      body: JSON.stringify({
        preferred_mode: preferredMode,
        expected_version: expectedVersion,
      }),
    },
  );
}

export async function sendParticipantMessageAction(
  text: string,
  clientMessageId: string,
  expectedVersion: number,
  idempotencyKey: string,
): Promise<MessageResponse> {
  return participantApiFetch<MessageResponse>("/v1/participant-session/messages", {
    method: "POST",
    csrf: true,
    headers: {
      [IDEMPOTENCY_HEADER_NAME]: idempotencyKey,
    },
    body: JSON.stringify({
      client_message_id: clientMessageId,
      text,
      expected_version: expectedVersion,
    }),
  });
}

export async function fetchParticipantTranscriptAction(): Promise<TranscriptResponse> {
  return participantApiFetch<TranscriptResponse>(
    "/v1/participant-session/transcript",
  );
}

export async function completeParticipantSessionAction(
  reason: string,
  expectedVersion: number,
  idempotencyKey: string,
): Promise<SessionCompleteResponse> {
  return participantApiFetch<SessionCompleteResponse>(
    "/v1/participant-session/complete",
    {
      method: "POST",
      csrf: true,
      headers: {
        [IDEMPOTENCY_HEADER_NAME]: idempotencyKey,
      },
      body: JSON.stringify({
        reason,
        expected_version: expectedVersion,
        recovery_observations: [],
      }),
    },
  );
}

export async function createRealtimeCallAction(
  sdpOffer: string,
  expectedVersion: number,
  idempotencyKey: string,
): Promise<{ sdp_answer: string; expires_at: string }> {
  return participantApiFetch<{ sdp_answer: string; expires_at: string }>(
    "/v1/participant-session/realtime/calls",
    {
      method: "POST",
      csrf: true,
      headers: {
        [IDEMPOTENCY_HEADER_NAME]: idempotencyKey,
      },
      body: JSON.stringify({
        sdp_offer: sdpOffer,
        expected_version: expectedVersion,
      }),
    },
  );
}
