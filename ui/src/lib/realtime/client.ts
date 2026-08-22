import { createRealtimeCallAction } from "@/lib/api/study-backend-client";

/**
 * Negotiate a WebRTC session with the Study API Realtime endpoint.
 *
 * Returns the SDP answer from the server. The browser never receives provider
 * credentials or call identifiers.
 */
export async function negotiateRealtimeSession(
  sdpOffer: string,
  expectedVersion: number,
  idempotencyKey: string,
): Promise<string> {
  const response = await createRealtimeCallAction(
    sdpOffer,
    expectedVersion,
    idempotencyKey,
  );
  return response.sdp_answer;
}
